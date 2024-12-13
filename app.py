import os
import logging
from flask import Flask, render_template, session, request, jsonify

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_for_quiz_app")

from quiz_data import questions

@app.route('/')
def index():
    try:
        # Reset session data at the start
        session['score'] = 0
        session['current_question'] = 0
        logger.debug("Starting new quiz session")
        return render_template('index.html', 
                            question=questions[0],
                            question_number=1,
                            total_questions=len(questions))
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return "An error occurred", 500

@app.route('/next_question', methods=['GET'])
def next_question():
    try:
        current_question = session.get('current_question', 0)
        score = session.get('score', 0)
        
        # Update current question
        current_question += 1
        session['current_question'] = current_question
        
        logger.debug(f"Moving to question {current_question + 1}, current score: {score}")
        
        if current_question >= len(questions):
            logger.debug("Quiz completed")
            return render_template('result.html', 
                                score=score,
                                total_questions=len(questions))
        
        return render_template('index.html',
                            question=questions[current_question],
                            question_number=current_question + 1,
                            total_questions=len(questions))
    except Exception as e:
        logger.error(f"Error in next_question route: {e}")
        return "An error occurred", 500

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    try:
        data = request.get_json()
        current_question = session.get('current_question', 0)
        
        if data and 'selected' in data:
            selected = int(data['selected'])
            correct = questions[current_question]['correct']
            
            if selected == correct:
                session['score'] = session.get('score', 0) + 1
                logger.debug(f"Correct answer! New score: {session['score']}")
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error in submit_answer route: {e}")
        return jsonify({'success': False, 'error': str(e)})
