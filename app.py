import os
import logging
from datetime import datetime
from flask import Flask, render_template, session, request, jsonify
from extensions import db

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_for_quiz_app")

# Configure database
database_url = os.environ.get("DATABASE_URL")
if database_url is None:
    database_url = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}"

# Ensure proper postgresql:// prefix
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config.update(
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "connect_args": {
            "connect_timeout": 10
        }
    }
)

# Initialize extensions
db.init_app(app)

# Import models and create tables
with app.app_context():
    import models
    db.create_all()

from quiz_data import questions

@app.route('/')
def index():
    # Reset session data at the start
    session['score'] = 0
    session['current_question'] = 0
    logger.debug("Starting new quiz session")
    return render_template('index.html', 
                         question=questions[0],
                         question_number=1,
                         total_questions=len(questions))

@app.route('/next_question', methods=['GET'])
def next_question():
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

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.get_json()
    current_question = session.get('current_question', 0)
    
    if data and 'selected' in data:
        selected = int(data['selected'])
        correct = questions[current_question]['correct']
        
        if selected == correct:
            session['score'] = session.get('score', 0) + 1
            logger.debug(f"Correct answer! New score: {session['score']}")
        
    return jsonify({'success': True})

with app.app_context():
    import models
    db.create_all()
