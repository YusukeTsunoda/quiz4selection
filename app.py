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
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import logging
from logging.config import dictConfig
from models import db, User, QuizAttempt
from config import Config
from urllib.parse import urlparse

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
    db_uri = os.environ.get('LOCAL_DATABASE_URL')
    if not db_uri:
        logger.error("LOCAL_DATABASE_URL is not set for development environment")
        raise ValueError("LOCAL_DATABASE_URL is required in development environment")
    logger.info("Using LOCAL_DATABASE_URL for development")
else:
    # 本番環境ではDATABASE_URLを使用
    db_uri = os.environ.get('DATABASE_URL')
    if not db_uri:
        logger.error("DATABASE_URL is not set for production environment")
        raise ValueError("DATABASE_URL is required in production environment")
    
    # URLの形式を確認して修正
    if db_uri.startswith('postgres://'):
        db_uri = db_uri.replace('postgres://', 'postgresql://', 1)
        logger.info("Converted postgres:// to postgresql:// in DATABASE_URL")

# データベース接続設定の詳細をログ出力（機密情報を除く）
parsed_uri = urlparse(db_uri)
logger.info(json.dumps({
    'event': 'database_configuration',
    'host': parsed_uri.hostname,
    'port': parsed_uri.port or 5432,
    'database': parsed_uri.path.lstrip('/'),
    'ssl_mode': 'prefer',
    'application_name': 'quiz_app'
}))

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
        'sslmode': 'prefer',
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

@app.route('/grade/<int:grade>/category')
def select_category(grade):
    """
    カテゴリー選択ページを表示
    """
    if grade < 1 or grade > 6:
        flash('Invalid grade selected')
        return redirect(url_for('grade_select'))
    
    return render_template('category_select.html', grade=grade)

<<<<<<< HEAD
@app.route('/grade/<int:grade>/category/<category>/subcategory')
def select_subcategory(grade, category):
    subcategories = get_subcategories(grade, category)
    return render_template('subcategory_select.html',
                         grade=grade,
                         category=category,
                         category_name=CATEGORY_NAMES[category],
                         subcategories=subcategories,
                         subcategory_names=SUBCATEGORY_NAMES)

