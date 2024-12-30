import os
import random
import logging
import sys
from flask import Flask, render_template, session, request, jsonify, flash, redirect, url_for, g
from flask_caching import Cache
from extensions import db
from models import QuizAttempt
from config import Config, db_connection, supabase
from flask_migrate import Migrate
import json
from sqlalchemy import text, create_engine
import socket
import time
from functools import wraps
import uuid
from quiz_data import questions_by_category
import psutil
import traceback
from sqlalchemy import event
from sqlalchemy.engine import Engine

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # 標準出力に出力
)
logger = logging.getLogger('quiz_app')
logger.setLevel(logging.INFO)

# 既存のハンドラをクリア
for handler in logger.handlers:
    logger.removeHandler(handler)

# 標準出力へのハンドラを追加
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

def log_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        request_id = str(uuid.uuid4())
        print(json.dumps({  # printを使用して直接標準出力に出力
            'event': 'function_start',
            'function': func.__name__,
            'request_id': request_id,
            'start_memory_mb': start_memory,
            'timestamp': start_time
        }))
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            duration_ms = (end_time - start_time) * 1000
            memory_diff = end_memory - start_memory
            
            print(json.dumps({  # printを使用して直接標準出力に出力
                'event': 'function_end',
                'function': func.__name__,
                'request_id': request_id,
                'duration_ms': duration_ms,
                'end_memory_mb': end_memory,
                'memory_diff_mb': memory_diff,
                'timestamp': end_time
            }))
            
            return result
            
        except Exception as e:
            end_time = time.time()
            print(json.dumps({  # printを使用して直接標準出力に出力
                'event': 'function_error',
                'function': func.__name__,
                'request_id': request_id,
                'error': str(e),
                'error_type': type(e).__name__,
                'stack_trace': traceback.format_exc(),
                'duration_ms': (end_time - start_time) * 1000,
                'timestamp': end_time
            }))
            raise
            
    return wrapper

# Initialize Flask app
app = Flask(__name__)

# データベースURLの設定
if os.environ.get('VERCEL_ENV') == 'development':
    # 開発環境ではローカルデータベースを使用
    db_uri = os.environ.get('LOCAL_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/quiz_db')
    logger.info("Using LOCAL_DATABASE_URL for development")
else:
    # 本番環境ではDATABASE_URLを使用
    db_uri = os.environ.get('DATABASE_URL')
    if db_uri and db_uri.startswith('postgres://'):
        db_uri = db_uri.replace('postgres://', 'postgresql://', 1)

if not db_uri:
    raise ValueError("Database URI is not set")

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 1,
    'pool_timeout': 30,
    'pool_recycle': 1800,
    'pool_pre_ping': True,
    'connect_args': {
        'connect_timeout': 10,
        'application_name': 'quiz_app',
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
        'sslmode': 'prefer',  # 'require'から'prefer'に変更
        'options': '-c statement_timeout=5000'
    }
}

# IPv4を優先的に使用するための設定
import socket
original_getaddrinfo = socket.getaddrinfo

def getaddrinfo_ipv4_first(*args, **kwargs):
    """IPv4アドレスを優先的に返すようにgetaddrinfoをラップ"""
    responses = original_getaddrinfo(*args, **kwargs)
    if responses:
        # IPv4とIPv6のアドレスを分離
        ipv4_responses = [resp for resp in responses if resp[0] == socket.AF_INET]
        ipv6_responses = [resp for resp in responses if resp[0] == socket.AF_INET6]
        # IPv4を先頭に配置
        return ipv4_responses + ipv6_responses
    return responses

socket.getaddrinfo = getaddrinfo_ipv4_first

# SQLAlchemyのイベントリスナーを設定
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', time.time())
    logger.info(json.dumps({
        'event': 'query_start',
        'statement': statement,
        'parameters': str(parameters),
        'timestamp': time.time()
    }))

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info.pop('query_start_time')
    logger.info(json.dumps({
        'event': 'query_complete',
        'statement': statement,
        'duration_ms': total * 1000,
        'timestamp': time.time()
    }))

# 残りの設定を読み込む
app.config.from_object(Config)

