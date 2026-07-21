"""
Video-Cutter - main module
"""

import os
import sys
import logging
from datetime import datetime
from core import VideoAnalyzer, FCPXImporter

def setup_logging():
    """Настройка логирования"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"video_cutter_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    """Основная функция"""
    logger = setup_logging()
    logger.info("🚀 Запуск Video Cutter")
    
    # Проверяем наличие входной папки
    input_dir = "input_videos"
    output_dir = "output_videos"
    
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        logger.warning(f"Создана папка для входных файлов: {input_dir}")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.warning(f"Создана папка для выходных файлов: {output_dir}")
    
    # Получаем список видеофайлов
    video_files = [f for f in os.listdir(input_dir) 
                   if f.lower().endswith(('.mov', '.mp4', '.avi'))]
    
    if not video_files:
        logger.warning("Нет видеофайлов для обработки")
        return
    
    logger.info(f"Найдено {len(video_files)} видеофайлов")
    
    # Создаем анализатор
    analyzer = VideoAnalyzer()
    importer = FCPXImporter()
    
    # Обрабатываем каждый файл
    for video_file in video_files:
        input_path = os.path.join(input_dir, video_file)
        logger.info(f"🔄 Обработка файла: {video_file}")
        
        try:
            # Анализируем видео и получаем хорошие кадры
            good_frames = analyzer.analyze_video(input_path)
            
            logger.info(f"✅ Найдено {len(good_frames)} хороших кадров")
            
            # Создаем XML файл для FCPX
            if good_frames:
                xml_file = importer.create_fcpx_xml(
                    good_frames, 
                    f"Wedding_{os.path.splitext(video_file)[0]}"
                )
                logger.info(f"Создан XML файл для импорта: {xml_file}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке {video_file}: {str(e)}")
            continue
    
    logger.info("🏁 Обработка завершена")

if __name__ == "__main__":
    main()

