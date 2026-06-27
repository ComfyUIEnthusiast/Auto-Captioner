import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'output')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2 GB max upload
    OPENAI_URL = os.environ.get('OPENAI_URL', 'http://127.0.0.1:11434/v1')
    
    # Supported video formats
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv'}
    
    @staticmethod
    def init(app):
        """Initialize directories"""
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.OUTPUT_FOLDER, exist_ok=True)