@app.route('/grade/<int:grade>/category/<category>/subcategory/<subcategory>/difficulty')
def select_difficulty(grade, category, subcategory):
    """難易度選択画面を表示する"""
    try:
        logger.info(f"Entering select_difficulty with grade={grade}, category={category}, subcategory={subcategory}")
        
        # 問題データの存在確認
        file_path = f'quiz_data/grade_{grade}/{category}.json'
        logger.info(f"Checking file: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            flash('問題データが見つかりません。', 'error')
            return redirect(url_for('grade_select'))

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Loaded data keys: {list(data.keys())}")
            
            if subcategory not in data:
                logger.error(f"Subcategory {subcategory} not found in data")
                flash('選択されたカテゴリーの問題が見つかりません。', 'error')
                return redirect(url_for('grade_select'))
            
            logger.info(f"Found subcategory {subcategory} in data")
            logger.info(f"Available difficulties in {subcategory}: {list(data[subcategory].keys())}")

        # 各難易度のクイズ統計を取得
        stats = {}
        for difficulty in ['easy', 'medium', 'hard']:
            logger.info(f"Getting stats for difficulty: {difficulty}")
            stats[difficulty] = QuizAttempt.get_stats(grade, category, subcategory, difficulty)
            logger.info(f"Stats for {difficulty}: {stats[difficulty]}")
            
        logger.info("Preparing to render template with context:")
        logger.info(f"grade: {grade}")
        logger.info(f"category: {category}")
        logger.info(f"subcategory: {subcategory}")
        logger.info(f"category_name: {CATEGORY_NAMES.get(category)}")
        logger.info(f"subcategory_name: {SUBCATEGORY_NAMES.get(subcategory)}")
        logger.info(f"stats: {stats}")
        
        return render_template('difficulty_select.html',
                             grade=grade,
                             category=category,
                             subcategory=subcategory,
                             stats=stats,
                             category_name=CATEGORY_NAMES[category],
                             subcategory_name=SUBCATEGORY_NAMES[subcategory])
    except Exception as e:
        logger.error(f"Error in select_difficulty: {e}")
        logger.exception("Full traceback:")
        flash('難易度選択画面の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('select_grade'))

def get_questions(grade, category, subcategory, difficulty):
    """指定された件に基づいて問題を取得する"""
    try:
        logger.info(f"Getting questions for grade={grade}, category={category}, subcategory={subcategory}, difficulty={difficulty}")
        
        # 問題データを取得
        questions, error = get_quiz_data(grade, category, subcategory, difficulty)
        if error:
            logger.error(f"Error getting quiz data: {error}")
            return []
        if not questions:
            logger.error("No questions returned from get_quiz_data")
            return []
            
        logger.info(f"Retrieved {len(questions)} questions from quiz data")
            
        # 問題をランダムに選択し、10問を選択
        if len(questions) > 10:
            selected_questions = random.sample(questions, 10)
            logger.info(f"Selected 10 random questions from {len(questions)} available questions")
        else:
            selected_questions = questions
            logger.info(f"Using all {len(questions)} available questions")
        
        return selected_questions
    except Exception as e:
        logger.error(f"Error in get_questions: {e}")
        logger.exception("Full traceback:")
        return []

@app.route('/start_quiz/<int:grade>/<category>/<subcategory>/<difficulty>')
def start_quiz(grade, category, subcategory, difficulty):
    """クイズを開始する"""
    try:
        # デバッグログを追加
        logger.info(f"Starting quiz with parameters:")
        logger.info(f"Grade: {grade}")
        logger.info(f"Category: {category}")
        logger.info(f"Subcategory: {subcategory}")
        logger.info(f"Difficulty: {difficulty}")
        
        # セッションをクリア
        session.clear()
        logger.info("Session cleared")
        
        # 問題を取得
        questions = get_questions(grade, category, subcategory, difficulty)
        logger.info(f"Retrieved {len(questions) if questions else 0} questions")
        
        if not questions:
            logger.error("No questions retrieved")
            flash('問題の取得に失敗しました。', 'error')
            return redirect(url_for('select_difficulty', grade=grade, category=category, subcategory=subcategory))
            
        logger.info(f"Starting quiz with {len(questions)} questions")
        logger.info(f"Question categories: {category}, {subcategory}, {difficulty}")
            
        # セッションに情報を保存
        session['questions'] = questions
        session['current_question'] = 0
        session['score'] = 0
        session['quiz_history'] = []
        session['grade'] = grade
        session['category'] = category
        session['subcategory'] = subcategory
        session['difficulty'] = difficulty
        logger.info("Session data saved")
        
        # 最初の問題を表示
        logger.info("Rendering first question")
        return render_template('quiz.html',
                            question=questions[0],
                            question_number=1,
                            total_questions=len(questions),
                            correct_answers=0)
        
    except Exception as e:
        logger.error(f"Error in start_quiz: {e}")
        logger.exception("Full traceback:")
        flash('クイズの開始中にエラーが発生しました。', 'error')
        return redirect(url_for('select_difficulty', grade=grade, category=category, subcategory=subcategory))

def get_subcategories(grade, category):
    """定された学年とカテゴリのサブカテゴリを取得"""
    # カテゴリに応じたサブカテゴリのマッピング
    category_subcategories = {
        'japanese': ['kanji', 'reading', 'grammar', 'writing'],
        'math': ['calculation', 'figure', 'measurement', 'graph'],
        'science': ['physics', 'chemistry', 'biology', 'earth_science'],
        'society': ['history', 'geography', 'civics', 'current_events', 'prefectures']
    }
    return category_subcategories.get(category, [])

def get_quiz_data(grade, category, subcategory, difficulty):
    """クイズデータを取得する関数"""
    try:
        file_path = f'quiz_data/grade_{grade}/{category}.json'
        logger.info(f"Loading quiz data from: {file_path}")
        
        # ファイルの存在確認
        if not os.path.exists(file_path):
            logger.error(f"Quiz data file not found: {file_path}")
            return None, "問題データファイルが見つかりません"
            
        # ファイルの読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Successfully loaded JSON data")
            logger.info(f"Available subcategories: {list(data.keys())}")
            
            # サブカテゴリの確認
            if subcategory not in data:
                logger.error(f"Subcategory {subcategory} not found in data")
                return None, "選択されたサブカテゴリーの問題が見つかりません"
                
            logger.info(f"Found subcategory {subcategory}")
            logger.info(f"Available difficulties: {list(data[subcategory].keys())}")
                
            # 難易度の確認
            if difficulty not in data[subcategory]:
                logger.error(f"Difficulty {difficulty} not found in {subcategory}")
                return None, "選択された難易度の問題が見つかりません"
                
            all_questions = data[subcategory][difficulty]
            if not all_questions:
                logger.error(f"No questions found for {category}/{subcategory}/{difficulty}")
                return None, "問題が見つかりません"
            
            # 利用可能な問題数を確認
            num_questions = len(all_questions)
            target_questions = min(10, num_questions)  # 10問または利用可能な全問題数の少ない方
            
            logger.info(f"Total available questions: {num_questions}")
            logger.info(f"Target number of questions: {target_questions}")
            
            # 問題をランダムに選択
            selected_questions = random.sample(all_questions, target_questions)
            
            # 各問題の選択肢をシャッフル
            shuffled_questions = [get_shuffled_question(q) for q in selected_questions]
            
            logger.info(f"Successfully loaded and shuffled {len(shuffled_questions)} questions")
            for i, q in enumerate(shuffled_questions):
                logger.info(f"Question {i+1} correct index: {q['correct']}")
            
            return shuffled_questions, None
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return None, "問題データの形式が正しくありません"
    except Exception as e:
        logger.error(f"Error in get_quiz_data: {e}")
        logger.exception("Full traceback:")
        return None, "問題データの読み込み中にエラーが発生しました"

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    try:
        data = request.get_json()
        selected_index = data.get('selected')
        time_taken = data.get('time_taken', 0)
        
        current_question = session.get('current_question', 0)
        questions = session.get('questions', [])
        current_score = session.get('score', 0)
        quiz_history = session.get('quiz_history', [])
        
        # 受信データのログ
        logger.info(f"Received answer - Selected Index: {selected_index}, Type: {type(selected_index)}")
        logger.info(f"Current Question State - Number: {current_question + 1}, Total: {len(questions)}")
        
        if current_question >= len(questions):
            logger.error("Question index out of range")
            return jsonify({'success': False, 'error': '問題が見つかりません'})
            
        question = questions[current_question]
        correct_index = question['correct']
        
        # インデックスの比較前の型と値を確認
        logger.info(f"Comparing indices - Selected: {selected_index} ({type(selected_index)}), Correct: {correct_index} ({type(correct_index)})")
        is_correct = str(selected_index) == str(correct_index)
        logger.info(f"Answer is correct: {is_correct}")
        
        # 最後の問題かどうかを確認
        is_last_question = current_question >= len(questions) - 1
        logger.info(f"Question check - Current: {current_question + 1}, Total: {len(questions)}, Is Last: {is_last_question}")
        
        # スコアの更新
        if is_correct:
            current_score += 1
            session['score'] = current_score
            logger.info(f"Score updated - New score: {current_score}")
            
        # 履歴の保存
        quiz_history.append({
            'question': question['question'],
            'selected_option': question['options'][int(selected_index)],
            'correct_option': question['options'][int(correct_index)],
            'is_correct': is_correct,
            'time_taken': time_taken
        })
        session['quiz_history'] = quiz_history
        logger.info(f"Quiz history updated - Total entries: {len(quiz_history)}")
        
        # 最後の問題の場合、QuizAttemptを保存
        if is_last_question:
            try:
                quiz_attempt = QuizAttempt(
                    grade=session.get('grade'),
                    category=session.get('category'),
                    subcategory=session.get('subcategory'),
                    difficulty=session.get('difficulty'),
                    score=current_score,
                    total_questions=len(questions),
                    quiz_history=quiz_history
                )
                db.session.add(quiz_attempt)
                db.session.commit()
                logger.info(f"Quiz attempt saved - Final score: {current_score}/{len(questions)}")
            except Exception as e:
                logger.error(f"Error saving quiz attempt: {e}")
                db.session.rollback()
        
        # レスポンスデータの準備
        response_data = {
            'success': True,
            'isCorrect': is_correct,
            'currentScore': current_score,
            'isLastQuestion': is_last_question
        }
        
        # 最後の問題の場合、リダイレクトURLを設定
        if is_last_question:
            try:
                response_data['redirectUrl'] = '/result'
                logger.info(f"Last question - Setting redirect URL: {response_data['redirectUrl']}")
            except Exception as e:
                logger.error(f"Error setting redirect URL: {e}")
        else:
            # 次の問題のインデックスを更新（最後の問題でない場合のみ）
            session['current_question'] = current_question + 1
            logger.info(f"Next question index set to: {current_question + 1}")
        
        # 最終レスポンスの内容を確認
        logger.info(f"Sending response: {response_data}")
        return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"Error in submit_answer: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/next_question', methods=['GET'])
def next_question():
    """次の問題を表示する"""
    try:
        questions = session.get('questions', [])
        current_question = session.get('current_question', 0)
        quiz_history = session.get('quiz_history', [])
        
        logger.info(f"Current question index: {current_question}")
        logger.info(f"Total questions: {len(questions)}")
        logger.info(f"Quiz history entries: {len(quiz_history)}")
        
        # 全問題が終了した場合
        if current_question >= len(questions):
            logger.info("Quiz completed, redirecting to result page")
            return redirect(url_for('result'))
        
        # 現在の問題を表示
        logger.info(f"Showing question {current_question + 1}")
        return render_template('quiz.html',
                            question=questions[current_question],
                            question_number=current_question + 1,
                            total_questions=len(questions),
                            correct_answers=session.get('score', 0))
                            
    except Exception as e:
        logger.error(f"Error in next_question route: {e}")
        logger.exception("Full traceback:")
        return redirect(url_for('select_grade'))

=======
>>>>>>> 681de6ad92a5180cf7f6948754ec9bd5293c7a94
@app.route('/dashboard')
def dashboard():
    """
    学習成績ダッシュボードを表示
    """
    # クイズの試行履歴を取得
    quiz_attempts = QuizAttempt.query.order_by(QuizAttempt.id.desc()).all()
    return render_template('dashboard.html', quiz_attempts=quiz_attempts)

@app.route('/grade/<int:grade>/category/<category>/subcategory')
def select_subcategory(grade, category):
    """
    サブカテゴリー選択ページを表示
    """
    if grade < 1 or grade > 6:
        flash('Invalid grade selected')
        return redirect(url_for('grade_select'))
    
    if category not in ['japanese', 'math', 'science', 'society']:
        flash('Invalid category selected')
        return redirect(url_for('select_category', grade=grade))
    
    return render_template('subcategory_select.html', grade=grade, category=category)

@app.route('/grade/<int:grade>/category/<category>/subcategory/<subcategory>/difficulty')
def select_difficulty(grade, category, subcategory):
    """
    難易度選択ページを表示
    """
    if grade < 1 or grade > 6:
        flash('Invalid grade selected')
        return redirect(url_for('grade_select'))
    
    if category not in ['japanese', 'math', 'science', 'society']:
        flash('Invalid category selected')
        return redirect(url_for('select_category', grade=grade))
    
    return render_template('difficulty_select.html', 
                         grade=grade, 
                         category=category, 
                         subcategory=subcategory)

@app.route('/grade/<int:grade>/category/<category>/subcategory/<subcategory>/difficulty/<difficulty>/start')
def start_quiz(grade, category, subcategory, difficulty):
    """
    クイズを開始
    """
    if grade < 1 or grade > 6:
        flash('Invalid grade selected')
        return redirect(url_for('grade_select'))
    
    if category not in ['japanese', 'math', 'science', 'society']:
        flash('Invalid category selected')
        return redirect(url_for('select_category', grade=grade))
    
    if difficulty not in ['easy', 'medium', 'hard']:
        flash('Invalid difficulty selected')
        return redirect(url_for('select_difficulty', grade=grade, category=category, subcategory=subcategory))
    
    # クイズデータを読み込む
    quiz_file = f'quiz_data/grade{grade}/{category}.json'
    try:
        with open(quiz_file, 'r', encoding='utf-8') as f:
            quiz_data = json.load(f)
    except FileNotFoundError:
        flash('Quiz data not found')
        return redirect(url_for('grade_select'))
    
    # 選択された条件に合うクイズをフィルタリング
    filtered_questions = [q for q in quiz_data 
                        if q['subcategory'] == subcategory and 
                           q['difficulty'] == difficulty]
    
    if not filtered_questions:
        flash('No questions available for selected criteria')
        return redirect(url_for('select_difficulty', 
                              grade=grade, 
                              category=category, 
                              subcategory=subcategory))
    
    # クイズをシャッフル
    random.shuffle(filtered_questions)
    
    # セッションにクイズ情報を保存
    session['questions'] = filtered_questions
    session['current_question'] = 0
    session['score'] = 0
    session['grade'] = grade
    session['category'] = category
    session['subcategory'] = subcategory
    session['difficulty'] = difficulty
    
    return redirect(url_for('show_question'))

@app.route('/question')
def show_question():
    """
    問題を表示
    """
    if 'questions' not in session:
        flash('No quiz in progress')
        return redirect(url_for('grade_select'))
    
    current = session.get('current_question', 0)
    questions = session.get('questions', [])
    
    if current >= len(questions):
        # クイズ終了時の処理
        score = session.get('score', 0)
        total_questions = len(questions)
        grade = session.get('grade')
        category = session.get('category')
        subcategory = session.get('subcategory')
        difficulty = session.get('difficulty')
        
        # 結果をデータベースに保存
        quiz_attempt = QuizAttempt(
            score=score,
            total_questions=total_questions,
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty
        )
        db.session.add(quiz_attempt)
        db.session.commit()
        
        # セッションをクリア
        session.pop('questions', None)
        session.pop('current_question', None)
        session.pop('score', None)
        session.pop('grade', None)
        session.pop('category', None)
        session.pop('subcategory', None)
        session.pop('difficulty', None)
        
        return render_template('result.html', 
                             score=score, 
                             total_questions=total_questions)
    
    question_data = questions[current]
    return render_template('quiz.html',
                         current_question=current,
                         total_questions=len(questions),
                         score=session.get('score', 0),
                         question=question_data['question_text'],
                         options=question_data['choices'],
                         question_data=question_data)

<<<<<<< HEAD
@app.route('/question_history/<int:grade>/<category>/<subcategory>/<difficulty>/<path:question_text>')
def question_history(grade, category, subcategory, difficulty, question_text):
    try:
        history = QuizAttempt.get_question_history(grade, category, subcategory, difficulty, question_text)
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error in question_history route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/result')
def result():
    """クイズ結果を表示する"""
    try:
        # セッションから必要な情報を取得
        score = session.get('score', 0)
        total_questions = len(session.get('questions', []))
        quiz_history = session.get('quiz_history', [])
        
        if not quiz_history:
            logger.error("No quiz history found")
            return redirect(url_for('grade_select'))
            
        logger.info(f"Showing result page - Score: {score}/{total_questions}")
        
        return render_template('result.html',
                             correct_answers=score,
                             total_questions=total_questions,
                             quiz_history=quiz_history)
                             
    except Exception as e:
        logger.error(f"Error in result route: {e}")
        return redirect(url_for('select_grade'))

@app.route('/show_question')
def show_question():
    """現在の問題を表示する"""
    try:
        questions = session.get('questions', [])
        current_question = session.get('current_question', 0)
        
        logger.info(f"Showing question {current_question + 1} of {len(questions)}")
        
        if not questions or current_question >= len(questions):
            logger.error("No questions available or current question index out of range")
            return redirect(url_for('grade_select'))
            
        return render_template('quiz.html',
                            question=questions[current_question],
                            question_number=current_question + 1,
                            total_questions=len(questions),
                            correct_answers=session.get('score', 0))
                            
    except Exception as e:
        logger.error(f"Error in show_question: {e}")
        logger.exception("Full traceback:")
        return redirect(url_for('select_grade'))
=======
@app.route('/answer', methods=['POST'])
def submit_answer():
    """
    回答を処理
    """
    if 'questions' not in session:
        flash('No quiz in progress')
        return redirect(url_for('grade_select'))
    
    current = session.get('current_question', 0)
    questions = session.get('questions', [])
    
    if current >= len(questions):
        return redirect(url_for('show_question'))
    
    # 回答を取得
    answer = request.form.get('answer')
    correct_answer = questions[current]['correct_answer']
    
    # 正誤判定
    if answer == correct_answer:
        session['score'] = session.get('score', 0) + 1
        flash('Correct!', 'success')
    else:
        flash(f'Incorrect. The correct answer was: {correct_answer}', 'error')
    
    # 次の問題へ
    session['current_question'] = current + 1
    return redirect(url_for('show_question'))
>>>>>>> 681de6ad92a5180cf7f6948754ec9bd5293c7a94
