"""
Video Cutter
"""

__version__ = "0.1.0"
__author__ = "winefg"

#Import basic classes
from .video_analyzer import VideoAnalyzer
from .frame_processor import FrameProcessor
from .fcpx_importer import FCPXImporter

__all__ = ['VideoAnalyzer', 'FrameProcessor', 'FCPXImporter']
