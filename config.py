import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# ロガーの設定
logger = logging.getLogger(__name__)

def is_development():
    """開発環境かどうかを判定"""
    env = os.getenv('FLASK_ENV')
    logger.info(f"Current environment: {env}")
    return env == 'development'

class Config:
    """アプリケーション設定"""
    def __init__(self):
        if is_development():
            # 開発環境ではローカルのPostgreSQLを使用
            self.SQLALCHEMY_DATABASE_URI = os.getenv('LOCAL_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/quiz4selection')
            logger.info("Using local database configuration")
        else:
            # 本番環境ではSupabaseを使用
            db_url = os.getenv('DATABASE_URL')
            if db_url and '?' not in db_url:
                db_url += '?options=-c search_path=public'
            self.SQLALCHEMY_DATABASE_URI = db_url
            logger.info("Using production database configuration")
            
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
        self.DEBUG = is_development()

# Supabaseクライアントの初期化
if is_development():
    # 開発環境ではダミーのクライアントを使用
    logger.info("Initializing dummy Supabase client for development")
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
    
    supabase = DummySupabaseClient()
else:
    # 本番環境では実際のSupabaseクライアントを使用
    logger.info("Initializing production Supabase client")
    
    # 環境変数の確認
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    logger.info(f"Supabase URL exists: {bool(supabase_url)}")
    logger.info(f"Supabase key exists: {bool(supabase_key)}")
    logger.info(f"Supabase key length: {len(supabase_key) if supabase_key else 0}")
    logger.info(f"Environment variables: {dict(filter(lambda item: 'SUPABASE' in item[0], os.environ.items()))}")

    if not supabase_url or not supabase_key:
        error_msg = "SUPABASE_URL and SUPABASE_KEY must be set in production environment"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        logger.info("Supabase client created successfully")
    except Exception as e:
        logger.error(f"Error creating Supabase client: {str(e)}")
        raise
