"""
FCPX Importer for video cutter project
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime
from math import gcd
from fractions import Fraction
import uuid
import logging

logger = logging.getLogger(__name__)

# Известные "круглые" частоты кадров и их точное рациональное представление
# frameDuration (числитель/знаменатель) + признак drop-frame таймкода.
_KNOWN_FRAME_RATES = [
    (23.976, 1001, 24000, False),
    (24.0, 1, 24, False),
    (25.0, 1, 25, False),
    (29.97, 1001, 30000, True),
    (30.0, 1, 30, False),
    (50.0, 1, 50, False),
    (59.94, 1001, 60000, True),
    (60.0, 1, 60, False),
]

class FCPXImporter:
    def __init__(self):
        self.version = '1.10'

    def create_fcpx_xml(self, good_frames: list, project_name: str = 'Video_Cutter_Project',
                        video_path: str = None, frame_clip_duration_frames: int = 1) -> str:
        """
        Создает .fcpxml с отобранными кадрами.

        :param good_frames: список словарей с найденными кадрами. Каждый должен
            содержать 'frame_number' (номер кадра в исходном видео, считая с 1) —
            именно он используется, чтобы клип в итоговом проекте указывал
            на реальную позицию этого кадра в исходнике.
        :param video_path: путь к исходному видео. Обязателен для того, чтобы
            кадры реально попали в проект (без него создать валидную ссылку
            на медиа невозможно).
        :param frame_clip_duration_frames: длительность одного клипа в кадрах
            (по умолчанию 1 кадр = ровно тот самый "хороший кадр"). Можно
            увеличить, если нужен клип подлиннее вокруг найденного кадра.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        xml_filename = f'{project_name}_{timestamp}.fcpxml'
        output_dir = 'output_videos'
        os.makedirs(output_dir, exist_ok=True)
        full_path = os.path.join(output_dir, xml_filename)

        root = ET.Element('fcpxml', {'version': '1.10'})
        resources = ET.SubElement(root, 'resources')

        has_video = bool(video_path and os.path.exists(video_path))
        source = self._probe_source(video_path) if has_video else None
        if has_video and source is None:
            logger.warning(
                'Не удалось прочитать параметры исходного видео через OpenCV — '
                'использую значения по умолчанию (4K, 29.97fps).'
            )
        if source is None:
            source = {
                'width': 3840, 'height': 2160,
                'fd_num': 1001, 'fd_den': 30000,
                'drop_frame': True, 'total_frames': None,
            }

        fd_num, fd_den = source['fd_num'], source['fd_den']

        # Важно: FCPXML DTD не поддерживает 'frameRate' и 'pixelAspect'.
        # Частота кадров задается через frameDuration (рациональная дробь,
        # "время одного кадра"), вычисленная из реального fps источника.
        #
        # ВАЖНО про id: несмотря на то, что символ '.' формально допустим
        # в XML Name, парсер Final Cut Pro на практике не принимает
        # описательные id (например 'H.264_4K2997') как валидный IDREF и
        # выдает "Encountered an unexpected value" на любой атрибут, который
        # на него ссылается. Все реальные экспорты FCP используют простые id
        # вида 'r1', 'r2', ...
        #
        # ВАЖНО про уникальность: id должен быть уникален не только внутри
        # ЭТОГО файла, но и во всей библиотеке FCP, куда его импортируют.
        # При повторном импорте FCP сопоставляет ресурсы по id: если в
        # библиотеке уже есть, например, 'r1' с ДРУГИМИ шириной/высотой/fps
        # (из более раннего теста или другого исходника), новый 'r1' будет
        # считаться конфликтующим — отсюда "Encountered an unexpected value"
        # на @format и, как следствие, "Invalid edit with no respective
        # media" на всех клипах, ссылающихся на этот формат. Поэтому
        # генерируем случайный уникальный id на каждый вызов.
        FORMAT_ID = f'r_fmt_{uuid.uuid4().hex[:12]}'
        ET.SubElement(resources, 'format', {
            'id': FORMAT_ID,
            'name': f"Source Format {source['width']}x{source['height']}",
            'width': str(source['width']),
            'height': str(source['height']),
            'frameDuration': self._frames_to_time(1, fd_num, fd_den),
            # Без colorSpace Final Cut Pro на практике не принимает
            # произвольный format как валидный для использования в
            # sequence/@format — выдает "Encountered an unexpected value"
            # именно на этот атрибут, даже если сам format синтаксически
            # корректен. Rec. 709 — стандартное цветовое пространство для
            # обычного SDR HD/UHD видео.
            'colorSpace': '1-1-1 (Rec. 709)',
        })

        event = ET.SubElement(root, 'event', {'name': f'{project_name} Event'})
        project = ET.SubElement(event, 'project', {'name': project_name})

        # <sequence> в FCPXML не имеет атрибута 'name' — имя задается только
        # на уровне <project>.
        sequence = ET.SubElement(project, 'sequence', {
            'duration': '0s',
            'tcStart': '0s',
            'tcFormat': 'DF' if source['drop_frame'] else 'NDF',
            'format': FORMAT_ID,
        })
        spine = ET.SubElement(sequence, 'spine')

        if has_video and good_frames:
            ASSET_ID = f'r_asset_{uuid.uuid4().hex[:12]}'

            # Сортируем по реальному номеру кадра — порядок в спине должен
            # соответствовать хронологии исходника, а не порядку обнаружения.
            sorted_frames = sorted(good_frames, key=lambda f: f.get('frame_number', 0))

            last_frame_number = sorted_frames[-1].get('frame_number', 0)
            total_source_frames = source['total_frames'] or (last_frame_number + frame_clip_duration_frames)

            # ВАЖНО: в FCPXML 1.10 у <asset> нет атрибута 'src'. По DTD
            # content-модель asset — это (media-rep+, metadata?), то есть
            # путь к файлу задается ДОЧЕРНИМ элементом <media-rep>, а не
            # атрибутом на самом asset. Отсюда и ошибка "expecting
            # (media-rep+, metadata?)" / "No declaration for attribute src".
            asset = ET.SubElement(resources, 'asset', {
                'id': ASSET_ID,
                'name': os.path.basename(video_path),
                'start': '0s',
                'duration': self._frames_to_time(total_source_frames, fd_num, fd_den),
                'format': FORMAT_ID,
                'hasVideo': '1',
                'videoSources': '1',
            })
            
            # Добавляем media-rep элемент для указания пути к файлу
            # Используем правильный путь с file:// префиксом
            if video_path and os.path.exists(video_path):
                abs_video_path = os.path.abspath(video_path)
                media_rep = ET.SubElement(asset, 'media-rep', {
                    'kind': 'original-media',
                    'src': f'file://{abs_video_path}',
                })
            else:
                # Если файл не существует, создаем пустой media-rep
                media_rep = ET.SubElement(asset, 'media-rep', {
                    'kind': 'original-media',
                    'src': 'file://',
                })

            # Создаем asset-clip (не clip!) для каждого отобранного кадра.
            # 'ref' — ссылка на asset по id. 'start' — реальная позиция
            # этого кадра внутри исходника (из frame_data['frame_number']).
            # 'offset' — последовательная позиция клипа на таймлинии
            # итоговой секвенции (клипы идут друг за другом по порядку).
            cumulative_offset_frames = 0
            for frame_data in sorted_frames:
                frame_number = frame_data.get('frame_number', 1)
                # frame_number считается с 1 (см. VideoAnalyzer.analyze_video),
                # переводим в 0-based позицию для внутреннего таймкода asset'а.
                source_start_frames = max(frame_number - 1, 0)

                offset = self._frames_to_time(cumulative_offset_frames, fd_num, fd_den)
                start = self._frames_to_time(source_start_frames, fd_num, fd_den)
                duration = self._frames_to_time(frame_clip_duration_frames, fd_num, fd_den)

                ET.SubElement(spine, 'asset-clip', {
                    'name': f'Good_Frame_{frame_number}',
                    'ref': ASSET_ID,
                    'offset': offset,
                    'start': start,
                    'duration': duration,
                    'format': FORMAT_ID,
                })
                cumulative_offset_frames += frame_clip_duration_frames

            # Реальная длительность секвенции = сумма длительностей всех клипов.
            sequence.set('duration', self._frames_to_time(cumulative_offset_frames, fd_num, fd_den))
        else:
            # Без video_path или без good_frames валидный asset-clip создать
            # нельзя (не на что ставить 'ref') — секвенция останется пустой.
            logger.warning(
                'video_path не передан/не найден или good_frames пуст — '
                'клипы не будут добавлены в проект.'
            )

        try:
            tree = ET.ElementTree(root)
            self._indent(root)
            tree.write(full_path, encoding='utf-8', xml_declaration=True)
            logger.info(f'Создан XML файл для FCPX: {full_path}')
            return full_path
        except Exception as e:
            logger.error(f'Ошибка при создании XML файла: {str(e)}')
            raise

    def _probe_source(self, video_path: str):
        """Читает реальные параметры исходного видео через OpenCV
        (разрешение, fps, общее число кадров). Возвращает None, если
        видео открыть не удалось или OpenCV недоступен."""
        try:
            import cv2
        except ImportError:
            logger.warning('OpenCV недоступен — не могу определить параметры исходного видео.')
            return None

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        try:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
            fps = cap.get(cv2.CAP_PROP_FPS) or 29.97
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or None
        finally:
            cap.release()

        fd_num, fd_den, drop_frame = self._fps_to_frame_duration(fps)
        return {
            'width': width, 'height': height,
            'fd_num': fd_num, 'fd_den': fd_den,
            'drop_frame': drop_frame, 'total_frames': total_frames,
        }

    def _fps_to_frame_duration(self, fps: float):
        """Переводит fps в точную рациональную пару (числитель, знаменатель)
        для frameDuration + признак drop-frame таймкода. Для нестандартных
        fps подбирает ближайшую рациональную аппроксимацию."""
        for known_fps, num, den, drop_frame in _KNOWN_FRAME_RATES:
            if abs(fps - known_fps) < 0.05:
                return num, den, drop_frame

        frac = Fraction(1, 1)
        if fps > 0:
            frac = Fraction(1 / fps).limit_denominator(60000)
        return frac.numerator, frac.denominator, False

    def _frames_to_time(self, frames: int, fd_num: int = 1001, fd_den: int = 30000) -> str:
        """Переводит количество кадров в рациональную строку времени FCPXML,
        кратную frameDuration (fd_num/fd_den), например '15015/30000s'.
        Дробь по возможности сокращается через НОД. Если дробь сокращается
        до целого числа секунд, возвращает короткую форму, например '4s'
        (именно так FCP форматирует целые значения)."""
        if frames == 0:
            return '0s'
        numerator = frames * fd_num
        denominator = fd_den
        divisor = gcd(numerator, denominator)
        numerator //= divisor
        denominator //= divisor
        if denominator == 1:
            return f'{numerator}s'
        return f'{numerator}/{denominator}s'

    def _indent(self, elem, level=0):
        """Функция для корректного форматирования XML"""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i


if __name__ == '__main__':
    importer = FCPXImporter()
    print('FCPX Importer ready')
