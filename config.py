import os
from dotenv import load_dotenv
import logging
from supabase import create_client, Client

# ロガーの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')

    # Supabase設定
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    # データベースURL
    DATABASE_URL = os.getenv('DATABASE_URL')

    logger.debug("--- 環境変数の設定 ---")
    logger.debug(f"FLASK_SECRET_KEY: {'設定されています' if SECRET_KEY else '設定されていません'}")
    logger.debug(f"SUPABASE_URL: {SUPABASE_URL}")
    logger.debug(f"SUPABASE_KEY: {'設定されています' if SUPABASE_KEY else '設定されていません (注意: 本番環境では安全な管理をしてください)'}")
    logger.debug(f"DATABASE_URL: {DATABASE_URL}")
    logger.debug("--- 環境変数の設定 完了 ---")

    # DNS解決テストとログ出力
    if DATABASE_URL:
        logger.debug(f"Original DATABASE_URL: {DATABASE_URL}")

        # postgresからpostgresqlへの変換
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            logger.debug(f"After protocol conversion: {DATABASE_URL}")

        try:
            from urllib.parse import urlparse, urlunparse
            import socket

            parsed_url = urlparse(DATABASE_URL)
            host = parsed_url.hostname
            logger.debug(f"Parsed hostname: {host}")
            port = parsed_url.port or 5432
            logger.debug(f"Parsed port: {port}")

            # DNS解決テスト
            try:
                logger.debug("Testing DNS resolution...")

                # IPv4のみの解決を試行
                logger.debug("Attempting IPv4-only resolution...")
                try:
                    addr_info_v4 = socket.getaddrinfo(
                        host,
                        port,
                        socket.AF_INET,
                        socket.SOCK_STREAM,
                        0,
                        socket.AI_ADDRCONFIG
                    )
                    logger.debug(f"IPv4 resolution result: {addr_info_v4}")

                    if addr_info_v4:
                        ipv4_addr = addr_info_v4[0][4][0]
                        logger.debug(f"Selected IPv4 address: {ipv4_addr}")

                        # 接続テスト
                        logger.debug(f"Testing connection to {ipv4_addr}:{port}")
                        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        test_socket.settimeout(5)

                        try:
                            test_socket.connect((ipv4_addr, port))
                            logger.debug("Socket connection test successful")

                            # URLを更新
                            new_netloc = f"{parsed_url.username}:{parsed_url.password}@{ipv4_addr}:{port}"
                            DATABASE_URL = urlunparse((
                                parsed_url.scheme,
                                new_netloc,
                                parsed_url.path,
                                parsed_url.params,
                                parsed_url.query,
                                parsed_url.fragment
                            ))
                            logger.debug(f"Updated DATABASE_URL with IPv4: {DATABASE_URL}")

                        except Exception as e:
                            logger.error(f"Socket connection test failed: {e}", exc_info=True)
                        finally:
                            test_socket.close()
                    else:
                        logger.warning("No IPv4 addresses found")
                except socket.gaierror as e:
                    logger.error(f"IPv4 DNS resolution failed: {e}", exc_info=True)

                # IPv6の解決も試行
                logger.debug("Attempting IPv6 resolution...")
                try:
                    addr_info_v6 = socket.getaddrinfo(
                        host,
                        port,
                        socket.AF_INET6,
                        socket.SOCK_STREAM,
                        0,
                        socket.AI_ADDRCONFIG
                    )
                    logger.debug(f"IPv6 resolution result: {addr_info_v6}")
                    if addr_info_v6:
                        logger.debug("IPv6 address found, but IPv4 is preferred for this test.")
                    else:
                        logger.debug("No IPv6 addresses found.")
                except socket.gaierror as e:
                    logger.debug(f"IPv6 DNS resolution failed: {e}", exc_info=True)

            except Exception as e:
                logger.error(f"Error during DNS resolution or connection test: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error parsing DATABASE_URL: {e}", exc_info=True)
    else:
        logger.error("DATABASE_URL is not set")

    # 基本的な接続設定
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 最小限の接続オプション
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 1,  # 最小限のプールサイズ
        "max_overflow": 0,  # オーバーフローなし
        "connect_args": {
            "sslmode": "disable",
            "connect_timeout": 30,
            "application_name": "quiz_app"
        }
    }

    logger.debug("SQLAlchemy configuration:")
    logger.debug(f"  Database URI: {SQLALCHEMY_DATABASE_URI}")
    logger.debug(f"  Engine options: {SQLALCHEMY_ENGINE_OPTIONS}")

# Supabaseクライアントの初期化
try:
    logger.info("Initializing Supabase client...")
    supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Supabase client: {e}", exc_info=True)
    supabase = None