# Initialize cache
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

@log_performance
def check_db_connection():
    try:
        # 環境変数から直接ホスト名を取得
        if os.environ.get('VERCEL_ENV') == 'development':
            db_host = 'localhost'
        else:
            db_uri = os.environ.get('DATABASE_URL', '')
            db_host = db_uri.split('@')[1].split('/')[0].split(':')[0] if '@' in db_uri else ''
        
        if not db_host:
            logger.error(json.dumps({
                'event': 'db_host_error',
                'error': 'Database host is not set',
                'timestamp': time.time()
            }))
            return False
        
        # IPv4/IPv6アドレス解決の詳細ログ
        try:
            addrinfo = socket.getaddrinfo(
                db_host,
                5432,
                socket.AF_INET,  # IPv4のみを使用
                socket.SOCK_STREAM
            )
            logger.error(json.dumps({
                'event': 'address_resolution',
                'host': db_host,
                'resolved_addresses': [{
                    'family': 'IPv4',
                    'ip': addr[4][0],
                    'port': addr[4][1]
                } for addr in addrinfo],
                'timestamp': time.time()
            }))
        except socket.gaierror as e:
            logger.error(json.dumps({
                'event': 'address_resolution_error',
                'host': db_host,
                'error': str(e),
                'timestamp': time.time()
            }))
            return False
        
        # 接続試行の詳細ログ
        logger.error(json.dumps({
            'event': 'db_connection_attempt',
            'connection_details': {
                'host': db_host,
                'port': 5432,
                'ssl_mode': app.config['SQLALCHEMY_ENGINE_OPTIONS']['connect_args'].get('sslmode'),
                'timeout': app.config['SQLALCHEMY_ENGINE_OPTIONS']['connect_args'].get('connect_timeout'),
                'socket_options': {
                    'keepalive': app.config['SQLALCHEMY_ENGINE_OPTIONS']['connect_args'].get('keepalives'),
                    'keepalive_idle': app.config['SQLALCHEMY_ENGINE_OPTIONS']['connect_args'].get('keepalives_idle'),
                    'ip_version': 'IPv4'
                }
            },
            'timestamp': time.time()
        }))
        
        with db.session.begin():
            start_time = time.time()
            db.session.execute(text("SELECT 1"))
            duration = time.time() - start_time
            
            logger.info(json.dumps({
                'event': 'db_connection_success',
                'duration_ms': duration * 1000,
                'timestamp': time.time()
            }))
            return True
    except Exception as e:
        logger.error(json.dumps({
            'event': 'db_connection_error',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'connection_details': {
                'host': db_host,
                'port': 5432,
                'engine_options': app.config['SQLALCHEMY_ENGINE_OPTIONS'],
                'socket_error': str(e) if isinstance(e, socket.error) else None
            },
            'timestamp': time.time()
        }))
        return False

@app.before_request
def before_request():
    g.request_start_time = time.time()
    g.request_id = str(uuid.uuid4())
    
    try:
        db_host = app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1].split('/')[0].split(':')[0]
        ip_address = socket.gethostbyname(db_host)
        logger.error(json.dumps({
            'event': 'connection_check',
            'request_id': g.request_id,
            'dns_resolution': {
                'host': db_host,
                'resolved_ip': ip_address
            },
            'timestamp': time.time()
        }))
    except Exception as e:
        logger.error(json.dumps({
            'event': 'dns_resolution_error',
            'request_id': g.request_id,
            'error': str(e),
            'timestamp': time.time()
        }))
    
    if not check_db_connection():
        logger.error(json.dumps({
            'event': 'database_connection_failed',
            'request_id': g.request_id,
            'error_details': {
                'host': db_host,
                'port': 5432,
                'engine_options': app.config['SQLALCHEMY_ENGINE_OPTIONS']
            },
            'timestamp': time.time()
        }))
        return "Database connection error", 500

