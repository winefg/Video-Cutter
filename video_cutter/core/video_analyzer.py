"""
Анализ видеофайлов для отбора хороших кадров
"""

import os
import cv2
import numpy as np
import logging
from typing import List, Dict  # Добавлен импорт Dict
from .frame_processor import FrameProcessor

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """
    Класс для анализа видеофайлов и отбора хороших кадров
    """

    def __init__(self):
        self.frame_processor = FrameProcessor()
        # Пороги для определения хороших кадров (можно настраивать)
        # Снижены для более гибкого анализа
        self.min_blur_threshold = 50
        self.min_exposure_threshold = 20
        self.max_exposure_threshold = 230
        self.min_contrast_threshold = 10

    def analyze_video(self, video_path: str) -> List[Dict]:
        """
        Основной метод анализа видеофайла

        :param video_path: путь к видеофайлу
        :return: список хороших кадров с метриками
        """
        logger.info(f"Начинаем анализ видео: {os.path.basename(video_path)}")

        # Проверяем существование файла
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Видео файл не найден: {video_path}")

        # Открываем видео
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видео файл: {video_path}")

        good_frames = []
        frame_count = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1

                # Анализируем кадр
                metrics = self.frame_processor.process_frame(frame, frame_count)

                # Проверяем, хороший ли кадр
                is_good = self.is_good_frame(metrics)

                # Логируем метрики для каждого кадра (только для первых нескольких)
                if frame_count <= 5:
                    logger.info(f"Кадр {frame_count}: blur={metrics.get('blur', 0):.2f}, "
                               f"exposure={metrics.get('exposure', 0):.2f}, "
                               f"contrast={metrics.get('contrast', 0):.2f}, "
                               f"good={is_good}")

                if is_good:
                    good_frames.append({
                        'frame_number': frame_count,
                        'timestamp': frame_count / 29.97,  # Предполагаем 30 FPS
                        'metrics': metrics
                    })

                # Логируем прогресс каждые 100 кадров
                if frame_count % 100 == 0:
                    logger.info(f"Обработано {frame_count} кадров")

        except Exception as e:
            logger.error(f"Ошибка при анализе видео: {str(e)}")
            raise
        finally:
            cap.release()

        logger.info(f"Анализ завершен. Найдено {len(good_frames)} хороших кадров из {frame_count}")
        return good_frames

    def is_good_frame(self, metrics: Dict) -> bool:
        """
        Проверяет, является ли кадр хорошим по заданным критериям

        :param metrics: метрики кадра
        :return: True если кадр хороший
        """
        blur = metrics.get('blur', 0)
        exposure = metrics.get('exposure', 0)
        contrast = metrics.get('contrast', 0)

        # Логирование для отладки (можно удалить в продакшене)
        logger.debug(f"Frame metrics - blur: {blur}, exposure: {exposure}, contrast: {contrast}")

        # Проверяем размытие (чем выше значение, тем меньше размытость)
        if blur < self.min_blur_threshold:
            logger.debug(f"Кадр отклонен по размытию: {blur} < {self.min_blur_threshold}")
            return False

        # Проверяем экспозицию
        if exposure < self.min_exposure_threshold or exposure > self.max_exposure_threshold:
            logger.debug(f"Кадр отклонен по экспозиции: {exposure} не в диапазоне "
                       f"{self.min_exposure_threshold}-{self.max_exposure_threshold}")
            return False

        # Проверяем контрастность
        if contrast < self.min_contrast_threshold:
            logger.debug(f"Кадр отклонен по контрастности: {contrast} < {self.min_contrast_threshold}")
            return False

        logger.debug("Кадр прошел все проверки")
        return True


if __name__ == "__main__":
    # Тестовый запуск
    analyzer = VideoAnalyzer()
    print("VideoAnalyzer создан успешно")
