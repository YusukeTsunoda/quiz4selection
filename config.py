import os
import logging
import json
import socket
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def resolve_db_host(host, port=5432):
    """
    IPv4優先でデータベースホストのDNSを解決。
    IPv4が使えない場合はIPv6にフォールバック。
    """
    try:
        # まずIPv4を試す
        logger.info(f"Attempting IPv4 resolution for {host}")
        addrinfo = socket.getaddrinfo(
            host, port,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM
        )
        ip = addrinfo[0][4][0]
        logger.info(f"Successfully resolved IPv4 address: {ip}")
        return ip
    except socket.gaierror as e:
        logger.warning(f"IPv4 resolution failed: {e}, trying IPv6")
        try:
            # IPv4が失敗したらIPv6を試す
            addrinfo = socket.getaddrinfo(
                host, port,
                family=socket.AF_INET6,
                type=socket.SOCK_STREAM
            )
            ip = addrinfo[0][4][0]
            logger.info(f"Successfully resolved IPv6 address: {ip}")
            return ip
        except socket.gaierror as e:
            logger.error(f"Both IPv4 and IPv6 resolution failed: {e}")
            raise

def test_database_connection(app):
    """データベース接続をテストする関数"""
    try:
        engine = create_engine(
            app.config['SQLALCHEMY_DATABASE_URI'],
            **app.config['SQLALCHEMY_ENGINE_OPTIONS']
        )
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection test successful")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in database connection test: {e}")
        return False

class Config:
    """アプリケーションの設定クラス"""
    # セッション設定
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    
    # 環境設定
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    VERCEL_ENV = os.environ.get('VERCEL_ENV')
    
    # データベース基本設定
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLAlchemy接続プール設定
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'application_name': 'quiz4selection',
            'options': '-c statement_timeout=30000'
        }
    }
    
    def __init__(self):
        try:
            # データベースURLの設定
            if self.FLASK_ENV == 'development' or self.VERCEL_ENV == 'development':
                logger.info("Using LOCAL_DATABASE_URL for development")
                database_url = os.environ.get('LOCAL_DATABASE_URL')
                if not database_url:
                    raise ValueError("LOCAL_DATABASE_URL is not set in development environment")
                self.SQLALCHEMY_DATABASE_URI = database_url
            else:
                logger.info("Using DATABASE_URL for production")
                # データベース接続情報を環境変数から取得
                db_user = os.environ.get('POSTGRES_USER', 'postgres')
                db_pass = os.environ.get('POSTGRES_PASSWORD')
                db_name = os.environ.get('POSTGRES_DATABASE')
                db_host = os.environ.get('NEXT_PUBLIC_SUPABASE_URL')
                db_port = os.environ.get('POSTGRES_PORT', '5432')

                if not all([db_pass, db_name, db_host]):
                    raise ValueError("Required database environment variables are not set")

                # DNS解決でIPアドレスを取得
                resolved_host = resolve_db_host(db_host, int(db_port))
                
                # 接続文字列を構築
                database_url = f"postgresql://{db_user}:{db_pass}@{resolved_host}:{db_port}/{db_name}"
                
                # PostgreSQL URLの修正（必要な場合）
                if database_url.startswith('postgres://'):
                    database_url = database_url.replace('postgres://', 'postgresql://', 1)
                
                self.SQLALCHEMY_DATABASE_URI = database_url
                
                # 本番環境での追加の接続設定
                self.SQLALCHEMY_ENGINE_OPTIONS.update({
                    'pool_size': 10,
                    'max_overflow': 20,
                    'pool_recycle': 300,
                    'connect_args': {
                        **self.SQLALCHEMY_ENGINE_OPTIONS['connect_args'],
                        'sslmode': 'require',
                        'connect_timeout': 5
                    }
                })
            
            # 環境に応じたデバッグ設定
            self.DEBUG = self.FLASK_ENV == 'development'
            self.DEVELOPMENT = self.FLASK_ENV == 'development'
            
            # 設定状態のログ出力（機密情報を除外）
            logger.info(json.dumps({
                'event': 'database_config',
                'is_production': not self.DEVELOPMENT,
                'database_url_set': bool(self.SQLALCHEMY_DATABASE_URI),
                'engine_options': {
                    k: v for k, v in self.SQLALCHEMY_ENGINE_OPTIONS.items()
                    if k != 'connect_args'
                }
            }))
            
        except Exception as e:
            logger.error(f"Error in Config initialization: {e}")
            raise

# Supabaseクライアントの初期化
try:
    logger.info("Initializing Supabase client...")
    if os.environ.get('NEXT_PUBLIC_SUPABASE_URL') and os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY'):
        from supabase import create_client
        supabase = create_client(
            os.environ.get('NEXT_PUBLIC_SUPABASE_URL'),
            os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY')
        )
    else:
        logger.error("Failed to initialize Supabase client: supabase_url is required")
        supabase = None
except Exception as e:
    logger.error(f"Error initializing Supabase client: {e}")
    supabase = None
