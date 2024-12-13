import os
import random
import logging
from flask import Flask, render_template, session, request, jsonify
from extensions import db
from models import QuizAttempt
from sqlalchemy import func
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_for_quiz_app")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

from quiz_data import questions_by_category

@app.route('/')
def index():
    try:
        # Show category selection page
        categories = list(questions_by_category.keys())
        return render_template('category_select.html', categories=categories)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return "An error occurred", 500

@app.route('/select_difficulty/<category>')
def select_difficulty(category):
    try:
        difficulties = ["easy", "medium", "hard"]
        return render_template('difficulty_select.html', 
                             category=category,
                             difficulties=difficulties)
    except Exception as e:
        logger.error(f"Error in select_difficulty route: {e}")
        return "An error occurred", 500

@app.route('/start_quiz/<category>/<difficulty>')
def start_quiz(category, difficulty):
    try:
        # Get questions for the selected category and difficulty
        questions = questions_by_category[category][difficulty]
        # Select 5 random questions
        selected_questions = random.sample(questions, min(5, len(questions)))
        
        # Randomize options for each question
        for question in selected_questions:
            options = question['options'].copy()
            correct_option = options[question['correct']]
            random.shuffle(options)
            question['correct'] = options.index(correct_option)
            question['options'] = options
        
        # Initialize session variables
        session['questions'] = selected_questions
        session['current_question'] = 0
        session['score'] = 0
        session['category'] = category
        session['difficulty'] = difficulty
        session['incorrect_questions'] = []
        
        logger.debug(f"Starting new quiz session: {category} - {difficulty} with 5 questions")
        
        return render_template('quiz.html', 
                            question=session['questions'][0],
                            question_number=1,
                            total_questions=len(session['questions']))
    except Exception as e:
        logger.error(f"Error in start_quiz route: {e}")
        return "An error occurred", 500

@app.route('/next_question', methods=['GET'])
def next_question():
    try:
        current_question = session.get('current_question', 0)
        score = session.get('score', 0)
        questions = session.get('questions', [])
        
        # Update current question
        current_question += 1
        session['current_question'] = current_question
        
        logger.debug(f"Moving to question {current_question + 1}, current score: {score}")
        
        if current_question >= 5:  # Fixed number of questions
            logger.debug("Quiz completed")
            return render_template('result.html', 
                                score=score,
                                total_questions=5)
        
        return render_template('quiz.html',
                            question=questions[current_question],
                            question_number=current_question + 1,
                            total_questions=5)
    except Exception as e:
        logger.error(f"Error in next_question route: {e}")
        return "An error occurred", 500

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    try:
        data = request.get_json()
        current_question = session.get('current_question', 0)
        questions = session.get('questions', [])
        
        if data and 'selected' in data:
            selected = int(data['selected'])
            correct = questions[current_question]['correct']
            
            # Initialize incorrect_questions list if not exists
            if 'incorrect_questions' not in session:
                session['incorrect_questions'] = []
            
            logger.debug(f"Current incorrect questions: {session.get('incorrect_questions', [])}")
            
            # Record question attempt regardless of correctness
            question_record = {
                'question': questions[current_question]['question'],
                'selected': questions[current_question]['options'][selected],
                'correct': questions[current_question]['options'][correct],
                'options': questions[current_question]['options'],
                'correct_answer': selected == correct
            }
            if 'quiz_history' not in session:
                session['quiz_history'] = []
            session['quiz_history'].append(question_record)
            logger.debug(f"Question added to history")

            if selected == correct:
                session['score'] = session.get('score', 0) + 1
                logger.debug(f"Correct answer! New score: {session['score']}")
            
        # クイズが完了したら結果を保存（非同期的に）
            if current_question == len(questions) - 1:
                try:
                    quiz_attempt = QuizAttempt(
                        category=session.get('category'),
                        difficulty=session.get('difficulty'),
                        score=session.get('score', 0),
                        questions_history=session.get('quiz_history', [])
                    )
                    db.session.add(quiz_attempt)
                    db.session.commit()
                    logger.debug("Quiz attempt saved to database")
                except Exception as e:
                    logger.error(f"Error saving quiz attempt: {e}")
                    db.session.rollback()
            
            return jsonify({
                'success': True,
                'isLastQuestion': current_question == len(questions) - 1
            })
    except Exception as e:
        logger.error(f"Error in submit_answer route: {e}")
        return jsonify({'success': False, 'error': str(e)})
@app.route('/dashboard')
def dashboard():
    try:
        # 全カテゴリーの進捗を取得
        progress = {}
        for category in questions_by_category.keys():
            progress[category] = {}
            for difficulty in ['easy', 'medium', 'hard']:
                attempts = QuizAttempt.query.filter_by(
                    category=category,
                    difficulty=difficulty
                ).all()
                
                stats = {
                    'attempts': len(attempts),
                    'avg_score': sum(attempt.get_percentage() for attempt in attempts) / len(attempts) if attempts else 0,
                    'highest_score': max((attempt.get_percentage() for attempt in attempts), default=0)
                }
                progress[category][difficulty] = stats
        
        return render_template('dashboard.html', progress=progress)
    except Exception as e:
        logger.error(f"Error in dashboard route: {e}")
        return "An error occurred", 500

@app.route('/quiz_history/<category>/<difficulty>')
def quiz_history(category, difficulty):
    try:
        attempts = QuizAttempt.query.filter_by(
            category=category,
            difficulty=difficulty
        ).order_by(QuizAttempt.timestamp.desc()).all()
        
        return render_template('quiz_history.html',
                             category=category,
                             difficulty=difficulty,
                             attempts=attempts)
    except Exception as e:
        logger.error(f"Error in quiz_history route: {e}")
        return "An error occurred", 500