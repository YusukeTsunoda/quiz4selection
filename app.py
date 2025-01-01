import os
import sys
import json
import random
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from models import db, QuizAttempt, User
from config import Config, supabase, is_development
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from functools import wraps
import commands  # コマンドをインポート
from extensions import db, migrate
from flask_login import LoginManager, current_user, login_user, logout_user, login_required

# .envファイルを読み込む
load_dotenv()

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# アプリケーションの初期化
app = Flask(__name__)

# 設定の読み込み
try:
    app.config.from_object(Config())
    logger.info("Application configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load application configuration: {e}")
    sys.exit(1)

# データベースの初期化
try:
    db.init_app(app)
    migrate.init_app(app, db)  # マイグレーションの初期化を追加
    with app.app_context():
        # データベース接続のテスト
        try:
            db.engine.connect().close()
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            sys.exit(1)
        
        # データベーステーブルの作成
        db.create_all()
        logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    sys.exit(1)

# テンプレートで使用する関数を登録
@app.context_processor
def utility_processor():
    return {
        'get_subcategories': get_subcategories,
        'CATEGORY_NAMES': CATEGORY_NAMES,
        'SUBCATEGORY_NAMES': SUBCATEGORY_NAMES
    }

# コマンドの登録
commands.init_app(app)

# データベース接続エラーハンドリング
def get_db():
    """データベース接続を取得する関数"""
    try:
        if not hasattr(g, 'db_conn'):
            g.db_conn = db.engine.connect()
        return g.db_conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
    raise
            
@app.teardown_appcontext
def close_db(error):
    """データベース接続を閉じる関数"""
    db_conn = getattr(g, 'db_conn', None)
    if db_conn is not None:
        db_conn.close()

def init_app():
    """アプリケーションの初期化"""
    with app.app_context():
        try:
            # データベースの作成
            db.create_all()
            # 接続テスト
            with get_db() as conn:
                conn.execute('SELECT 1')
            logger.info('Database connection successful')
        except Exception as e:
            logger.error(f'Database initialization error: {e}')
            sys.exit(1)

# 各ルートでのデータベースエラーハンドリング
@app.errorhandler(SQLAlchemyError)
def handle_db_error(error):
    """データベースエラーのハンドリング"""
    logger.error(f"Database error occurred: {error}")
    db.session.rollback()
    return "データベースエラーが発生しました。しばらく待ってから再試行してください。", 500

# カテゴリーと科目名の対応
CATEGORY_NAMES = {
    'japanese': '国語',
    'math': '算数',
    'science': '理科',
    'society': '社会',
    'life': '生活'
}

