import os
from dotenv import load_dotenv
from supabase import create_client
import logging
from sqlalchemy import create_engine

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    LOCAL_DATABASE_URL = os.environ.get('LOCAL_DATABASE_URL')
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

# データベース接続の設定
def get_db_connection():
    if Config.ENVIRONMENT == 'production':
        return Config.SQLALCHEMY_DATABASE_URI
    return Config.LOCAL_DATABASE_URL

db_connection = get_db_connection()

# Supabaseクライアントの初期化
def init_supabase():
    try:
        return create_client(
            supabase_url=Config.SUPABASE_URL,
            supabase_key=Config.SUPABASE_KEY,
        )
    except Exception as e:
        return None

supabase = init_supabase()