import os
import random
import logging
from flask import Flask, render_template, session, request, jsonify, flash, redirect, url_for
from extensions import db
from models import QuizAttempt
from config import Config
from flask_migrate import Migrate
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

# Create database tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

from quiz_data import questions_by_category

# カテゴリ名の日本語マッピング
CATEGORY_NAMES = {
    'japanese': '国語',
    'math': '算数',
    'science': '理科',
    'society': '社会'
}

# サブカテゴリ名の日本語マッピング
SUBCATEGORY_NAMES = {
    # 国語
    'kanji': '漢字',
    'reading': '読解',
    'grammar': '文法',
    'writing': '作文',
    # 算数
    'calculation': '計算',
    'figure': '図形',
    'measurement': '測定',
    'graph': 'グラフ',
    # 理科
    'physics': '物理',
    'chemistry': '化学',
    'biology': '生物',
    'earth_science': '地学',
    # 社会
    'history': '歴史',
    'geography': '地理',
    'civics': '公民',
    'current_events': '時事',
    'prefectures': '都道府県'
}

def get_shuffled_question(question):
    """
    問題の選択肢をランダムにシャッフルし、correct indexも更新する
    """
    # 元の選択肢と正解のインデックスを保持
    original_options = question['options'].copy()
    original_correct = question['correct']
    
    # 選択肢と正解のインデックスをペアにする
    pairs = list(enumerate(original_options))
    
    # ペアをシャッフル
    random.shuffle(pairs)
    
    # シャッフルされた選択肢と新しい正解のインデックスを取得
    shuffled_indices, shuffled_options = zip(*pairs)
    new_correct = shuffled_indices.index(original_correct)
    
    # 問題のコピーを作成し、シャッフルされた情報で更新
    shuffled_question = question.copy()
    shuffled_question['options'] = list(shuffled_options)
    shuffled_question['correct'] = new_correct
    
    return shuffled_question

def get_prioritized_questions(questions, grade, category, subcategory, difficulty):
    """
    優先順位付けされた問題を取得する
    1. まだ回答していない問題
    2. 正答率の低い問題
    3. その他の問題
    """
    try:
        total_questions = len(questions)
        if total_questions == 0:
            logger.error(f"No questions available in {category} - {subcategory} - {difficulty}")
            return None
            
        # 問題の統計情報を取得
        attempts = QuizAttempt.query.filter_by(
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty
        ).all()
        
        # 問題を3つのグループに分類
        unanswered_questions = []
        low_accuracy_questions = []
        other_questions = []
        
        # 問題ごとの正答率を計算
        question_stats = {}
        for attempt in attempts:
            if not hasattr(attempt, 'quiz_history') or not attempt.quiz_history:
                continue
                
            for history in attempt.quiz_history:
                q_text = history.get('question', '')
                if not q_text:
                    continue
                    
                if q_text not in question_stats:
                    question_stats[q_text] = {'correct': 0, 'total': 0}
                    
                question_stats[q_text]['total'] += 1
                if history.get('is_correct', False):
                    question_stats[q_text]['correct'] += 1
        
        # 問題を分類
        for question in questions:
            q_text = question['question']
            if q_text not in question_stats:
                # 未回答の問題
                unanswered_questions.append(question)
            else:
                # 正答率に基づいて分類（50%未満を低正答率とする）
                stats = question_stats[q_text]
                accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
                if accuracy < 50:
                    low_accuracy_questions.append(question)
                else:
                    other_questions.append(question)
        
        # 各グループをシャッフル
        random.shuffle(unanswered_questions)
        random.shuffle(low_accuracy_questions)
        random.shuffle(other_questions)
        
        # 優先順位に基づいて問題を選択
        target_questions = min(10, total_questions)  # 最大10問
        selected_questions = []
        
        # 1. まず未回答の問題を追加
        remaining = target_questions
        if unanswered_questions:
            num_unanswered = min(len(unanswered_questions), remaining)
            selected_questions.extend(unanswered_questions[:num_unanswered])
            remaining -= num_unanswered
            
        # 2. 次に低正答率の問題を追加
        if remaining > 0 and low_accuracy_questions:
            num_low_accuracy = min(len(low_accuracy_questions), remaining)
            selected_questions.extend(low_accuracy_questions[:num_low_accuracy])
            remaining -= num_low_accuracy
            
        # 3. 最後にその他の問題を追加
        if remaining > 0 and other_questions:
            num_other = min(len(other_questions), remaining)
            selected_questions.extend(other_questions[:num_other])
            
        return selected_questions
        
    except Exception as e:
        logger.error(f"Error in get_prioritized_questions: {e}")
        return None

