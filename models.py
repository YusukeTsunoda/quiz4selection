from flask_login import UserMixin
from datetime import datetime
from extensions import db
from sqlalchemy import func, JSON
import logging

logger = logging.getLogger(__name__)

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
    score = db.Column(db.Integer, nullable=False, default=0)
    total_questions = db.Column(db.Integer, nullable=False, default=0)
    quiz_history = db.Column(JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def get_percentage(self):
        """スコアをパーセンテージで返す"""
        if not self.total_questions or not self.score:
            return 0.0
        return (self.score / self.total_questions) * 100

    @staticmethod
    def get_stats(grade, category, subcategory, difficulty):
        """特定の条件での統計情報を取得"""
        try:
            attempts = QuizAttempt.query.filter_by(
                grade=grade,
                category=category,
                subcategory=subcategory,
                difficulty=difficulty
            ).all()

            if not attempts:
                return {
                    'attempts': 0,
                    'avg_score': 0.0,
                    'highest_score': 0.0
                }

            total_percentage = sum(attempt.get_percentage() for attempt in attempts)
            highest_percentage = max(attempt.get_percentage() for attempt in attempts)

            return {
                'attempts': len(attempts),
                'avg_score': total_percentage / len(attempts),
                'highest_score': highest_percentage
            }
        except Exception as e:
            logger.error(f"Error in get_stats: {e}")
            return {
                'attempts': 0,
                'avg_score': 0.0,
                'highest_score': 0.0
            }

    @staticmethod
    def get_question_stats(grade, category, subcategory, difficulty):
        """問題ごとの統計情報を取得"""
        try:
            attempts = QuizAttempt.query.filter_by(
                grade=grade,
                category=category,
                subcategory=subcategory,
                difficulty=difficulty
            ).all()

            if not attempts:
                return {}

            # 問題ごとの統計を集計
            stats = {}
            for attempt in attempts:
                if not attempt.quiz_history:
                    continue

                for question in attempt.quiz_history:
                    q_text = question.get('question', '')
                    if not q_text:
                        continue

                    if q_text not in stats:
                        stats[q_text] = {
                            'attempts': 0,
                            'correct': 0,
                            'total_time': 0,
                            'correct_rate': 0,
                            'avg_time': 0
                        }

                    stats[q_text]['attempts'] += 1
                    if question.get('is_correct', False):
                        stats[q_text]['correct'] += 1
                    stats[q_text]['total_time'] += question.get('time_taken', 0)

            # 統計を計算
            for q_stats in stats.values():
                if q_stats['attempts'] > 0:
                    q_stats['correct_rate'] = q_stats['correct'] / q_stats['attempts']
                    q_stats['avg_time'] = q_stats['total_time'] / q_stats['attempts']

            return stats
        except Exception as e:
            logger.error(f"Error in get_question_stats: {e}")
            return {}
