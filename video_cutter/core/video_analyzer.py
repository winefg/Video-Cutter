import os
import cv2
import numpy as np
import logging
from typing import List, Dict
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
                metrics = self.frame_processor.process_frame(frame, 
frame_count)
                
                # Проверяем, хороший ли кадр
                if self.is_good_frame(metrics):
                    good_frames.append({
                        'frame_number': frame_count,
                        'timestamp': frame_count / 30,  # Предполагаем 30 FPS
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
        
        logger.info(f"Анализ завершен. Найдено {len(good_frames)} хороших 
кадров из {frame_count}")
        return good_frames
    
    def is_good_frame(self, metrics: Dict) -> bool:
        """
        Определяет, хороший ли кадр по метрикам
        
        :param metrics: словарь с метриками кадра
        :return: True если кадр хороший
        """
        # Проверяем размытие (меньше = хуже)
        if 'blur' in metrics and metrics['blur'] < self.min_blur_threshold:
            return False
            
        # Проверяем экспозицию
        if 'exposure' in metrics and metrics['exposure'] < 
self.min_exposure_threshold:
            return False
            
        # Проверяем контрастность (простая проверка)
        if 'contrast' in metrics and metrics['contrast'] < 10:
            return False
            
        return True

if __name__ == "__main__":
    # Тестовый запуск
    analyzer = VideoAnalyzer()
    print("VideoAnalyzer создан успешно")
