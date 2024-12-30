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
if os.environ.get('ENVIRONMENT') == 'production':
    db_uri = os.environ.get('DATABASE_URL')
    if db_uri and db_uri.startswith('postgres://'):
        db_uri = db_uri.replace('postgres://', 'postgresql://', 1)
else:
    db_uri = os.environ.get('LOCAL_DATABASE_URL')

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
        'keepalives_count': 5
    }
}

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
        logger.info(json.dumps({
            'event': 'db_connection_attempt',
            'db_uri': app.config['SQLALCHEMY_DATABASE_URI'].replace(
                app.config['SQLALCHEMY_DATABASE_URI'].split('@')[0],
                '***SECRET***'
            ),
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
            'error': str(e),
            'traceback': traceback.format_exc(),
            'timestamp': time.time()
        }))
        return False

@app.before_request
def before_request():
    start_time = time.time()
    g.request_start_time = start_time
    g.request_id = str(uuid.uuid4())
    
    # システムメトリクスの記録
    memory_info = psutil.Process().memory_info()
    logger.info(json.dumps({
        'event': 'request_start',
        'request_id': g.request_id,
        'path': request.path,
        'method': request.method,
        'memory_rss_mb': memory_info.rss / 1024 / 1024,
        'memory_vms_mb': memory_info.vms / 1024 / 1024,
        'cpu_percent': psutil.cpu_percent(),
        'timestamp': start_time
    }))
    
    # データベース接続の確認
    if not check_db_connection():
        return "Database connection error", 500

@app.after_request
def after_request(response):
    if hasattr(g, 'request_start_time'):
        end_time = time.time()
        duration_ms = (end_time - g.request_start_time) * 1000
        
        memory_info = psutil.Process().memory_info()
        logger.info(json.dumps({
            'event': 'request_end',
            'request_id': getattr(g, 'request_id', 'unknown'),
            'path': request.path,
            'method': request.method,
            'status_code': response.status_code,
            'duration_ms': duration_ms,
            'memory_rss_mb': memory_info.rss / 1024 / 1024,
            'memory_vms_mb': memory_info.vms / 1024 / 1024,
            'cpu_percent': psutil.cpu_percent(),
            'timestamp': end_time
        }))
        
        # 処理時間が長い場合は警告
        if duration_ms > 5000:  # 5秒以上
            logger.warning(json.dumps({
                'event': 'long_request_warning',
                'request_id': getattr(g, 'request_id', 'unknown'),
                'path': request.path,
                'method': request.method,
                'duration_ms': duration_ms,
                'timestamp': end_time
            }))
    
    return response