@app.after_request
def after_request(response):
    if hasattr(g, 'request_start_time'):
        duration = time.time() - g.request_start_time
        
        # エラーレスポンスの場合のみログを出力
        if response.status_code >= 400:
            logger.error(json.dumps({
                'event': 'error_response',
                'request_id': getattr(g, 'request_id', 'unknown'),
                'path': request.path,
                'method': request.method,
                'status_code': response.status_code,
                'duration_ms': duration * 1000,
                'timestamp': time.time()
            }))
        
        # 処理時間が長い場合の警告
        if duration > 5:
            logger.warning(json.dumps({
                'event': 'long_request_warning',
                'request_id': getattr(g, 'request_id', 'unknown'),
                'path': request.path,
                'method': request.method,
                'duration_ms': duration * 1000,
                'timestamp': time.time()
            }))
    
    return response

@app.errorhandler(504)
def gateway_timeout(error):
    error_time = time.time()
    logger.error(json.dumps({
        'event': 'gateway_timeout',
        'request_id': getattr(g, 'request_id', 'unknown'),
        'path': request.path,
        'method': request.method,
        'error': str(error),
        'database_uri': app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1] if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else 'masked',
        'engine_options': app.config['SQLALCHEMY_ENGINE_OPTIONS'],
        'connection_error_details': {
            'host': app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1].split('/')[0].split(':')[0],
            'port': 5432,
            'timeout_settings': {
                'connect_timeout': app.config['SQLALCHEMY_ENGINE_OPTIONS']['connect_args'].get('connect_timeout'),
                'pool_timeout': app.config['SQLALCHEMY_ENGINE_OPTIONS'].get('pool_timeout')
            }
        },
        'timestamp': error_time
    }))
    return "Gateway Timeout - The server took too long to respond", 504

@app.errorhandler(500)
def internal_server_error(error):
    logger.error(json.dumps({
        'event': 'internal_server_error',
        'request_id': getattr(g, 'request_id', 'unknown'),
        'error_type': type(error).__name__,
        'error_message': str(error),
        'path': request.path,
        'method': request.method,
        'traceback': traceback.format_exc(),
        'database_config': {
            'host': app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1].split('/')[0].split(':')[0],
            'engine_options': app.config['SQLALCHEMY_ENGINE_OPTIONS']
        },
        'timestamp': time.time()
    }))
    return "Internal Server Error", 500

# データベーステーブルの作成（キャッシュ付き）
@cache.memoize(timeout=3600)
def create_database_tables():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        return False

