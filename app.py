import os
import sys
import json
import random
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from models import db, QuizAttempt
from config import Config
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

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

# カテゴリーと科目の定義
CATEGORY_NAMES = {
    'japanese': '国語',
    'math': '算数',
    'science': '理科',
    'society': '社会'
}

SUBCATEGORY_NAMES = {
    'kanji': '漢字',
    'reading': '読解',
    'grammar': '文法',
    'writing': '作文',
    'calculation': '計算',
    'figure': '図形',
    'measurement': '測定',
    'graph': 'グラフ',
    'physics': '物理',
    'chemistry': '化学',
    'biology': '生物',
    'earth_science': '地学',
    'history': '歴史',
    'geography': '地理',
    'civics': '公民',
    'current_events': '時事',
    'prefectures': '都道府県'
}

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

@app.route('/')
def index():
    """ルートページのハンドラ"""
    return redirect(url_for('grade_select'))

@app.route('/grade_select')
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
            attempts = QuizAttempt.query.filter_by(
                grade=grade,
                category=category,
                subcategory=subcategory,
                difficulty=difficulty
            ).all()

            if attempts:
                total_attempts = len(attempts)
                total_score_percentage = sum(
                    attempt.score / attempt.total_questions * 100
                    for attempt in attempts
                )
                highest_score_percentage = max(
                    attempt.score / attempt.total_questions * 100
                    for attempt in attempts
                )
                stats[difficulty] = {
                    'attempts': total_attempts,
                    'avg_score': total_score_percentage / total_attempts,
                    'highest_score': highest_score_percentage
                }
            else:
                stats[difficulty] = {
                    'attempts': 0,
                    'avg_score': 0,
                    'highest_score': 0
                }

        logger.info(f"Stats: {stats}")

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
        return redirect(url_for('grade_select'))


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
            return redirect(url_for('select_difficulty', grade=grade,
                            category=category, subcategory=subcategory))

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
        logger.exception("Full traceback:")
        flash('クイズの開始中にエラーが発生しました。', 'error')
        return redirect(url_for('select_difficulty', grade=grade,
                        category=category, subcategory=subcategory))


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
        logger.info(
            f"Received answer - Selected Index: {selected_index}, Type: {type(selected_index)}")
        logger.info(
            f"Current Question State - Number: {current_question + 1}, Total: {len(questions)}")

        if current_question >= len(questions):
            logger.error("Question index out of range")
            return jsonify({'success': False, 'error': '問題が見つかりません'})

        question = questions[current_question]
        correct_index = question['correct']

        # インデックスの比較前の型と値を確認
        logger.info(
            f"Comparing indices - Selected: {selected_index} ({
                type(selected_index)}), Correct: {correct_index} ({
                type(correct_index)})")
        is_correct = str(selected_index) == str(correct_index)
        logger.info(f"Answer is correct: {is_correct}")

        # 最後の問題かどうかを確認
        is_last_question = current_question >= len(questions) - 1
        logger.info(
            f"Question check - Current: {
                current_question +
                1}, Total: {
                len(questions)}, Is Last: {is_last_question}")

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
        logger.info(
            f"Quiz history updated - Total entries: {len(quiz_history)}")

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
                logger.info(
                    f"Quiz attempt saved - Final score: {current_score}/{len(questions)}")
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
                logger.info(
                    f"Last question - Setting redirect URL: {response_data['redirectUrl']}")
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
def dashboard():
    """学習成績ダッシュボードを表示"""
    try:
        # クイズの試行履歴を取得
        quiz_attempts = QuizAttempt.query.order_by(QuizAttempt.timestamp.desc()).all()

        # 進捗データの初期化
        progress = {grade: {} for grade in range(1, 7)}

        # 各学年、カテゴリー、サブカテゴリーごとの進捗を集計
        for grade in range(1, 7):
            for category in CATEGORY_NAMES.keys():
                progress[grade][category] = {
                    'name': CATEGORY_NAMES[category],
                    'subcategories': {}
                }

                for subcategory in get_subcategories(grade, category):
                    progress[grade][category]['subcategories'][subcategory] = {
                        'name': SUBCATEGORY_NAMES[subcategory],
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
        logger.exception("Full traceback:")
        flash('ダッシュボードの表示中にエラーが発生しました。', 'error')
        return redirect(url_for('grade_select'))
    

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
        return redirect(url_for('grade_select'))


def get_subcategories(grade, category):
    """指定された学年とカテゴリのサブカテゴリを取得"""
    # カテゴリに応じたサブカテゴリのマッピング
    category_subcategories = {
        'japanese': ['kanji', 'reading', 'grammar', 'writing'],
        'math': ['calculation', 'figure', 'measurement', 'graph'],
        'science': ['physics', 'chemistry', 'biology', 'earth_science'],
        'society': ['history', 'geography', 'civics', 'current_events', 'prefectures']
    }
    return category_subcategories.get(category, [])


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
            logger.info(
                f"Available difficulties: {
                    list(
                        data[subcategory].keys())}")

            # 難易度の確認
            if difficulty not in data[subcategory]:
                logger.error(
                    f"Difficulty {difficulty} not found in {subcategory}")
                return None, "選択された難易度の問題が見つかりません"

            all_questions = data[subcategory][difficulty]
            if not all_questions:
                logger.error(
                    f"No questions found for {category}/{subcategory}/{difficulty}")
                return None, "問題が見つかりません"

            # 利用可能な問題数を確認
            num_questions = len(all_questions)
            target_questions = min(10, num_questions)  # 10問または利用可能な全問題数の少ない方

            logger.info(f"Total available questions: {num_questions}")
            logger.info(f"Target number of questions: {target_questions}")

            # 問題をランダムに選択
            selected_questions = random.sample(all_questions, target_questions)

            # 各問題の選択肢をシャッフル
            shuffled_questions = [
                get_shuffled_question(q) for q in selected_questions]

            logger.info(
                f"Successfully loaded and shuffled {
                    len(shuffled_questions)} questions")
            for i, q in enumerate(shuffled_questions):
                logger.info(f"Question {i + 1} correct index: {q['correct']}")

            return shuffled_questions, None

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return None, "問題データの形式が正しくありません"
    except Exception as e:
        logger.error(f"Error in get_quiz_data: {e}")
        logger.exception("Full traceback:")
        return None, "問題データの読み込み中にエラーが発生しました"


@app.route('/quiz_history/<int:grade>/<category>/<subcategory>/<difficulty>')
def quiz_history(grade, category, subcategory, difficulty):
    """特定の条件でのクイズ履歴を表示"""
    try:
        # 指定された条件での試行履歴を取得
        attempts = QuizAttempt.query.filter_by(
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty
        ).order_by(QuizAttempt.id.desc()).all()

        # 問題ごとの統計情報を集計
        question_stats = {}
        for attempt in attempts:
            if hasattr(attempt, 'quiz_history') and attempt.quiz_history:
                for question in attempt.quiz_history:
                    q_text = question['question']
                    if q_text not in question_stats:
                        question_stats[q_text] = {
                            'total': 0,
                            'correct': 0,
                            'percentage': 0
                        }

                    question_stats[q_text]['total'] += 1
                    if question['is_correct']:
                        question_stats[q_text]['correct'] += 1

                    # 正答率を更新
                    question_stats[q_text]['percentage'] = (
                        question_stats[q_text]['correct'] /
                        question_stats[q_text]['total'] * 100
                    )

        # 難易度の日本語名を設定
        difficulty_name = {
            'easy': '初級',
            'medium': '中級',
            'hard': '上級'
        }.get(difficulty, difficulty)

        return render_template('quiz_history.html',
                               attempts=attempts,
                               grade=grade,
                               category_name=CATEGORY_NAMES[category],
                               subcategory_name=SUBCATEGORY_NAMES[subcategory],
                               difficulty_name=difficulty_name,
                               question_stats=question_stats)

    except Exception as e:
        logger.error(f"Error in quiz_history route: {e}")
        logger.exception("Full traceback:")
        flash('クイズ履歴の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('dashboard'))
