import os
import xml.etree.ElementTree as ET
from datetime import datetime
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

        # Создаем корневой элемент
        root = ET.Element('fcpxml', {'version': '1.10'})

        # Создаем library и event
        library = ET.SubElement(root, 'library')
        event = ET.SubElement(library, 'event', {'name': f'{project_name} Event'})
        project = ET.SubElement(event, 'project', {'name': project_name})

        # Создаем sequence с форматом для 4K 29.97fps
        sequence = ET.SubElement(project, 'sequence', {
            'name': f'{project_name} Sequence',
            'duration': '0s',
            'tcStart': '0s',
            'tcFormat': 'DF',
            'format': 'H.264_4K2997'  # Формат для 4K 29.97fps
        })

        spine = ET.SubElement(sequence, 'spine')

        # Если указан путь к видео, создаем asset
        if video_path and os.path.exists(video_path):
            # Создаем asset (ассеты должны быть в library)
            asset = ET.SubElement(library, 'asset', {
                'id': 'r1',
                'name': 'Source Video',
                'src': f'file://{video_path}',
                'start': '0s',
                'duration': '10s'  # Укажи реальную длительность
            })

            # Создаем clip, который ссылается на asset
            for i, frame_data in enumerate(good_frames):
                clip = ET.SubElement(spine, 'clip', {
                    'name': f'Good_Frame_{i + 1}',
                    'start': f'{i * 0.5}s',
                    'duration': '0.5s',
                    'asset': 'r1'  # Ссылка на asset
                })
        else:
            # Если нет видео, создаем простые clip'ы (не рекомендуется)
            for i, frame_data in enumerate(good_frames):
                ET.SubElement(spine, 'clip', {
                    'name': f'Good_Frame_{i + 1}',
                    'start': f'{i * 0.5}s',
                    'duration': '0.5s'
                })

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
