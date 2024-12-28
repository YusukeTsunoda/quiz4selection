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
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    grade = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)
    selected_answer = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    time_taken = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @staticmethod
    def get_stats(grade, category, subcategory, difficulty):
        """特定の条件での統計情報を取得"""
        attempts = QuizAttempt.query.filter_by(
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty
        ).all()

        if not attempts:
            return {
                'attempts': 0,
                'avg_score': 0,
                'highest_score': 0
            }

        total_attempts = len(attempts)
        correct_attempts = sum(1 for attempt in attempts if attempt.is_correct)
        avg_score = (correct_attempts / total_attempts) * 100
        highest_score = 100 if correct_attempts > 0 else 0

        return {
            'attempts': total_attempts,
            'avg_score': avg_score,
            'highest_score': highest_score
        }

    @staticmethod
    def get_question_stats(grade, category, subcategory, difficulty):
        """問題ごとの統計情報を取得"""
        attempts = QuizAttempt.query.filter_by(
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty
        ).all()

        stats = {}
        for attempt in attempts:
            if attempt.question_text not in stats:
                stats[attempt.question_text] = {
                    'attempts': 0,
                    'correct': 0,
                    'total_time': 0
                }
            
            stats[attempt.question_text]['attempts'] += 1
            if attempt.is_correct:
                stats[attempt.question_text]['correct'] += 1
            stats[attempt.question_text]['total_time'] += attempt.time_taken

        # 統計情報の計算
        for question in stats:
            attempts = stats[question]['attempts']
            stats[question]['correct_rate'] = stats[question]['correct'] / attempts
            stats[question]['avg_time'] = stats[question]['total_time'] / attempts

        return stats

    @staticmethod
    def get_question_history(grade, category, subcategory, difficulty, question_text):
        """特定の問題の履歴を取得"""
        attempts = QuizAttempt.query.filter_by(
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty,
            question_text=question_text
        ).order_by(QuizAttempt.timestamp.desc()).all()

        return [{
            'timestamp': attempt.timestamp,
            'is_correct': attempt.is_correct,
            'time_taken': attempt.time_taken,
            'selected_answer': attempt.selected_answer,
            'correct_answer': attempt.correct_answer
        } for attempt in attempts]
