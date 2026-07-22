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
        self.min_blur_threshold = 100
        self.min_exposure_threshold = 30
        self.max_motion_threshold = 500

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
                if self.is_good_frame(metrics):
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

        """
        print(f"DEBUG: Metrics - blur={metrics.get('blur', 0)}, "
              f"exposure={metrics.get('exposure', 0)}, "
              f"contrast = {metrics.get('contrast', 0)}")
              
        print(f"DEBUG: blur={blur}, exposure={exposure}, contrast = {contrast} ")
        print(f"DEBUG: blur < 20? {blur < 20}")
        print(f"DEBUG: exposure < 30 or exposure > 240? {exposure < 30 or exposure > 240}")
        print(f"DEBUG: contrast < 15? {contrast < 15}")
        """
        blur = metrics.get('blur', 0)
        exposure = metrics.get('exposure', 0)
        contrast = metrics.get('contrast', 0)



        # Нормализованные критерии для реальных значений
        # Размытие (Laplacian variance):
        # - 0-20: очень размыто
        # - 20-50: размыто
        # - 50-100: нормально
        # - >100: хорошо

        # Проверяем размытие (чем выше значение, тем меньше размытость)
        if blur < 20:    # Снижаем порог размытия
            return False

    # Проверяем экспозицию
        # Экспозиция: от 0 до 255
        if exposure < 30 or exposure > 240:    # Слишком темное или слишком светлое
            return False

    # Контрастность: чем выше, тем лучше
        if contrast < 15:  # Снижаем порог контраста
            return False

        return True


if __name__ == "__main__":
    # Тестовый запуск
    analyzer = VideoAnalyzer()
    print("VideoAnalyzer создан успешно")
