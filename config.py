import os
from dotenv import load_dotenv
from supabase import create_client
import logging
from sqlalchemy import create_engine

# 環境変数の読み込み
load_dotenv()

class Config:
    # 基本設定
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'your-secret-key'
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
    
    # データベース接続設定
    DATABASE_URL = os.environ.get('DATABASE_URL')
    LOCAL_DATABASE_URL = os.environ.get('LOCAL_DATABASE_URL')
    
    # SQLAlchemy設定
    if ENVIRONMENT == 'production':
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    else:
        SQLALCHEMY_DATABASE_URI = LOCAL_DATABASE_URL
    
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("Database URI is not set. Check your environment variables.")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 1,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 30,
            'application_name': 'quiz_app'
        }
    }
    
    # Supabase設定
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

    @staticmethod
    def init_app(app):
        pass

# Supabaseクライアントの初期化
def init_supabase():
    try:
        return create_client(
            supabase_url=Config.SUPABASE_URL,
            supabase_key=Config.SUPABASE_KEY
        )
    except Exception as e:
        logging.error(f"Failed to initialize Supabase client: {e}")
        return None

# グローバルインスタンスの作成
supabase = init_supabase()

# データベース接続文字列の取得
def get_db_connection():
    return Config.SQLALCHEMY_DATABASE_URI

db_connection = get_db_connection()