@app.route('/show_question')
def show_question():
    """現在の問題を表示する"""
    try:
        current_question = session.get('current_question', 0)
        questions = session.get('questions', [])
        total_questions = len(questions)
        
        if not questions or current_question >= total_questions:
            logger.error("No questions available or invalid question index")
            return redirect(url_for('select_grade'))
            
        # 現在の正答数を取得
        current_score = session.get('score', 0)
        
        # セッションに保存された問題をそのまま使用（再シャッフルしない）
        current_q = questions[current_question]
        
        logger.info(f"Showing question {current_question + 1} of {total_questions}")
        logger.info(f"Current question correct index: {current_q['correct']}")
            
        return render_template('quiz.html',
                             question=current_q,
                             question_number=current_question + 1,
                             total_questions=total_questions,
                             correct_answers=current_score)
    except Exception as e:
        logger.error(f"Error in show_question: {e}")
        return redirect(url_for('select_grade'))

@app.route('/')
def select_grade():
    return render_template('grade_select.html')

@app.route('/grade/<int:grade>/category')
def select_category(grade):
    return render_template('category_select.html', grade=grade)

@app.route('/grade/<int:grade>/category/<category>/subcategory')
def select_subcategory(grade, category):
    # カテゴリに応じたサブカテゴリのリストを取得
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
            return redirect(url_for('select_grade'))

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Loaded data keys: {list(data.keys())}")
            
            if subcategory not in data:
                logger.error(f"Subcategory {subcategory} not found in data")
                flash('選択されたカテゴリーの問題が見つかりません。', 'error')
                return redirect(url_for('select_grade'))
            
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
        # 問題データを取得
        questions, error = get_quiz_data(grade, category, subcategory, difficulty)
        if error or not questions:
            logger.error(f"Error getting questions: {error}")
            return []
            
        # 問題をランダムに選択し、10問を選択
        if len(questions) > 10:
            selected_questions = random.sample(questions, 10)
        else:
            selected_questions = questions
        
        return selected_questions
    except Exception as e:
        logger.error(f"Error in get_questions: {e}")
        return []

@app.route('/start_quiz/<int:grade>/<category>/<subcategory>/<difficulty>')
def start_quiz(grade, category, subcategory, difficulty):
    """クイズを開始する"""
    try:
        # セッションをクリア
        session.clear()
        
        # 問題を取得
        questions = get_questions(grade, category, subcategory, difficulty)
        if not questions:
            flash('問題の取得に失敗しました。', 'error')
            return redirect(url_for('select_difficulty', grade=grade, category=category, subcategory=subcategory))
            
        # デバッグログを追加
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
        
        # 最初の問題を表示
        return redirect(url_for('show_question'))
        
    except Exception as e:
        logger.error(f"Error in start_quiz: {e}")
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
        
        if not os.path.exists(file_path):
            logger.error(f"Quiz data file not found: {file_path}")
            return None, "問題データファイルが見つかりません"
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            if subcategory not in data:
                logger.error(f"Subcategory {subcategory} not found in {category}.json")
                return None, "選択されたサブカテゴリーの問題が見つかりません"
                
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
            
    except Exception as e:
        logger.error(f"Error in get_quiz_data: {e}")
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
        
        # 最後の問題かどうかを確認（スコア更新前）
        is_last_question = (current_question + 1) >= len(questions)
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
                redirect_url = url_for('result')
                response_data['redirectUrl'] = redirect_url
                logger.info(f"Last question - Setting redirect URL: {redirect_url}")
            except Exception as e:
                logger.error(f"Error building redirect URL: {e}")
                response_data['redirectUrl'] = '/result'  # フォールバックとしてハードコードされたURLを使用
        else:
            # 次の問題のインデックスを更新（最後の問題でない場合のみ）
            next_question = current_question + 1
            session['current_question'] = next_question
            logger.info(f"Next question index set to: {next_question}")
        
        # 最終レスポンスの内容を確認
        logger.info(f"Sending response: {response_data}")
        return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"Error in submit_answer: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/next_question', methods=['GET'])
