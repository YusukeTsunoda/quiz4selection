from flask_login import UserMixin
from datetime import datetime
from extensions import db
from sqlalchemy import func

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    high_score = db.Column(db.Integer, default=0)
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True)

class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    questions_history = db.Column(db.JSON, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def get_percentage(self):
        try:
            if not self.questions_history or len(self.questions_history) == 0:
                return 0
            return (self.score / len(self.questions_history)) * 100
        except Exception as e:
            return 0

    @classmethod
    def get_question_history(cls, category, difficulty, question_text):
        """問題単位での履歴を取得"""
        attempts = cls.query.filter_by(
            category=category,
            difficulty=difficulty
        ).order_by(cls.timestamp.desc()).all()

        question_history = []
        for attempt in attempts:
            for question in attempt.questions_history:
                if question['question'] == question_text:
                    question_history.append({
                        'timestamp': attempt.timestamp,
                        'selected': question['selected'],
                        'correct': question['correct'],
                        'is_correct': question['correct_answer']
                    })
        return question_history

    @classmethod
    def get_question_stats(cls, category, difficulty):
        """問題ごとの統計情報を取得"""
        attempts = cls.query.filter_by(
            category=category,
            difficulty=difficulty
        ).all()

        question_stats = {}
        for attempt in attempts:
            for question in attempt.questions_history:
                q_text = question['question']
                if q_text not in question_stats:
                    question_stats[q_text] = {
                        'total_attempts': 0,
                        'correct_attempts': 0,
                        'history': []
                    }
                
                question_stats[q_text]['total_attempts'] += 1
                if question['correct_answer']:
                    question_stats[q_text]['correct_attempts'] += 1
                
                question_stats[q_text]['history'].append({
                    'timestamp': attempt.timestamp,
                    'selected': question['selected'],
                    'correct': question['correct'],
                    'is_correct': question['correct_answer']
                })

        # 正答率の計算
        for stats in question_stats.values():
            stats['accuracy'] = (stats['correct_attempts'] / stats['total_attempts']) * 100
            stats['history'].sort(key=lambda x: x['timestamp'], reverse=True)

        return question_stats
