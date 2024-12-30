import os
import random
import logging
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
from utils.logging_utils import request_logger, db_logger, api_logger, system_logger, log_system_metrics, network_logger
import uuid
from quiz_data import questions_by_category
import psutil
import traceback

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize cache with larger timeout
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

# リクエスト前のデータベース接続確認（キャッシュ付き）
@cache.memoize(timeout=60)
def check_db_connection():
    try:
        with db.session.begin():
            db.session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return False

@app.before_request
def before_request():
    start_time = time.time()
    g.request_start_time = start_time
    
    # データベース接続の確認（キャッシュ利用）
    if not check_db_connection():
        return "Database connection error", 500

    # リクエストの開始をログ
    request_logger.info(json.dumps({
        'event': 'request_start',
        'path': request.path,
        'method': request.method,
        'timestamp': start_time
    }))

# リクエスト後の処理
@app.after_request
def after_request(response):
    if hasattr(g, 'request_start_time'):
        total_time = time.time() - g.request_start_time
        
        # レスポンスのログ
        request_logger.info(json.dumps({
            'event': 'request_end',
            'path': request.path,
            'method': request.method,
            'status_code': response.status_code,
            'duration_ms': total_time * 1000,
            'timestamp': time.time()
        }))
        
        # 処理時間が長い場合は警告
        if total_time > 5:
            request_logger.warning(json.dumps({
                'event': 'long_request_warning',
                'path': request.path,
                'method': request.method,
                'duration_ms': total_time * 1000,
                'timestamp': time.time()
            }))
    
    return response

# エラーハンドラー
@app.errorhandler(504)
def gateway_timeout(error):
    error_time = time.time()
    request_logger.error(json.dumps({
        'event': 'gateway_timeout',
        'path': request.path,
        'method': request.method,
        'error': str(error),
        'timestamp': error_time
    }))
    return "Request timeout. Please try again.", 504

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

with app.app_context():
    create_database_tables()

# クイズデータの取得（キャッシュ付き）
@cache.memoize(timeout=300)
def get_quiz_data(grade, category, subcategory, difficulty):
    try:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # データ取得開始のログ
        db_logger.info(json.dumps({
            'event': 'quiz_data_fetch_start',
            'request_id': request_id,
            'grade': grade,
            'category': category,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'timestamp': start_time
        }))
        
        # クイズデータの取得処理
        data_fetch_start = time.time()
        questions = questions_by_category.get(category, {}).get(str(grade), [])
        data_fetch_end = time.time()
        
        db_logger.info(json.dumps({
            'event': 'quiz_data_fetch_step',
            'request_id': request_id,
            'step': 'initial_data_fetch',
            'duration_ms': (data_fetch_end - data_fetch_start) * 1000,
            'questions_count': len(questions) if questions else 0,
            'timestamp': data_fetch_end
        }))
        
        if not questions:
            return None
            
        # 該当する問題をフィルタリング
        filter_start = time.time()
        filtered_questions = [q for q in questions if q.get('subcategory') == subcategory and q.get('difficulty') == difficulty]
        filter_end = time.time()
        
        db_logger.info(json.dumps({
            'event': 'quiz_data_fetch_step',
            'request_id': request_id,
            'step': 'filter_questions',
            'duration_ms': (filter_end - filter_start) * 1000,
            'filtered_count': len(filtered_questions),
            'timestamp': filter_end
        }))
        
        if not filtered_questions:
            return None

        # 問題の統計情報を取得して優先順位付け
        stats_start = time.time()
        question_stats = QuizAttempt.get_question_stats(grade, category, subcategory, difficulty)
        stats_end = time.time()
        
        db_logger.info(json.dumps({
            'event': 'quiz_data_fetch_step',
            'request_id': request_id,
            'step': 'get_question_stats',
            'duration_ms': (stats_end - stats_start) * 1000,
            'stats_count': len(question_stats),
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
        
        db_logger.info(json.dumps({
            'event': 'quiz_data_fetch_step',
            'request_id': request_id,
            'step': 'prioritize_and_select',
            'duration_ms': (sort_end - sort_start) * 1000,
            'selected_count': len(selected_questions),
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
        
        db_logger.info(json.dumps({
            'event': 'quiz_data_fetch_step',
            'request_id': request_id,
            'step': 'shuffle_options',
            'duration_ms': (shuffle_end - shuffle_start) * 1000,
            'timestamp': shuffle_end
        }))
        
        end_time = time.time()
        total_duration_ms = (end_time - start_time) * 1000
        
        # データ取得完了のログ
        db_logger.info(json.dumps({
            'event': 'quiz_data_fetch_complete',
            'request_id': request_id,
            'grade': grade,
            'category': category,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'num_questions': len(shuffled_questions),
            'total_duration_ms': total_duration_ms,
            'timestamp': end_time,
            'memory_usage': psutil.Process().memory_info().rss / 1024 / 1024  # MB単位
        }))
        
        return shuffled_questions
        
    except Exception as e:
        error_time = time.time()
        db_logger.error(json.dumps({
            'event': 'quiz_data_fetch_error',
            'request_id': request_id,
            'grade': grade,
            'category': category,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'error': str(e),
            'error_type': type(e).__name__,
            'stack_trace': traceback.format_exc(),
            'timestamp': error_time
        }))
        return None

@app.route('/')
@cache.cached(timeout=300)
def index():
    return render_template('index.html')

@app.route('/grade/<int:grade>/category/<category>/subcategory/<subcategory>/difficulty/<difficulty>')
def quiz_with_params(grade, category, subcategory, difficulty):
    try:
        start_time = time.time()
        
        # システムメトリクスの記録
        log_system_metrics()
        
        # クイズデータの取得（キャッシュ利用）
        quiz_data = get_quiz_data(grade, category, subcategory, difficulty)
        fetch_time = time.time()
        
        if quiz_data is None:
            request_logger.error(json.dumps({
                'event': 'quiz_not_found',
                'grade': grade,
                'category': category,
                'subcategory': subcategory,
                'difficulty': difficulty,
                'timestamp': time.time()
            }))
            return "Quiz not found", 404
        
        # テンプレートのレンダリング
        response = render_template('quiz.html',
                                 quiz_data=quiz_data,
                                 grade=grade,
                                 category=category,
                                 subcategory=subcategory,
                                 difficulty=difficulty)
                                 
        end_time = time.time()
        total_duration_ms = (end_time - start_time) * 1000
        
        # 完了ログ
        request_logger.info(json.dumps({
            'event': 'quiz_complete',
            'grade': grade,
            'category': category,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'fetch_duration_ms': (fetch_time - start_time) * 1000,
            'total_duration_ms': total_duration_ms,
            'timestamp': end_time
        }))
        
        return response
        
    except Exception as e:
        error_time = time.time()
        request_logger.error(json.dumps({
            'event': 'quiz_error',
            'grade': grade,
            'category': category,
            'subcategory': subcategory,
            'difficulty': difficulty,
            'error': str(e),
            'error_type': type(e).__name__,
            'duration_ms': (error_time - start_time) * 1000,
            'timestamp': error_time
        }))
        raise
