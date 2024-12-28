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
    'current_events': '時事'
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

def get_prioritized_questions(category, difficulty, num_questions=10):
    """
    優先順位付けされた問題を取得する（10問固定）
    1. まだ回答していない問題
    2. 正答率の低い問題
    3. その他の問題
    """
    try:
        # カテゴリと難易度の全問題を取得
        all_questions = questions_by_category[category][difficulty]
        if len(all_questions) < 10:
            logger.error(f"Not enough questions in {category} - {difficulty}. Only {len(all_questions)} available")
            return all_questions  # 10問未満の場合は全問題を返す
        
        # 問題の統計情報を取得
        stats = QuizAttempt.get_question_stats(category, difficulty)
        
        # 問題を3つのグループに分類
        unanswered_questions = []
        low_accuracy_questions = []
        other_questions = []
        
        for question in all_questions:
            q_text = question['question']
            if q_text not in stats:
                # 未回答の問題
                unanswered_questions.append(question)
            else:
                # 正答率に基づいて分類（50%未満を低正答率とする）
                if stats[q_text]['accuracy'] < 50:
                    low_accuracy_questions.append(question)
                else:
                    other_questions.append(question)
        
        # 各グループをシャッフル
        random.shuffle(unanswered_questions)
        random.shuffle(low_accuracy_questions)
        random.shuffle(other_questions)
        
        # 優先順位に基づいて問題を選択（合計10問）
        selected_questions = []
        
        # 未回答問題から選択（4問）
        num_unanswered = min(len(unanswered_questions), 4)
        selected_questions.extend(unanswered_questions[:num_unanswered])
        
        # 低正答率問題から選択（4問）
        remaining = 10 - len(selected_questions)
        num_low_accuracy = min(len(low_accuracy_questions), 4)
        selected_questions.extend(low_accuracy_questions[:num_low_accuracy])
        
        # 残りをその他の問題から選択（2問）
        remaining = 10 - len(selected_questions)
        if remaining > 0:
            additional_questions = other_questions[:remaining]
            if len(additional_questions) < remaining:
                # その他の問題が足りない場合、未回答問題や低正答率問題から補完
                remaining_pool = unanswered_questions[num_unanswered:] + low_accuracy_questions[num_low_accuracy:]
                if remaining_pool:
                    random.shuffle(remaining_pool)
                    additional_questions.extend(remaining_pool[:remaining - len(additional_questions)])
            selected_questions.extend(additional_questions)
        
        # 10問に満たない場合、残りの問題からランダムに追加
        while len(selected_questions) < 10:
            remaining_questions = [q for q in all_questions if q not in selected_questions]
            if not remaining_questions:
                break
            random.shuffle(remaining_questions)
            selected_questions.append(remaining_questions[0])
        
        # 最終的な問題リストをシャッフル
        random.shuffle(selected_questions)
        return selected_questions[:10]  # 必ず10問を返す
        
    except Exception as e:
        logger.error(f"Error in get_prioritized_questions: {e}")
        # エラーが発生した場合は、通常のランダム選択で10問を選ぶ
        all_questions = questions_by_category[category][difficulty]
        return random.sample(all_questions, min(10, len(all_questions)))

def show_question():
    """現在の問題を表示する"""
    try:
        current_question = session.get('current_question', 0)
        questions = session.get('questions', [])
        
        if not questions or current_question >= len(questions):
            logger.error("No questions available or invalid question index")
            return "An error occurred", 500
            
        return render_template('quiz.html',
                             question=questions[current_question],
                             question_number=current_question + 1,
                             total_questions=len(questions))
    except Exception as e:
        logger.error(f"Error in show_question: {e}")
        return "An error occurred", 500

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
    return render_template('difficulty_select.html',
                         grade=grade,
                         category=category,
                         category_name=CATEGORY_NAMES[category],
                         subcategory=subcategory,
                         subcategory_name=SUBCATEGORY_NAMES[subcategory])

