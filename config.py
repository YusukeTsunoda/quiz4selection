import os
import logging
import json
import socket
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def resolve_db_host(host, port=5432):
    """
    IPv6優先でSupabaseホストのDNSを解決
    """
    try:
        # URLからホスト名を抽出
        parsed_url = urlparse(host)
        hostname = parsed_url.hostname or host.replace('https://', '').replace('http://', '')
        
        # もしホスト名がdb.で始まっていなければ追加
        # if not hostname.startswith('db.'):
        #     hostname = f"db.{hostname}"
        
        logger.info(f"Attempting IPv6 resolution for {hostname}")
        # IPv6のみを試行
        addrinfo = socket.getaddrinfo(
            hostname, port,
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP
        )
        ip = addrinfo[0][4][0]
        logger.info(f"Successfully resolved IPv6 address: {ip}")
        # IPv6アドレスを角括弧で囲む（PostgreSQL接続文字列の要件）
        return f"[{ip}]"
    except Exception as e:
        logger.error(f"IPv6 resolution failed: {e}")
        # 解決失敗時は元のホスト名を返す
        return hostname

def test_database_connection(database_uri, engine_options):
    """データベース接続をテストする関数"""
    try:
        engine = create_engine(
            database_uri,
            **engine_options
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
            self.FLASK_ENV = 'production' if os.environ.get('VERCEL_ENV') == 'production' else os.environ.get('FLASK_ENV', 'development')
            
            print(f"FLASK_ENV: {self.FLASK_ENV}")
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

                # IPv6解決を試みる
                resolved_host = resolve_db_host(db_host, int(db_port))
                logger.info(f"Using resolved host: {resolved_host}")

                # 接続文字列を構築
                database_url = f"postgresql://{db_user}:{db_pass}@{resolved_host}:{db_port}/{db_name}"
                
                # 接続設定を更新
                self.SQLALCHEMY_DATABASE_URI = database_url
                self.SQLALCHEMY_ENGINE_OPTIONS.update({
                    'pool_size': 10,
                    'max_overflow': 20,
                    'pool_recycle': 300,
                    'connect_args': {
                        **self.SQLALCHEMY_ENGINE_OPTIONS['connect_args'],
                        'sslmode': 'require',
                        'connect_timeout': 10,  # タイムアウトを少し長めに
                        'keepalives': 1,
                        'keepalives_idle': 30,
                        'keepalives_interval': 10,
                        'keepalives_count': 5,
                        'options': '-c statement_timeout=30000'
                    }
                })

                # 接続テストを実行（修正版）
                logger.info("Testing database connection...")
                if not test_database_connection(self.SQLALCHEMY_DATABASE_URI, self.SQLALCHEMY_ENGINE_OPTIONS):
                    raise ConnectionError("Failed to establish database connection")
            
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