@app.errorhandler(504)
def gateway_timeout(error):
    logger.error(json.dumps({
        'event': 'gateway_timeout',
        'path': request.path,
        'method': request.method,
        'error': str(error),
        'timestamp': time.time()
    }))
    return "Gateway Timeout - The server took too long to respond", 504

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(json.dumps({
        'event': 'unhandled_exception',
        'error_type': type(e).__name__,
        'error': str(e),
        'path': request.path,
        'method': request.method,
        'traceback': traceback.format_exc(),
        'timestamp': time.time()
    }))
    return "An internal error occurred", 500

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
        
        # DNS解決のテスト
        db_host = app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1].split('/')[0].split(':')[0]
        try:
            ip_address = socket.gethostbyname(db_host)
            logger.info(json.dumps({
                'event': 'dns_resolution',
                'host': db_host,
                'ip': ip_address,
                'duration_ms': (time.time() - start_time) * 1000
            }))
        except socket.gaierror as e:
            logger.error(json.dumps({
                'event': 'dns_resolution_error',
                'host': db_host,
                'error': str(e)
            }))

        # TCP接続テスト
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            start_connect = time.time()
            sock.connect((db_host, 5432))
            logger.info(json.dumps({
                'event': 'tcp_connection',
                'host': db_host,
                'port': 5432,
                'duration_ms': (time.time() - start_connect) * 1000
            }))
            sock.close()
        except Exception as e:
            logger.error(json.dumps({
                'event': 'tcp_connection_error',
                'host': db_host,
                'port': 5432,
                'error': str(e)
            }))

        # データベース接続テスト
        if check_db_connection():
            logger.info("Database connection test completed successfully")
        else:
            logger.error("Database connection test failed")

    except Exception as e:
        logger.error(json.dumps({
            'event': 'database_test_error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }))

with app.app_context():
    test_database_connection()
    create_database_tables()

# クイズデータの取得（キャッシュ付き）
@cache.memoize(timeout=300)
@log_performance
def get_quiz_data(grade, category, subcategory, difficulty):
    try:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        logger.info(json.dumps({
            'event': 'quiz_data_fetch_start',
            'request_id': request_id,
            'grade': grade,
            'category': category,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': start_time
        }))
        
        # クイズデータの取得処理
        data_fetch_start = time.time()
        questions = questions_by_category.get(category, {}).get(str(grade), [])
        data_fetch_end = time.time()
        
        logger.info(json.dumps({
            'event': 'quiz_data_fetch_step',
            'request_id': request_id,
            'step': 'initial_data_fetch',
            'duration_ms': (data_fetch_end - data_fetch_start) * 1000,
            'questions_count': len(questions) if questions else 0,
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': data_fetch_end
        }))
        
        if not questions:
            return None
            
        # 該当する問題をフィルタリング
        filter_start = time.time()
        filtered_questions = [q for q in questions if q.get('subcategory') == subcategory and q.get('difficulty') == difficulty]
        filter_end = time.time()
        
        logger.info(json.dumps({
            'event': 'quiz_data_fetch_step',
            'request_id': request_id,
            'step': 'filter_questions',
            'duration_ms': (filter_end - filter_start) * 1000,
            'filtered_count': len(filtered_questions),
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': filter_end
        }))
        
        if not filtered_questions:
            return None

        # 問題の統計情報を取得
        stats_start = time.time()
        question_stats = QuizAttempt.get_question_stats(grade, category, subcategory, difficulty)
        stats_end = time.time()
        
        logger.info(json.dumps({
            'event': 'quiz_data_fetch_step',
            'request_id': request_id,
            'step': 'get_question_stats',
            'duration_ms': (stats_end - stats_start) * 1000,
            'stats_count': len(question_stats),
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': stats_end
        }))
        
        # 問題を優先順位付けしてソート
        sort_start = time.time()
        prioritized = sorted(filtered_questions, 
            key=lambda q: (
                question_stats.get(q['question'], {'total': 0})['total'] > 0,
                question_stats.get(q['question'], {'percentage': 100})['percentage'],
                question_stats.get(q['question'], {'total': 0})['total']
            )
        )
        selected_questions = prioritized[:10]
        sort_end = time.time()
        
        logger.info(json.dumps({
            'event': 'quiz_data_fetch_step',
            'request_id': request_id,
            'step': 'prioritize_and_select',
            'duration_ms': (sort_end - sort_start) * 1000,
            'selected_count': len(selected_questions),
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': sort_end
        }))
        
        # 選択肢のシャッフル
        shuffle_start = time.time()
        shuffled_questions = []
        for q in selected_questions:
            shuffled = q.copy()
            options = [shuffled['correct_answer']] + shuffled['incorrect_answers']
            random.shuffle(options)
            shuffled['options'] = options
            shuffled['correct_index'] = options.index(shuffled['correct_answer'])
            shuffled_questions.append(shuffled)
        shuffle_end = time.time()
        
        logger.info(json.dumps({
            'event': 'quiz_data_fetch_step',
            'request_id': request_id,
            'step': 'shuffle_options',
            'duration_ms': (shuffle_end - shuffle_start) * 1000,
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': shuffle_end
        }))
        
        end_time = time.time()
        total_duration_ms = (end_time - start_time) * 1000
        
        logger.info(json.dumps({
            'event': 'quiz_data_fetch_complete',
            'request_id': request_id,
            'grade': grade,
            'category': category,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'num_questions': len(shuffled_questions),
            'total_duration_ms': total_duration_ms,
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': end_time
        }))
        
        return shuffled_questions
        
    except Exception as e:
        error_time = time.time()
        logger.error(json.dumps({
            'event': 'quiz_data_fetch_error',
            'request_id': request_id,
            'grade': grade,
            'category': category,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'error': str(e),
            'error_type': type(e).__name__,
            'stack_trace': traceback.format_exc(),
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': error_time
        }))
        return None

@app.route('/')
@cache.cached(timeout=300)
def index():
    return render_template('index.html')

@app.route('/grade/<int:grade>/category/<category>/subcategory/<subcategory>/difficulty/<difficulty>')
@log_performance
def quiz_with_params(grade, category, subcategory, difficulty):
    try:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        print(json.dumps({
            'event': 'quiz_request_start',
            'request_id': request_id,
            'grade': grade,
            'category': category,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': start_time
        }))
        
        # クイズデータの取得（キャッシュ利用）
        quiz_data = get_quiz_data(grade, category, subcategory, difficulty)
        fetch_time = time.time()
        
        if quiz_data is None:
            print(json.dumps({
                'event': 'quiz_not_found',
                'request_id': request_id,
                'grade': grade,
                'category': category,
                'subcategory': subcategory,
                'difficulty': difficulty,
                'timestamp': time.time()
            }))
            return "Quiz not found", 404
        
        # テンプレートのレンダリング
        render_start = time.time()
        response = render_template('quiz.html',
                                 quiz_data=quiz_data,
                                 grade=grade,
                                 category=category,
                                 subcategory=subcategory,
                                 difficulty=difficulty)
        render_end = time.time()
                                 
        end_time = time.time()
        total_duration_ms = (end_time - start_time) * 1000
        
        print(json.dumps({
            'event': 'quiz_complete',
            'request_id': request_id,
            'grade': grade,
            'category': category,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'fetch_duration_ms': (fetch_time - start_time) * 1000,
            'render_duration_ms': (render_end - render_start) * 1000,
            'total_duration_ms': total_duration_ms,
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': end_time
        }))
        
        return response
        
    except Exception as e:
        error_time = time.time()
        print(json.dumps({
            'event': 'quiz_error',
            'request_id': request_id,
            'grade': grade,
            'category': category,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'error': str(e),
            'error_type': type(e).__name__,
            'stack_trace': traceback.format_exc(),
            'duration_ms': (error_time - start_time) * 1000,
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': error_time
        }))
        raise
