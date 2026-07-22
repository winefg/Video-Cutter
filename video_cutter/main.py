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


def main(input_path="./video_cutter/input_videos"):
    """Основная функция"""
    logger = setup_logging()
    logger.info("🚀 Запуск Video Cutter")

    # Проверяем наличие входной папки
    output_dir = "./output_videos"
    os.makedirs(output_dir, exist_ok=True)

    # Обрабатываем входной путь - может быть файлом или директорией
    video_file = []

    if os.path.isfile(input_path):
        # Если это файл, добавляем его в список
        video_files = [os.path.basename(input_path)]
        input_dir = os.path.dirname(input_path)
    elif os.path.isdir(input_path):
        # Если это директория, получаем все видеофайлы
        input_dir = input_path
        video_files = [f for f in os.listdir(input_dir)
                       if f.lower().endswith(('.mov', '.mp4', '.avi'))]
    else:
        logger.error(f"Указанный путь не существует: {input_path}")
        return

    if not video_files:
        logger.warning("Нет видеофайлов для обработки")
        return

    logger.info(f"Найдено {len(video_files)} видеофайлов")

    # Создаем анализатор
    analyzer = VideoAnalyzer()
    importer = FCPXImporter()

    # Обрабатываем каждый файл
    for video_file in video_files:
        if os.path.isfile(input_path):
            # Если input_path был файлом, используем его как путь к файлу
            input_path_full = input_path
        else:
            # Иначе формируем полный путь к файлу
            input_path_full = os.path.join(input_dir, video_file)

        logger.info(f"🔄 Обработка файла: {video_file}")

        try:
            # Анализируем видео и получаем хорошие кадры
            good_frames = analyzer.analyze_video(input_path_full)

            logger.info(f"✅ Найдено {len(good_frames)} хороших кадров")

            # Создаем XML файл для FCPX
            if good_frames:
                xml_file = importer.create_fcpx_xml(
                    good_frames,
                    project_name="Wedding_PAKV3379",
                    video_path=input_path_full,  # <-- Это уже абсолютный путь
                    frame_clip_duration_frames=1
                )
                logger.info(f"Создан XML файл для импорта: {xml_file}")

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке {video_file}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    logger.info("🏁 Обработка завершена")


if __name__ == "__main__":
    # Allow input directory to be passed as command line argument
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = "./input_videos"

    main(input_path)
