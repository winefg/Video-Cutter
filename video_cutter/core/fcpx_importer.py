"""
Importing footage into Final Cut Pro
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FCPXImporter:
    """
    Класс для создания XML файлов для импорта в Final Cut Pro
    """
    
    def __init__(self):
        self.version = "1.10"
    
    def create_fcpx_xml(self, good_frames: list, project_name: str = 
"Video_Cutter_Project") -> str:
        """
        Создание XML файла для импорта в FCPX
        
        :param good_frames: список хороших кадров
        :param project_name: имя проекта
        :return: путь к созданному XML файлу
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        xml_filename = f"{project_name}_{timestamp}.xml"
        
        # Создаем корневой элемент
        root = ET.Element("fcpxml")
        root.set("version", self.version)
        
        # Создаем проект
        project = ET.SubElement(root, "project")
        project.set("name", project_name)
        
        # Создаем событие
        event = ET.SubElement(project, "event")
        event.set("name", f"{project_name}_Event")
        
        # Создаем последовательность
        sequence = ET.SubElement(event, "sequence")
        
        # Создаем spine (основная линия)
        spine = ET.SubElement(sequence, "spine")
        
        # Добавляем каждый хороший кадр как clip
        for i, frame in enumerate(good_frames):
            clip = ET.SubElement(spine, "clip")
            clip.set("name", f"Good_Frame_{i+1}")
            clip.set("start", f"{frame['timestamp']}s")
            clip.set("duration", "0.5s")  # Продолжительность по умолчанию
            
        # Сохраняем XML файл
        try:
            tree = ET.ElementTree(root)
            tree.write(xml_filename, encoding='utf-8', xml_declaration=True)
            logger.info(f"Создан XML файл для FCPX: {xml_filename}")
            return xml_filename
        except Exception as e:
            logger.error(f"Ошибка при создании XML файла: {str(e)}")
            raise

if __name__ == "__main__":
    # Тестовый запуск
    importer = FCPXImporter()
    print("FCPXImporter создан успешно")
