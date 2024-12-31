import os
import socket
import logging
from dotenv import load_dotenv

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 環境変数の読み込み
load_dotenv()

def resolve_db_host(host, port=5432):
    """Supabaseホストの DNS 解決 - IPv6専用版"""
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(host)
        hostname = parsed_url.hostname or host
        logger.info(f"Attempting to resolve: {hostname}")

        # IPv6のみを使用するように設定
        addrinfo = socket.getaddrinfo(
            hostname,
            port,
            family=socket.AF_INET6,  # IPv6のみ
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
            flags=socket.AI_ADDRCONFIG  # IPv4マッピングを無効化
        )
        
        if not addrinfo:
            logger.error("No IPv6 addresses found")
            return hostname

        ip = addrinfo[0][4][0]
        logger.info(f"Resolved IPv6: {ip}")
        # IPv6アドレスは常に括弧で囲む
        return f"[{ip}]"

    except socket.gaierror as e:
        logger.error(f"IPv6 DNS resolution error: {e}")
        return hostname
    except Exception as e:
        logger.error(f"Unexpected error in IPv6 resolution: {e}")
        return hostname

class Config:
    """アプリケーション設定クラス"""
    def __init__(self):
        # 基本設定
        self.FLASK_ENV = os.getenv('FLASK_ENV', 'development')
        self.DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'
        self.SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev_key_for_quiz_app')

        # データベース設定
        if self.FLASK_ENV == 'development':
            # 開発環境用の設定
            self.SQLALCHEMY_DATABASE_URI = os.getenv('LOCAL_DATABASE_URL')
            self.SQLALCHEMY_ENGINE_OPTIONS = {
                "pool_pre_ping": True,
                "pool_recycle": 300,
            }
        else:
            # 本番環境（Supabase）用の設定
            db_user = os.getenv('POSTGRES_USER')
            db_password = os.getenv('POSTGRES_PASSWORD')
            db_host = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
            db_port = os.getenv('POSTGRES_PORT', '5432')
            db_name = os.getenv('POSTGRES_DATABASE')
            self.SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')

            # IPv6アドレスの解決
            resolved_host = resolve_db_host(db_host, int(db_port))
            
            # データベースURLの構築
            self.SQLALCHEMY_DATABASE_URI = f"postgresql://{db_user}:{db_password}@{resolved_host}:{db_port}/{db_name}"
            
            # 本番環境用のエンジンオプション
            self.SQLALCHEMY_ENGINE_OPTIONS = {
                "pool_pre_ping": True,
                "pool_recycle": 300,
                "connect_args": {
                    "sslmode": "require"
                }
            }

        # 共通設定
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
