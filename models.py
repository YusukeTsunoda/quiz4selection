from flask_login import UserMixin
from datetime import datetime
from extensions import db
from sqlalchemy import func, JSON, desc
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

    @classmethod
    def get_stats(cls, grade, category, subcategory, difficulty):
        """特定の条件での統計情報を取得"""
        try:
            attempts = cls.query.filter_by(
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

    @classmethod
    def get_question_stats(cls, grade, category, subcategory, difficulty):
        """問題ごとの統計情報を取得"""
        try:
            attempts = cls.query.filter_by(
                grade=grade,
                category=category,
                subcategory=subcategory,
                difficulty=difficulty
            ).order_by(desc(cls.timestamp)).all()

            question_stats = {}

            for attempt in attempts:
                if not attempt.quiz_history:
                    continue

                for history in attempt.quiz_history:
                    question = history.get('question')
                    if not question:
                        continue

                    if question not in question_stats:
                        question_stats[question] = {
                            'attempts': 0,
                            'correct': 0,
                            'total_time': 0,
                            'recent_answers': []
                        }

                    stats = question_stats[question]
                    stats['attempts'] += 1
                    if history.get('is_correct'):
                        stats['correct'] += 1
                    stats['total_time'] += history.get('time_taken', 0)

                    # 回答履歴を追加
                    answer_record = {
                        'timestamp': attempt.timestamp,
                        'is_correct': history.get('is_correct'),
                        'selected_option': history.get('selected_option'),
                        'correct_option': history.get('correct_option'),
                        'time_taken': history.get('time_taken', 0)
                    }
                    stats['recent_answers'].append(answer_record)

            # 統計を計算して整形
            for question, stats in question_stats.items():
                stats['correct_rate'] = stats['correct'] / stats['attempts'] if stats['attempts'] > 0 else 0
                stats['avg_time'] = stats['total_time'] / stats['attempts'] if stats['attempts'] > 0 else 0
                # 最新10件の回答のみを保持
                stats['recent_answers'] = sorted(
                    stats['recent_answers'],
                    key=lambda x: x['timestamp'],
                    reverse=True
                )[:10]

            return question_stats
        except Exception as e:
            logger.error(f"Error in get_question_stats: {e}")
            return {}

    @classmethod
    def get_question_history(cls, grade, category, subcategory, difficulty, question_text):
        """特定の問題の回答履歴を取得"""
        attempts = cls.query.filter_by(
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty
        ).order_by(desc(cls.timestamp)).all()

        history = []
        for attempt in attempts:
            if not attempt.quiz_history:
                continue

            for question in attempt.quiz_history:
                if question.get('question') == question_text:
                    history.append({
                        'timestamp': attempt.timestamp,
                        'is_correct': question.get('is_correct'),
                        'selected_option': question.get('selected_option'),
                        'correct_option': question.get('correct_option'),
                        'time_taken': question.get('time_taken', 0)
                    })

        return sorted(history, key=lambda x: x['timestamp'], reverse=True)
