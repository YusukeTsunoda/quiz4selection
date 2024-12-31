from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy

# データベースインスタンスの作成
db = SQLAlchemy()

class QuizAttempt(db.Model):
    """クイズの試行を記録するモデル"""
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)
    grade = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    total_questions = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    _quiz_history = db.Column('quiz_history', db.Text, nullable=True)

    @property
    def quiz_history(self):
        """クイズ履歴をJSONとして取得"""
        if self._quiz_history:
            return json.loads(self._quiz_history)
        return []

    @quiz_history.setter
    def quiz_history(self, value):
        """クイズ履歴をJSON形式で保存"""
        self._quiz_history = json.dumps(value) if value else None

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
                'total_attempts': 0,
                'avg_score': 0,
                'highest_score': 0
            }

        total_attempts = len(attempts)
        total_score_percentage = sum(
            attempt.score / attempt.total_questions * 100
            for attempt in attempts
        )
        highest_score_percentage = max(
            attempt.score / attempt.total_questions * 100
            for attempt in attempts
        )

        return {
            'total_attempts': total_attempts,
            'avg_score': total_score_percentage / total_attempts,
            'highest_score': highest_score_percentage
        }
