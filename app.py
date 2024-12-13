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
        session['quiz_history'] = []
        
        logger.debug(f"Starting new quiz session: {category} - {difficulty} with 5 questions")
        
        return render_template('quiz.html', 
                            question=session['questions'][0],
                            question_number=1,
                            total_questions=len(session['questions']))
    except Exception as e:
        logger.error(f"Error in start_quiz route: {e}")
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
            
            # Record question attempt with detailed information
            question_record = {
                'question': questions[current_question]['question'],
                'selected': questions[current_question]['options'][selected],
                'correct': questions[current_question]['options'][correct],
                'correct_answer': selected == correct
            }
            
            # Initialize quiz_history if not exists
            if 'quiz_history' not in session:
                session['quiz_history'] = []
            
            # Update quiz history
            quiz_history = session['quiz_history']
            quiz_history.append(question_record)
            session['quiz_history'] = quiz_history
            session.modified = True  # Ensure session is saved
            logger.debug(f"Question {current_question + 1} added to history: {'correct' if selected == correct else 'incorrect'}")

            # Update score if answer is correct
            if selected == correct:
                session['score'] = session.get('score', 0) + 1
                logger.debug(f"Correct answer! New score: {session['score']}")

            # Save quiz attempt if this is the last question
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
                    logger.debug(f"Final quiz history: {session.get('quiz_history', [])}")
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