import os
import logging
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# ロガーの設定
logger = logging.getLogger(__name__)

def is_development():
    """開発環境かどうかを判定"""
    return os.getenv('IS_DEVELOPMENT', 'true').lower() == 'true'

class Config:
    """アプリケーション設定"""
    def __init__(self):
        # PostgreSQL接続設定
        self.SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/quiz4selection')
        logger.info(f"Using PostgreSQL database: {self.SQLALCHEMY_DATABASE_URI}")
            
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
        self.DEBUG = is_development()

# ダミーのSupabaseクライアント
class DummySupabaseClient:
    class Auth:
        def sign_up(self, credentials):
            logger.info(f"Dummy signup for email: {credentials.get('email')}")
            return type('User', (), {'id': f"dev-{credentials['email']}"})()
        
        def sign_in_with_password(self, credentials):
            logger.info(f"Dummy sign in for email: {credentials.get('email')}")
            return type('User', (), {'id': f"dev-{credentials['email']}"})()
        
        def sign_out(self):
            logger.info("Dummy sign out")
            pass
        
        def reset_password_email(self, email):
            logger.info(f"Dummy password reset for email: {email}")
            pass
    
    auth = Auth()

# Supabaseのダミークライアントを使用
supabase = DummySupabaseClient()
