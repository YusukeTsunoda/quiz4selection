import os
from dotenv import load_dotenv
from supabase import create_client, Client
import re

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')
    
    # Supabase設定
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    # データベースURL
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL:
        # postgresからpostgresqlへの変換
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        # ポート番号の変更（5432 → 6543）
        DATABASE_URL = re.sub(r':5432/', ':6543/', DATABASE_URL)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # データベース接続オプション
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 5,  # 接続プールのサイズ
        "max_overflow": 2,  # 最大オーバーフロー数
        "pool_timeout": 30,  # プール接続のタイムアウト（秒）
        "pool_recycle": 1800,  # 接続のリサイクル時間（30分）
        "pool_pre_ping": True,  # 接続前の生存確認
        "connect_args": {
            "sslmode": "require",  # SSL接続を強制
            "connect_timeout": 30,  # 接続タイムアウトを30秒に延長
            "keepalives": 1,  # TCP keepaliveを有効化
            "keepalives_idle": 30,  # アイドル30秒後にkeepalive開始
            "keepalives_interval": 10,  # keepaliveの間隔を10秒に
            "keepalives_count": 5,  # 5回試行後に接続を切断
            "tcp_user_timeout": 30000,  # TCPタイムアウトを30秒に設定
            "options": "-c search_path=public -c statement_timeout=30000",  # タイムアウト設定
            "application_name": "quiz_app"  # アプリケーション名を設定
        }
    }

# Supabaseクライアントの初期化
try:
    supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    supabase = None