def next_question():
    try:
        questions = session.get('questions', [])
        current_question = session.get('current_question', 0)
        quiz_history = session.get('quiz_history', [])
        
        logger.debug(f"Current question index: {current_question}")
        logger.debug(f"Quiz history: {quiz_history}")
        
        # 全問題が終了した場合
        if current_question >= len(questions):
            logger.debug("Quiz completed")
            logger.debug(f"Final quiz history: {quiz_history}")
            return render_template('result.html', 
                                correct_answers=session.get('score', 0),
                                total_questions=len(questions),
                                quiz_history=quiz_history)
        
        # 現在の問題を表示
        return render_template('quiz.html',
                            question=questions[current_question],
                            question_number=current_question + 1,
                            total_questions=len(questions),
                            correct_answers=session.get('score', 0))
    except Exception as e:
        logger.error(f"Error in next_question route: {e}")
        return "An error occurred", 500

@app.route('/dashboard')
def dashboard():
    try:
        # 全学年の進捗を取得
        progress = {}
        for grade in range(1, 7):  # 1年生から6年生まで
            progress[grade] = {}
            for category, category_name in CATEGORY_NAMES.items():
                progress[grade][category] = {
                    'name': category_name,
                    'subcategories': {}
                }
                # カテゴリごとのサブカテゴリを取得
                subcategories = get_subcategories(grade, category)
                for subcategory in subcategories:
                    progress[grade][category]['subcategories'][subcategory] = {
                        'name': SUBCATEGORY_NAMES[subcategory],
                        'levels': {}
                    }
                    for difficulty in ['easy', 'medium', 'hard']:
                        try:
                            attempts = QuizAttempt.query.filter_by(
                                grade=grade,
                                category=category,
                                subcategory=subcategory,
                                difficulty=difficulty
                            ).all()
                            
                            if not attempts:
                                stats = {
                                    'attempts': 0,
                                    'avg_score': 0,
                                    'highest_score': 0
                                }
                            else:
                                stats = {
                                    'attempts': len(attempts),
                                    'avg_score': sum(attempt.get_percentage() for attempt in attempts) / len(attempts),
                                    'highest_score': max((attempt.get_percentage() for attempt in attempts), default=0)
                                }
                            progress[grade][category]['subcategories'][subcategory]['levels'][difficulty] = stats
                        except Exception as e:
                            logger.error(f"Error processing {grade}年生 - {category} - {subcategory} - {difficulty}: {e}")
                            progress[grade][category]['subcategories'][subcategory]['levels'][difficulty] = {
                                'attempts': 0,
                                'avg_score': 0,
                                'highest_score': 0
                            }
        
        return render_template('dashboard.html', 
                             progress=progress,
                             difficulty_names={'easy': 'かんたん', 'medium': 'ふつう', 'hard': 'むずかしい'})
    except Exception as e:
        logger.error(f"Error in dashboard route: {e}")
        return "An error occurred", 500

@app.route('/quiz_history/<int:grade>/<category>/<subcategory>/<difficulty>')
def quiz_history(grade, category, subcategory, difficulty):
    try:
        # 通常の試行履歴を取得
        attempts = QuizAttempt.query.filter_by(
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty
        ).order_by(QuizAttempt.timestamp.desc()).all()
        
        # 問題別の統計情報を取得
        question_stats = QuizAttempt.get_question_stats(grade, category, subcategory, difficulty)
        
        return render_template('quiz_history.html',
                             grade=grade,
                             category=category,
                             category_name=CATEGORY_NAMES[category],
                             subcategory=subcategory,
                             subcategory_name=SUBCATEGORY_NAMES[subcategory],
                             difficulty=difficulty,
                             difficulty_name={'easy': 'かんたん', 'medium': 'ふつう', 'hard': 'むずかしい'}[difficulty],
                             attempts=attempts,
                             question_stats=question_stats)
    except Exception as e:
        logger.error(f"Error in quiz_history route: {e}")
        return "An error occurred", 500

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
            return redirect(url_for('select_grade'))
            
        logger.info(f"Showing result page - Score: {score}/{total_questions}")
        
        return render_template('result.html',
                             correct_answers=score,
                             total_questions=total_questions,
                             quiz_history=quiz_history)
                             
    except Exception as e:
        logger.error(f"Error in result route: {e}")
        return redirect(url_for('select_grade'))
