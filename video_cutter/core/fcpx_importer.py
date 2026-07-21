import os
import xml.etree.ElementTree as ET
from datetime import datetime
from math import gcd
import logging

logger = logging.getLogger(__name__)


class FCPXImporter:
    def __init__(self):
        self.version = '1.10'

    def create_fcpx_xml(self, good_frames: list, project_name: str = 'Video_Cutter_Project',
                        video_path: str = None) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        xml_filename = f'{project_name}_{timestamp}.fcpxml'
        output_dir = 'output_videos'
        os.makedirs(output_dir, exist_ok=True)
        full_path = os.path.join(output_dir, xml_filename)

        # Создаем корневой элемент с DTD
        root = ET.Element('fcpxml', {'version': '1.10'})

        # Создаем resources section
        resources = ET.SubElement(root, 'resources')

        # Создаем формат в resources
        # Важно: FCPXML DTD не поддерживает 'frameRate' и 'pixelAspect'.
        # Частота кадров задается через frameDuration (рациональная дробь,
        # "время одного кадра"), а не десятичным числом.
        # 29.97 fps (drop-frame) => 1001/30000s
        #
        # ВАЖНО про id: несмотря на то, что символ '.' формально допустим
        # в XML Name, парсер Final Cut Pro на практике не принимает
        # описательные id вроде 'H.264_4K2997' как валидный IDREF и выдает
        # "Encountered an unexpected value" на любой атрибут, который на
        # него ссылается (например sequence/@format). Все реальные экспорты
        # FCP используют простые id вида 'r1', 'r2', ... — используем ту же
        # схему, а описательное имя переносим в атрибут 'name'.
        FORMAT_ID = 'r1'
        format_4k_2997 = ET.SubElement(resources, 'format', {
            'id': FORMAT_ID,
            'name': 'H.264 4K 29.97fps',
            'width': '3840',
            'height': '2160',
            'frameDuration': '1001/30000s'
            # pixelAspect убран: для квадратных пикселей (1:1) атрибут
            # не требуется и не описан в DTD.
        })

        # Создаем event
        event = ET.SubElement(root, 'event', {'name': f'{project_name} Event'})
        project = ET.SubElement(event, 'project', {'name': project_name})

        # Создаем sequence. Важно: <sequence> в FCPXML не имеет атрибута
        # 'name' — имя задается только на уровне <project>.
        sequence = ET.SubElement(project, 'sequence', {
            'duration': '0s',
            'tcStart': '0s',
            'tcFormat': 'DF',
            'format': FORMAT_ID
        })

        spine = ET.SubElement(sequence, 'spine')

        # Длительность одного "хорошего кадра" в кадрах тайм-базы 30000/1001.
        # Один реальный кадр при 29.97fps длится 1001/30000s; берем клип
        # длиной 15 кадров (~0.5s), чтобы получить ровное рациональное число.
        frames_per_segment = 15  # 15 * 1001/30000s = 15015/30000s ≈ 0.5s

        # Если указан путь к видео, создаем asset
        if video_path and os.path.exists(video_path):
            ASSET_ID = 'r2'
            total_frames = frames_per_segment * max(len(good_frames), 1)
            # Реальная длительность секвенции = сумма всех клипов,
            # а не захардкоженный '0s'.
            sequence.set('duration', self._frames_to_time(total_frames))

            # Создаем asset в resources (не в library).
            # 'format' обязателен — ссылка на формат этого asset'а.
            # 'hasVideo' указывает, что это видеодорожка.
            asset = ET.SubElement(resources, 'asset', {
                'id': ASSET_ID,
                'name': 'Source Video',
                'src': f'file://{video_path}',
                'start': '0s',
                'duration': self._frames_to_time(total_frames),
                'format': FORMAT_ID,
                'hasVideo': '1',
                'videoSources': '1'
            })

            # Создаем asset-clip (не clip!), который ссылается на asset
            # через атрибут 'ref'. 'offset' — позиция на общей таймлинии
            # секвенции, 'start' — точка входа внутри самого asset'а.
            for i, frame_data in enumerate(good_frames):
                offset = self._frames_to_time(i * frames_per_segment)
                duration = self._frames_to_time(frames_per_segment)
                ET.SubElement(spine, 'asset-clip', {
                    'name': f'Good_Frame_{i + 1}',
                    'ref': ASSET_ID,
                    'offset': offset,
                    'start': offset,
                    'duration': duration,
                    'format': FORMAT_ID
                })
        else:
            # Без исходного видео валидный asset-clip создать нельзя (нет
            # ref на реальный asset), поэтому явно предупреждаем в логах.
            logger.warning(
                'video_path не указан или файл не найден — '
                'clip-элементы без ссылки на asset не будут валидны '
                'по FCPXML DTD и пропущены.'
            )

        try:
            tree = ET.ElementTree(root)
            # Убираем лишние отступы для корректного форматирования
            self._indent(root)
            tree.write(full_path, encoding='utf-8', xml_declaration=True)
            logger.info(f'Создан XML файл для FCPX: {full_path}')
            return full_path
        except Exception as e:
            logger.error(f'Ошибка при создании XML файла: {str(e)}')
            raise

    def _frames_to_time(self, frames: int) -> str:
        """Переводит количество кадров в рациональную строку времени FCPXML,
        кратную frameDuration (1001/30000s), например '15015/30000s'.
        Дробь по возможности сокращается через НОД."""
        numerator = frames * 1001
        denominator = 30000
        divisor = gcd(numerator, denominator) if numerator else 1
        if numerator == 0:
            return '0s'
        return f'{numerator // divisor}/{denominator // divisor}s'

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