# データベース接続テストを実行
def test_database_connection():
    try:
        logger.info("Starting database connection test...")
        start_time = time.time()
        
        # 環境変数の確認
        logger.info(json.dumps({
            'event': 'environment_check',
            'database_url': bool(os.environ.get('DATABASE_URL')),
            'local_database_url': bool(os.environ.get('LOCAL_DATABASE_URL')),
            'environment': os.environ.get('ENVIRONMENT', 'development'),
            'sqlalchemy_database_uri': bool(app.config.get('SQLALCHEMY_DATABASE_URI')),
            'timestamp': time.time()
        }))

        # データベースURIの解析
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        try:
            # URIからホスト情報を抽出
            uri_parts = db_uri.split('@')[1].split('/')
            db_host = uri_parts[0].split(':')[0]
            db_port = uri_parts[0].split(':')[1] if ':' in uri_parts[0] else '5432'
            db_name = uri_parts[1].split('?')[0] if '?' in uri_parts[1] else uri_parts[1]
            
            logger.info(json.dumps({
                'event': 'database_uri_parse',
                'host': db_host,
                'port': db_port,
                'database': db_name,
                'timestamp': time.time()
            }))
        except Exception as e:
            logger.error(json.dumps({
                'event': 'database_uri_parse_error',
                'error': str(e),
                'uri': db_uri.split('@')[1] if '@' in db_uri else 'invalid_uri',
                'timestamp': time.time()
            }))

        # DNS解決のテスト（複数の方法で試行）
        try:
            # 方法1: socket.gethostbyname
            ip_address = socket.gethostbyname(db_host)
            logger.info(json.dumps({
                'event': 'dns_resolution_socket',
                'method': 'gethostbyname',
                'host': db_host,
                'ip': ip_address,
                'duration_ms': (time.time() - start_time) * 1000
            }))
            
            # 方法2: socket.getaddrinfo
            addr_info = socket.getaddrinfo(
                db_host,
                int(db_port),
                socket.AF_UNSPEC,
                socket.SOCK_STREAM
            )
            logger.info(json.dumps({
                'event': 'dns_resolution_addrinfo',
                'host': db_host,
                'addresses': [{
                    'family': 'IPv6' if addr[0] == socket.AF_INET6 else 'IPv4',
                    'ip': addr[4][0],
                    'port': addr[4][1]
                } for addr in addr_info],
                'timestamp': time.time()
            }))
        except socket.gaierror as e:
            logger.error(json.dumps({
                'event': 'dns_resolution_error',
                'host': db_host,
                'error_code': e.errno,
                'error_message': str(e),
                'timestamp': time.time()
            }))

        # TCP接続テスト（タイムアウト付き）
        try:
            for family, socktype, proto, canonname, sockaddr in socket.getaddrinfo(
                db_host, int(db_port), socket.AF_UNSPEC, socket.SOCK_STREAM
            ):
                try:
                    sock = socket.socket(family, socktype, proto)
                    sock.settimeout(5)
                    start_connect = time.time()
                    sock.connect(sockaddr)
                    logger.info(json.dumps({
                        'event': 'tcp_connection_success',
                        'host': db_host,
                        'port': db_port,
                        'ip': sockaddr[0],
                        'family': 'IPv6' if family == socket.AF_INET6 else 'IPv4',
                        'duration_ms': (time.time() - start_connect) * 1000,
                        'timestamp': time.time()
                    }))
                    sock.close()
                    break
                except socket.error as e:
                    logger.error(json.dumps({
                        'event': 'tcp_connection_error',
                        'host': db_host,
                        'port': db_port,
                        'ip': sockaddr[0],
                        'family': 'IPv6' if family == socket.AF_INET6 else 'IPv4',
                        'error_code': e.errno if hasattr(e, 'errno') else None,
                        'error_message': str(e),
                        'timestamp': time.time()
                    }))
        except socket.gaierror as e:
            logger.error(json.dumps({
                'event': 'tcp_connection_dns_error',
                'host': db_host,
                'port': db_port,
                'error_code': e.errno,
                'error_message': str(e),
                'timestamp': time.time()
            }))

        # データベース接続テスト
        if check_db_connection():
            logger.info("Database connection test completed successfully")
            return True
        else:
            logger.error("Database connection test failed")
            return False

    except Exception as e:
        logger.error(json.dumps({
            'event': 'database_test_error',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'timestamp': time.time()
        }))
        return False

# アプリケーションの初期化
def init_app():
    """アプリケーションの初期化処理"""
    try:
        # データベース接続テストを実行
        if not test_database_connection():
            logger.error("Database connection test failed during initialization")
            if os.environ.get('ENVIRONMENT') != 'production':
                # 開発環境では警告のみ
                logger.warning("Continuing with application startup despite database connection failure")
            else:
                # 本番環境では起動を中止
                raise RuntimeError("Database connection failed in production environment")
        
        # データベーステーブルの作成
        if not create_database_tables():
            logger.error("Failed to create database tables")
            if os.environ.get('ENVIRONMENT') != 'production':
                logger.warning("Continuing with application startup despite table creation failure")
            else:
                raise RuntimeError("Database table creation failed in production environment")
                
        logger.info("Application initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Application initialization failed: {e}")
        if os.environ.get('ENVIRONMENT') == 'production':
            raise
        else:
            logger.warning("Continuing with application startup despite initialization failure")

# 直接実行時の処理
if __name__ == '__main__':
    # アプリケーションコンテキスト内での初期化
    with app.app_context():
        init_app()
        
    try:
        port = int(os.environ.get('PORT', 5002))
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

@app.route('/')
def index():
    """
    ルートページのハンドラ
    学年選択ページにリダイレクト
    """
    return redirect(url_for('grade_select'))

@app.route('/grade_select')
def grade_select():
    """
    学年選択ページを表示
    """
    return render_template('grade_select.html')