@app.route('/grade/<int:grade>/category/<category>/subcategory/<subcategory>/difficulty/<difficulty>/start')
def start_quiz(grade, category, subcategory, difficulty):
    try:
        # クイズデータを取得
        quiz_data = get_quiz_data(grade, category, subcategory, difficulty)
        if not quiz_data:
            flash('クイズデータが見つかりませんでした。', 'error')
            return redirect(url_for('select_difficulty', grade=grade, category=category, subcategory=subcategory))
        
        # 問題をシャッフルして保存
        shuffled_questions = [get_shuffled_question(q) for q in quiz_data]
        
        # セッションにクイズ情報を保存
        session['questions'] = shuffled_questions
        session['current_question'] = 0
        session['score'] = 0
        session['quiz_history'] = []
        session['grade'] = grade
        session['category'] = category
        session['subcategory'] = subcategory
        session['difficulty'] = difficulty
        
        return show_question()
    except Exception as e:
        logger.error(f"Error in start_quiz: {e}")
        flash('クイズの開始中にエラーが発生しました。', 'error')
        return redirect(url_for('select_difficulty', grade=grade, category=category, subcategory=subcategory))

def get_subcategories(grade, category):
    """指定された学年とカテゴリのサブカテゴリを取得"""
    # カテゴリに応じたサブカテゴリのマッピング
    category_subcategories = {
        'japanese': ['kanji', 'reading', 'grammar', 'writing'],
        'math': ['calculation', 'figure', 'measurement', 'graph'],
        'science': ['physics', 'chemistry', 'biology', 'earth_science'],
        'society': ['history', 'geography', 'civics', 'current_events']
    }
    return category_subcategories.get(category, [])

def get_quiz_data(grade, category, subcategory, difficulty):
    """クイズデータを取得する関数"""
    try:
        file_path = f'quiz_data/grade_{grade}/{category}.json'
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data[subcategory][difficulty]
    except Exception as e:
        print(f"Error loading quiz data: {e}")
        return None

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    try:
        data = request.get_json()
        current_question = session.get('current_question', 0)
        questions = session.get('questions', [])
        
        if data and 'selected' in data and 'time_taken' in data:
            selected = int(data['selected'])
            time_taken = float(data['time_taken'])
            correct = questions[current_question]['correct']
            
            # QuizAttemptの作成と保存
            quiz_attempt = QuizAttempt(
                grade=session.get('grade'),
                category=session.get('category'),
                subcategory=session.get('subcategory'),
                difficulty=session.get('difficulty'),
                question_text=questions[current_question]['question'],
                selected_answer=questions[current_question]['options'][selected],
                correct_answer=questions[current_question]['options'][correct],
                is_correct=(selected == correct),
                time_taken=time_taken
            )
            db.session.add(quiz_attempt)
            db.session.commit()
            
            # セッションのスコアを更新
            if selected == correct:
                session['score'] = session.get('score', 0) + 1
            
            return jsonify({
                'success': True,
                'isLastQuestion': current_question == len(questions) - 1
            })
            
    except Exception as e:
        logger.error(f"Error in submit_answer route: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/next_question', methods=['GET'])
def next_question():
    try:
        current_question = session.get('current_question', 0)
        score = session.get('score', 0)
        questions = session.get('questions', [])
        quiz_history = session.get('quiz_history', [])
        
        logger.debug(f"Moving to question {current_question + 1}, current score: {score}")
        logger.debug(f"Current quiz history: {quiz_history}")
        
        if current_question >= len(questions) - 1:
            logger.debug("Quiz completed")
            logger.debug(f"Final quiz history: {session.get('quiz_history', [])}")
            return render_template('result.html', 
                                score=session.get('score', 0),
                                total_questions=len(questions),
                                quiz_history=session.get('quiz_history', []))
        
        # Update current question
        current_question += 1
        session['current_question'] = current_question
        
        return render_template('quiz.html',
                            question=questions[current_question],
                            question_number=current_question + 1,
                            total_questions=len(questions))
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
        
        # 問題単位の統計情報を取得
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
