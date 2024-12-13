import os
import logging
from flask import Flask, render_template, session, request, jsonify

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_for_quiz_app")

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
        # Reset session data and store category/difficulty
        session['score'] = 0
        session['current_question'] = 0
        session['category'] = category
        session['difficulty'] = difficulty
        
        import random
        # Get all questions and randomly select 5
        all_questions = questions_by_category[category][difficulty]
        session['questions'] = random.sample(all_questions, 5)  # Randomly select 5 questions
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
            
            if selected == correct:
                session['score'] = session.get('score', 0) + 1
                logger.debug(f"Correct answer! New score: {session['score']}")
            else:
                # Save incorrect question with correct answer for review
                incorrect_question = {
                    'question': questions[current_question]['question'],
                    'selected': questions[current_question]['options'][selected],
                    'correct': questions[current_question]['options'][correct],
                    'options': questions[current_question]['options']
                }
                session['incorrect_questions'].append(incorrect_question)
                logger.debug(f"Question added to review list")
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error in submit_answer route: {e}")
        return jsonify({'success': False, 'error': str(e)})