# サブカテゴリーの日本語名
SUBCATEGORY_NAMES = {
    'japanese': {
        'hiragana': 'ひらがな・カタカナの読み書き',
        'kanji': '漢字の読み書き（配当漢字約200字）',
        'story': '物語文の読解（あらすじ、登場人物）',
        'explanation': '説明文の読解（段落、要点）',
        'speech': 'スピーチの仕方',
        'composition': '作文の書き方',
        'grammar': '主語と述語の関係',
        'reading': '音読と朗読',
        'vocabulary': '熟語の意味と使い方',
        'literature': '文学的な文章',
        'summary': '要約',
        'discussion': '話し合い',
        'language': '日本語の特質',
        'reading_comprehension': '読解力',
        'character_understanding': '文字の理解',
        'paragraph_structure': '段落構成',
        'letter_writing': '手紙の書き方',
        'essay_writing': '作文',
        'idioms': '慣用句・ことわざ',
        'expression': '表現の工夫',
        'comparison': '複数資料の関連付け'
    },
    'math': {
        'numbers': '数と計算（1から100まで）',
        'addition': 'たし算（2桁や3桁）',
        'subtraction': 'ひき算（2桁や3桁）',
        'shapes': '図形（三角形、四角形、直角、対称な形）',
        'measurement': '長さ・かさの単位と測定（cm、m、L、dL、mL）',
        'time': '時刻と時間の計算',
        'counting': 'ものの個数の数え方や分類',
        'multiplication': 'かけ算九九の完成',
        'division': 'わり算の導入と計算',
        'fractions': '分数',
        'decimals': '小数',
        'area': '面積',
        'volume': '体積',
        'statistics': '表とグラフ（棒グラフ）',
        'proportion': '比例',
        'large_numbers': '大きな数',
        'rounding': '概数と四捨五入',
        'angles': '角度',
        'parallel_lines': '垂直と平行',
        'patterns': '変わり方調べ',
        'line_graphs': '折れ線グラフ',
        'circle_area': '円の面積',
        'scale': '縮図と拡大図',
        'ratio': '比とその利用',
        'data': 'データの調べ方',
        'probability': '場合の数と確率',
        'algebra': '文字を使った式'
    },
    'science': {
        'living_things': '昆虫と植物の観察',
        'plants': '植物の育ち方',
        'weather': '天気の様子',
        'materials': '物の重さと体積',
        'magnets': '磁石の性質',
        'electricity': '電気の働き',
        'sound': '音の性質',
        'light': '光の性質',
        'force': '力の働き',
        'earth': '地球と天体',
        'human_body': '人の体',
        'moon_stars': '月と星',
        'properties': '物の性質',
        'metals': '金属の性質',
        'seasonal_changes': '季節と生き物',
        'ecosystem': '生物のつながり',
        'combustion': '燃焼の仕組み',
        'solution': '水溶液の性質',
        'lever': 'てこの規則性',
        'pendulum': '振り子の運動',
        'electromagnet': '電磁石の性質',
        'water_flow': '流れる水の働き'
    },
    'society': {
        'community': '身近な地域の様子',
        'industry': '商店街と大型店',
        'history': '歴史',
        'geography': '地図の読み方の基礎',
        'government': '政治',
        'economy': '経済',
        'culture': '昔の道具と暮らし',
        'international': '国際理解',
        'prefectures': '都道府県',
        'map_symbols': '地図記号',
        'local_geography': '地域の地理',
        'water_resources': '水源と水道',
        'environment': '環境保護',
        'disaster_prevention': '災害対策',
        'traditional_culture': '伝統文化',
        'regional_industry': '地域の産業',
        'constitution': '日本国憲法',
        'local': '地方自治',
        'un': '国際連合'
    },
    'life': {
        'school': '学校生活（施設・規則・友達）',
        'family': '家族や地域との関わり',
        'seasons': '季節と生活の関わり',
        'nature': '動植物の飼育・栽培',
        'safety': '安全な生活（交通・生活習慣）',
        'growth': '自分の成長（できるようになったこと）',
        'community': '町探検（地域の様子や働く人々）'
    }
}

