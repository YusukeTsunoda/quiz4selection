import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def is_development():
    """開発環境かどうかを判定"""
    return os.getenv('FLASK_ENV') == 'development'

class Config:
    """アプリケーション設定"""
    def __init__(self):
        if os.getenv('FLASK_ENV') == 'development':
            self.SQLALCHEMY_DATABASE_URI = os.getenv('LOCAL_DATABASE_URL')
        else:
            self.SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
        self.DEBUG = is_development()

# Supabaseクライアントの初期化
supabase: Client = create_client(
    os.getenv('SUPABASE_URL', ''),
    os.getenv('SUPABASE_KEY', '')
)