# 学年ごとのカテゴリーとサブカテゴリー
GRADE_CATEGORIES = {
    1: {
        'japanese': [
            'hiragana',
            'kanji',
            'story',
            'explanation',
            'speech',
            'composition'
        ],
        'math': [
            'numbers',
            'addition',
            'subtraction',
            'shapes',
            'measurement',
            'time',
            'counting'
        ],
        'life': [
            'school',
            'family',
            'seasons',
            'nature',
            'safety',
            'growth'
        ]
    },
    2: {
        'japanese': [
            'story',
            'explanation',
            'kanji',
            'composition',
            'speech'
        ],
        'math': [
            'addition',
            'subtraction',
            'multiplication',
            'measurement',
            'time',
            'shapes'
        ],
        'life': [
            'seasons',
            'community',
            'nature',
            'growth'
        ]
    },
    3: {
        'japanese': [
            'kanji',
            'story',
            'explanation',
            'speech',
            'reading',
            'composition',
            'vocabulary',
            'grammar'
        ],
        'math': [
            'multiplication',
            'division',
            'time',
            'measurement',
            'shapes',
            'statistics'
        ],
        'science': [
            'living_things',
            'plants',
            'light',
            'sound',
            'magnets',
            'force',
            'materials'
        ],
        'society': [
            'community',
            'geography',
            'industry',
            'culture'
        ]
    },
    4: {
        'japanese': [
            'kanji',
            'reading_comprehension',
            'character_understanding',
            'paragraph_structure',
            'idioms',
            'letter_writing',
            'essay_writing'
        ],
        'math': [
            'large_numbers',
            'rounding',
            'decimals',
            'fractions',
            'angles',
            'area',
            'parallel_lines',
            'patterns',
            'line_graphs'
        ],
        'science': [
            'weather',
            'moon_stars',
            'electricity',
            'properties',
            'metals',
            'living_things',
            'seasonal_changes'
        ],
        'society': [
            'prefectures',
            'map_symbols',
            'local_geography',
            'water_resources',
            'environment',
            'disaster_prevention',
            'traditional_culture',
            'regional_industry'
        ]
    },
    5: {
        'japanese': [
            'kanji',
            'reading',
            'grammar',
            'writing',
            'vocabulary',
            'composition',
            'discussion',
            'comparison',
            'explanation',
            'summary',
            'literature',
            'language',
            'idioms',
            'hyakuninishu'
        ],
        'math': [
            'integers',
            'decimals',
            'fractions',
            'area',
            'volume',
            'congruence',
            'percentage',
            'proportion',
            'geometry',
            'graph',
            'measurement',
            'calculation',
            'figure'
        ],
        'science': [
            'pendulum',
            'electromagnet',
            'weather',
            'water',
            'animals',
            'fish',
            'flowers',
            'plants',
            'earth_science',
            'biology',
            'chemistry',
            'physics'
        ],
        'society': [
            'agriculture',
            'manufacturing',
            'disaster',
            'environment',
            'transportation',
            'climate',
            'industry',
            'information',
            'current_events',
            'prefectures',
            'civics',
            'history',
            'geography'
        ]
    },
    6: {
        'japanese': [
            'kanji',
            'reading',
            'grammar',
            'writing',
            'composition',
            'discussion',
            'expression',
            'language',
            'comparison',
            'explanation',
            'literature',
            'hyakuninishu'
        ],
        'math': [
            'fractions',
            'volume',
            'circle_area',
            'scale',
            'ratio',
            'proportion',
            'algebra',
            'data',
            'probability',
            'graph',
            'measurement',
            'calculation',
            'figure'
        ],
        'science': [
            'earth',
            'electricity',
            'lever',
            'moon',
            'combustion',
            'ecosystem',
            'human_body',
            'solution',
            'plants',
            'earth_science',
            'biology',
            'chemistry',
            'physics'
        ],
        'society': [
            'constitution',
            'local',
            'un',
            'government',
            'modern',
            'taisho',
            'meiji',
            'edo',
            'kamakura',
            'muromachi',
            'azuchi',
            'asuka',
            'heian',
            'jomon',
            'prefectures',
            'civics',
            'current_events',
            'geography',
            'history'
        ]
    }
}

def get_subcategories(grade, category):
    """指定された学年とカテゴリのサブカテゴリを取得"""
    return GRADE_CATEGORIES.get(grade, {}).get(category, [])

def get_shuffled_question(question):
    """問題の選択肢をシャッフルする"""
    shuffled = question.copy()
    options = shuffled['options'].copy()
    correct = shuffled['correct']
    
    # 選択肢をシャッフル
    indices = list(range(len(options)))
    random.shuffle(indices)
    
    # 選択肢を並び替え
    shuffled['options'] = [options[i] for i in indices]
    # 正解のインデックスも更新
    shuffled['correct'] = indices.index(correct)
    
    return shuffled

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('ログインが必要です。', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('ログインが必要です。', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(session['user']['id'])
        if not user or not user.is_admin:
            flash('管理者権限が必要です。', 'error')
            return redirect(url_for('grade_select'))
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """ルートページのハンドラ"""
    return redirect(url_for('grade_select'))

@app.route('/grade_select')
@login_required
def grade_select():
    """学年選択ページを表示"""
    return render_template('grade_select.html')

@app.route('/grade/<int:grade>/category')
def select_category(grade):
    """カテゴリー選択ページを表示"""
    if grade < 1 or grade > 6:
        flash('無効な学年が選択されました')
        return redirect(url_for('grade_select'))
    
    return render_template('category_select.html', grade=grade)

@app.route('/grade/<int:grade>/category/<category>/subcategory')
def select_subcategory(grade, category):
    """サブカテゴリー選択ページを表示"""
    subcategories = get_subcategories(grade, category)
    return render_template('subcategory_select.html',
                           grade=grade,
                           category=category,
                           category_name=CATEGORY_NAMES[category],
                           subcategories=subcategories,
                           subcategory_names=SUBCATEGORY_NAMES[category])

@app.route('/grade/<int:grade>/category/<category>/subcategory/<subcategory>/difficulty')
def select_difficulty(grade, category, subcategory):
    """難易度選択画面を表示する"""
    try:
        if not current_user.is_authenticated:
            flash('ログインが必要です。', 'error')
            return redirect(url_for('login'))

        # 各難易度のクイズ統計を取得
        stats = {}
        for difficulty in ['easy', 'medium', 'hard']:
            # 問題データの存在確認と形式チェック
            file_path = f'quiz_data/grade_{grade}/{category}/{subcategory}/{difficulty}/questions.json'
            has_questions = False
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        questions = json.load(f)
                        if questions and isinstance(questions, list) and len(questions) > 0:
                            # 各問題の形式を確認
                            valid_format = all(
                                isinstance(q, dict) and 
                                'question' in q and 
                                'options' in q and 
                                ('correct' in q or 'correct_answer' in q) and 
                                isinstance(q['options'], list) 
                                for q in questions
                            )
                            has_questions = valid_format
                except Exception as e:
                    logger.error(f"Error reading questions from {file_path}: {e}")
                    has_questions = False

            # 統計情報の初期化
            stats[difficulty] = {
                'has_questions': has_questions,
                'attempts': 0,
                'avg_score': 0,
                'highest_score': 0
            }

            if has_questions:
                # クイズ履歴から統計を計算
                attempts = QuizAttempt.query.filter_by(
                    user_id=current_user.id,
                    grade=grade,
                    category=category,
                    subcategory=subcategory,
                    difficulty=difficulty
                ).all()

                if attempts:
                    stats[difficulty]['attempts'] = len(attempts)
                    total_score_percentage = sum((attempt.score / attempt.total_questions) * 100 for attempt in attempts)
                    stats[difficulty]['avg_score'] = total_score_percentage / len(attempts)
                    stats[difficulty]['highest_score'] = max((attempt.score / attempt.total_questions) * 100 for attempt in attempts)

        return render_template('difficulty_select.html',
                           grade=grade,
                           category=category,
                           subcategory=subcategory,
                           category_name=CATEGORY_NAMES[category],
                           subcategory_name=SUBCATEGORY_NAMES[category][subcategory],
                           stats=stats)

    except Exception as e:
        logger.error(f"Error in select_difficulty: {e}")
        flash('難易度選択画面の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('grade_select'))


@app.route('/start_quiz/<int:grade>/<category>/<subcategory>/<difficulty>')
@login_required
def start_quiz(grade, category, subcategory, difficulty):
    """クイズを開始する"""
    try:
        # ログイン情報を一時保存
        user_info = session.get('user')
        
        # クイズ関連のセッション情報のみをクリア
        quiz_keys = ['questions', 'current_question', 'score', 'quiz_history', 
                    'answered_questions', 'grade', 'category', 'subcategory', 'difficulty']
        for key in quiz_keys:
            if key in session:
                session.pop(key)
        
        # ログイン情報を復元
        session['user'] = user_info

        # 問題を取得
        questions = get_questions(grade, category, subcategory, difficulty)

        if not questions:
            flash('問題の取得に失敗しました。', 'error')
            return redirect(url_for('select_difficulty', grade=grade,
                            category=category, subcategory=subcategory))

        # セッションに情報を保存
        session['questions'] = questions
        session['current_question'] = 0
        session['score'] = 0
        session['quiz_history'] = []
        session['answered_questions'] = []
        session['grade'] = grade
        session['category'] = category
        session['subcategory'] = subcategory
        session['difficulty'] = difficulty

        # 最初の問題を表示
        first_question = questions[0]
        return render_template('quiz.html',
                            question=first_question['question'],
                            options=first_question['options'],
                            question_data=first_question,
                            current_question=0,
                            total_questions=len(questions),
                            score=0)

    except Exception as e:
        logger.error(f"Error in start_quiz: {e}")
        flash('クイズの開始中にエラーが発生しました。', 'error')
        return redirect(url_for('select_difficulty', grade=grade,
                        category=category, subcategory=subcategory))


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'User not logged in'})

        data = request.get_json()
        selected_index = data.get('answer')
        logger.info(f"Received answer data: {data}")
        
        current_question = session.get('current_question', 0)
        questions = session.get('questions', [])
        quiz_history = session.get('quiz_history', [])
        current_score = session.get('score', 0)

        if not questions or current_question >= len(questions):
            logger.error("Invalid question state")
            return jsonify({'success': False, 'error': 'Invalid question'})

        current_q = questions[current_question]
        correct_index = current_q.get('correct')
        logger.info(f"Question data: {current_q}")
        logger.info(f"Selected index: {selected_index}, Correct index: {correct_index}")
        
        # 型を合わせて比較
        is_correct = int(selected_index) == int(correct_index)
        logger.info(f"Is correct: {is_correct}")
        
        if is_correct:
            current_score += 1
            session['score'] = current_score

        # 回答履歴を保存
        quiz_history.append({
            'question': current_q.get('question', ''),
            'user_answer': current_q['options'][int(selected_index)],
            'correct_answer': current_q['options'][int(correct_index)],
            'is_correct': is_correct,
            'options': current_q.get('options', []),
            'explanation': current_q.get('explanation', '')  # 解説を追加
        })
        session['quiz_history'] = quiz_history

        is_last_question = current_question == len(questions) - 1
        logger.info(f"Is last question: {is_last_question}")

        # 最後の問題の場合、QuizAttemptを保存
        if is_last_question:
            try:
                quiz_attempt = QuizAttempt(
                    user_id=current_user.id,
                    grade=session.get('grade'),
                    category=session.get('category'),
                    subcategory=session.get('subcategory'),
                    difficulty=session.get('difficulty'),
                    score=current_score,
                    total_questions=len(questions),
                    _quiz_history=json.dumps(quiz_history)
                )
                db.session.add(quiz_attempt)
                db.session.commit()
                logger.info(f"Quiz attempt saved - User: {current_user.id}, Final score: {current_score}/{len(questions)}")
            except Exception as e:
                logger.error(f"Error saving quiz attempt: {e}")
                return jsonify({'success': False, 'error': 'Failed to save quiz attempt'})

        response_data = {
            'success': True,
            'isCorrect': is_correct,
            'currentScore': current_score,
            'isLastQuestion': is_last_question,
            'redirectUrl': url_for('result') if is_last_question else None
        }
        logger.info(f"Sending response: {response_data}")

        if not is_last_question:
            session['current_question'] = current_question + 1
                
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in submit_answer: {e}")
        logger.exception("Full traceback:")
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
        question_data = questions[current_question]

        return render_template('quiz.html',
                               question=question_data['question'],
                               options=question_data['options'],
                               question_data=question_data,
                               current_question=current_question,
                               total_questions=len(questions),
                               score=session.get('score', 0))

    except Exception as e:
        logger.error(f"Error in next_question route: {e}")
        logger.exception("Full traceback:")
        return redirect(url_for('grade_select'))
    

@app.route('/dashboard')
@login_required
def dashboard():
    """学習成績ダッシュボードを表示"""
    try:
        if not current_user.is_authenticated:
            flash('ログインが必要です。', 'error')
            return redirect(url_for('login'))

        # セッションからユーザーIDを取得
        user_id = session.get('user', {}).get('id')
        if not user_id:
            flash('セッションが無効です。再度ログインしてください。', 'error')
            return redirect(url_for('login'))
            
        # クイズの試行履歴を取得
        quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).order_by(QuizAttempt.timestamp.desc()).all()
        
        # 進捗データの初期化
        progress = {grade: {} for grade in range(1, 7)}

        # 各学年、カテゴリー、サブカテゴリーごとの進捗を集計
        for grade in range(1, 7):
            # 学年ごとの利用可能なカテゴリーを取得
            available_categories = GRADE_CATEGORIES.get(grade, {}).keys()
            
            for category in available_categories:
                if category in CATEGORY_NAMES:
                    progress[grade][category] = {
                        'name': CATEGORY_NAMES[category],
                        'subcategories': {}
                    }

                    # 利用可能なサブカテゴリーを取得
                    for subcategory in get_subcategories(grade, category):
                        # クイズデータが存在するか確認
                        has_quiz_data = False
                        for difficulty in ['easy', 'medium', 'hard']:
                            file_path = f'quiz_data/grade_{grade}/{category}/{subcategory}/{difficulty}/questions.json'
                            if os.path.exists(file_path):
                                has_quiz_data = True
                                break
                        
                        if has_quiz_data:
                            # サブカテゴリー名の取得を安全に行う
                            subcategory_name = SUBCATEGORY_NAMES.get(category, {}).get(subcategory, subcategory)
                            progress[grade][category]['subcategories'][subcategory] = {
                                'name': subcategory_name,
                                'levels': {
                                    'easy': {'attempts': 0, 'avg_score': 0, 'highest_score': 0},
                                    'medium': {'attempts': 0, 'avg_score': 0, 'highest_score': 0},
                                    'hard': {'attempts': 0, 'avg_score': 0, 'highest_score': 0}
                                }
                            }

        # 試行履歴から統計を計算
        for attempt in quiz_attempts:
            grade = attempt.grade
            category = attempt.category
            subcategory = attempt.subcategory
            difficulty = attempt.difficulty
            
            # カテゴリーとサブカテゴリーが存在する場合のみ統計を更新
            if (category in progress.get(grade, {}) and 
                subcategory in progress[grade][category].get('subcategories', {})):
                
                score_percentage = (attempt.score / attempt.total_questions) * 100
                stats = progress[grade][category]['subcategories'][subcategory]['levels'][difficulty]
                stats['attempts'] += 1

                # 平均スコアの更新
                current_total = stats['avg_score'] * (stats['attempts'] - 1)
                stats['avg_score'] = (current_total + score_percentage) / stats['attempts']

                # 最高スコアの更新
                stats['highest_score'] = max(stats['highest_score'], score_percentage)

        # 難易度の日本語名
        difficulty_names = {
            'easy': '初級',
            'medium': '中級',
            'hard': '上級'
        }

        return render_template('dashboard.html',
                           progress=progress,
                           difficulty_names=difficulty_names,
                           quiz_attempts=quiz_attempts)

    except Exception as e:
        logger.error(f"Error in dashboard route: {e}")
        flash('ダッシュボードの表示中にエラーが発生しました。', 'error')
        return redirect(url_for('login'))
    

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
            flash('クイズ履歴が見つかりません。', 'error')
            return redirect(url_for('grade_select'))
    
        logger.info(f"Showing result page - Score: {score}/{total_questions}")

        return render_template('result.html',
                           score=score,
                           total_questions=total_questions,
                           quiz_history=quiz_history)

    except Exception as e:
        logger.error(f"Error in result route: {e}")
        flash('結果の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('grade_select'))
    

def get_questions(grade, category, subcategory, difficulty):
    """指定された条件に基づいて問題を取得する"""
    try:
        logger.info(
            f"Getting questions for grade={grade}, category={category}, subcategory={subcategory}, difficulty={difficulty}")

        # 問題データを取得
        questions, error = get_quiz_data(
            grade, category, subcategory, difficulty)
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
            logger.info(
                f"Selected 10 random questions from {
                    len(questions)} available questions")
        else:
            selected_questions = questions
            logger.info(f"Using all {len(questions)} available questions")

        return selected_questions
    except Exception as e:
        logger.error(f"Error in get_questions: {e}")
        logger.exception("Full traceback:")
        return []


def get_quiz_data(grade, category, subcategory, difficulty):
    """クイズデータを取得する関数"""
    try:
        # 新しいフォルダ構造に基づいたファイルパス
        file_path = f'quiz_data/grade_{grade}/{category}/{subcategory}/{difficulty}/questions.json'
        logger.info(f"Loading quiz data from: {file_path}")

        # ファイルの存在確認
        if not os.path.exists(file_path):
            logger.error(f"Quiz data file not found: {file_path}")
            return None, "問題データファイルが見つかりません"

        # ファイルの読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Successfully loaded JSON data")

            if not data or not isinstance(data, list):
                logger.error("Invalid question data format")
                return None, "問題データの形式が正しくありません"

            # 問題をシャッフル
            shuffled_questions = [get_shuffled_question(q) for q in data]
            logger.info(f"Successfully loaded and shuffled {len(shuffled_questions)} questions")

            return shuffled_questions, None

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return None, "問題データの形式が正しくありません"
    except Exception as e:
        logger.error(f"Error in get_quiz_data: {e}")
        logger.exception("Full traceback:")
        return None, "問題データの読み込み中にエラーが発生しました"


@app.route('/quiz_history/<int:grade>/<category>/<subcategory>/<difficulty>')
@login_required
def quiz_history(grade, category, subcategory, difficulty):
    """特定の条件でのクイズ履歴を表示"""
    try:
        # クイズ履歴を取得
        attempts = QuizAttempt.query.filter_by(
            user_id=current_user.id,
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty
        ).order_by(QuizAttempt.timestamp.desc()).all()

        logger.info(f"Found {len(attempts)} attempts for user {current_user.id}")
        
        history_data = []
        for attempt in attempts:
            logger.info(f"Processing attempt {attempt.id}")
            try:
                if attempt._quiz_history:
                    # 文字列の場合はJSONとしてパース
                    if isinstance(attempt._quiz_history, str):
                        quiz_history = json.loads(attempt._quiz_history)
                    else:
                        quiz_history = attempt._quiz_history
                    
                    logger.info(f"Quiz history for attempt {attempt.id}: {quiz_history}")
                    
                    history_data.append({
                        'timestamp': attempt.timestamp,
                        'score': attempt.score,
                        'total_questions': attempt.total_questions,
                        'questions': quiz_history
                    })
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding quiz history for attempt {attempt.id}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing attempt {attempt.id}: {e}")
                continue

        logger.info(f"Processed {len(history_data)} history entries")

        # 問題データを取得して問題別統計を計算
        questions_data, error = get_quiz_data(grade, category, subcategory, difficulty)
        question_stats = {}
        
        if questions_data:
            # 問題ごとの統計を初期化
            for question in questions_data:
                question_text = question.get('question', '')
                question_stats[question_text] = {
                    'total_attempts': 0,
                    'correct_attempts': 0,
                    'percentage': 0
                }
        
            # 履歴から統計を計算
            for entry in history_data:
                for question in entry['questions']:
                    question_text = question.get('question', '')
                    if question_text in question_stats:
                        question_stats[question_text]['total_attempts'] += 1
                        if question.get('is_correct', False):
                            question_stats[question_text]['correct_attempts'] += 1
        
            # 正答率を計算
            for stats in question_stats.values():
                if stats['total_attempts'] > 0:
                    stats['percentage'] = (stats['correct_attempts'] / stats['total_attempts']) * 100

        return render_template(
            'quiz_history.html',
            history_data=history_data,
            question_stats=question_stats,
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty,
            category_name=CATEGORY_NAMES.get(category, category),
            subcategory_name=SUBCATEGORY_NAMES.get(category, {}).get(subcategory, subcategory)
        )

    except Exception as e:
        logger.error(f"Error in quiz_history route: {e}")
        flash('クイズ履歴の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('dashboard'))


@app.route('/signup', methods=['GET', 'POST'], endpoint='signup')
def signup():
    # セッションをクリア
    session.clear()
    
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            username = request.form['username']
            
            # メールアドレスの重複チェック
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('このメールアドレスは既に登録されています。', 'error')
                return render_template('signup.html')
            
            # ユーザー名の重複チェック
            existing_username = User.query.filter_by(username=username).first()
            if existing_username:
                flash('このユーザー名は既に使用されています。', 'error')
                return render_template('signup.html')
            
            if is_development():
                # 開発環境では認証をスキップ
                user_id = f'dev-{username}'
            else:
                # Supabaseでユーザー登録
                try:
                    response = supabase.auth.sign_up({
                        "email": email,
                        "password": password
                    })
                    user_id = response.user.id
                except Exception as auth_error:
                    logger.error(f"Supabase signup error: {auth_error}")
                    flash('アカウント登録に失敗しました。', 'error')
                    return render_template('signup.html')
            
            # ユーザーをデータベースに保存
            user = User(
                id=user_id,
                email=email,
                username=username,
                is_admin=False
            )
            db.session.add(user)
            db.session.commit()
            
            flash('アカウントが登録されました。ログインしてください。', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Error in signup: {e}")
            db.session.rollback()
            flash('登録に失敗しました。', 'error')
            return render_template('signup.html')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            
            if is_development():
                # 開発環境では認証をスキップ
                user = User.query.filter_by(email=email).first()
                if not user:
                    # 開発環境用のテストユーザーを作成
                    user = User(
                        id='dev-user-id',
                        email=email,
                        username=email.split('@')[0],
                        is_admin=False
                    )
                    db.session.add(user)
                    db.session.commit()
            else:
                # 本番環境での認証処理
                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    user = User.query.filter_by(email=email).first()
                    if not user:
                        flash('ユーザーが見つかりません。先にアカウント登録を行ってください。', 'error')
                        return redirect(url_for('signup'))
                except Exception as auth_error:
                    logger.error(f"Authentication error: {auth_error}")
                    flash('メールアドレスまたはパスワードが正しくありません。', 'error')
                    return render_template('login.html')
            
            # Flask-Loginでユーザーをログイン
            login_user(user)
            
            # セッションにユーザー情報を保存
            session['user'] = {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'is_admin': user.is_admin
            }
            
            flash('ログインしました。', 'success')
            return redirect(url_for('admin_dashboard' if user.is_admin else 'grade_select'))
            
        except Exception as e:
            logger.error(f"Error in login: {e}")
            flash('ログインに失敗しました。', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    try:
        # Supabaseからログアウト
        supabase.auth.sign_out()
        session.clear()
        flash('ログアウトしました。', 'success')
    except Exception as e:
        logger.error(f"Error in logout: {e}")
        flash('ログアウトに失敗しました。', 'error')
        
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    """管理者ダッシュボード"""
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin/dashboard.html', users=users)

@app.route('/admin/user/<user_id>', methods=['GET', 'POST'])
@admin_required
def admin_user_edit(user_id):
    """ユーザーの権限編集"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # 許可する学年を更新
            allowed_grades = [int(grade) for grade in request.form.getlist('grades[]')]
            user.allowed_grades = allowed_grades
            
            # 許可する科目とサブカテゴリを更新
            allowed_subjects = {}
            for grade in range(1, 7):
                for category in CATEGORY_NAMES.keys():
                    subcategories = request.form.getlist(f'subjects[{grade}][{category}][]')
                    if subcategories:
                        if category not in allowed_subjects:
                            allowed_subjects[category] = []
                        allowed_subjects[category].extend(subcategories)
            
            # 重複を除去
            for category in allowed_subjects:
                allowed_subjects[category] = list(set(allowed_subjects[category]))
            
            user.allowed_subjects = allowed_subjects
            db.session.commit()
            
            flash('ユーザー権限を更新しました。', 'success')
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            logger.error(f"Error updating user permissions: {e}")
            db.session.rollback()
            flash('ユーザー権限の更新に失敗しました。', 'error')
    
    return render_template('admin/user_edit.html',
                         user=user,
                         CATEGORY_NAMES=CATEGORY_NAMES,
                         SUBCATEGORY_NAMES=SUBCATEGORY_NAMES)

@app.route('/admin/setup', methods=['POST'])
def admin_setup():
    """本番環境での初期管理者セットアップ用エンドポイント"""
    try:
        # 環境変数から設定用のシークレットキーを取得
        setup_secret = os.environ.get('ADMIN_SETUP_SECRET')
        if not setup_secret:
            return jsonify({'error': 'ADMIN_SETUP_SECRET is not configured'}), 500

        # リクエストからシークレットキーとメールアドレスを取得
        data = request.get_json()
        if not data or data.get('secret') != setup_secret:
            return jsonify({'error': 'Invalid secret key'}), 403

        email = data.get('email')
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # ユーザーを検索
        user = User.get_by_email(email)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # 管理者に設定
        if user.promote_to_admin():
            return jsonify({'message': f'Successfully set {email} as admin'})
        else:
            return jsonify({'message': f'User {email} is already an admin'})

    except Exception as e:
        logger.error(f"Error in admin setup: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            
            # メールアドレスの存在確認
            user = User.get_by_email(email)
            if not user:
                flash('指定されたメールアドレスは登録されていません。', 'error')
                return redirect(url_for('reset_password'))
            
            # Supabaseでパスワードリセットメールを送信
            supabase.auth.reset_password_email(email)
            
            flash('パスワードリセットの手順をメールで送信しました。', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            logger.error(f"Error in reset_password: {e}")
            flash('パスワードリセットメールの送信に失敗しました。', 'error')
            
    return render_template('reset_password.html')

@app.route('/user/profile')
@login_required
def user_profile():
    """ユーザープロフィールページを表示"""
    user = User.query.get(session['user']['id'])
    return render_template('user_profile.html',
                         user=user,
                         CATEGORY_NAMES=CATEGORY_NAMES,
                         SUBCATEGORY_NAMES=SUBCATEGORY_NAMES)

@app.route('/admin/user/<user_id>/detail')
@admin_required
def admin_user_detail(user_id):
    """ユーザー詳細ページを表示（管理者用）"""
    user = User.query.get_or_404(user_id)
    quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).order_by(QuizAttempt.timestamp.desc()).limit(10).all()
    return render_template('admin/user_detail.html',
                         user=user,
                         quiz_attempts=quiz_attempts,
                         CATEGORY_NAMES=CATEGORY_NAMES,
                         SUBCATEGORY_NAMES=SUBCATEGORY_NAMES)

# LoginManagerの初期化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
