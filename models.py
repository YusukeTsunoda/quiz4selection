from flask_login import UserMixin
from datetime import datetime
from extensions import db
from sqlalchemy import func, JSON, desc
import logging
import json
from config import supabase

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
    grade = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    score = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    quiz_history = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """モデルを辞書に変換"""
        return {
            'id': self.id,
            'grade': self.grade,
            'category': self.category,
            'subcategory': self.subcategory,
            'difficulty': self.difficulty,
            'score': self.score,
            'total_questions': self.total_questions,
            'quiz_history': self.quiz_history,
            'timestamp': self.timestamp.isoformat()
        }

    @staticmethod
    def save_to_supabase(attempt_data):
        """クイズ試行データをSupabaseに保存"""
        try:
            if supabase:
                data = supabase.table('quiz_attempts').insert(attempt_data).execute()
                return data
            return None
        except Exception as e:
            print(f"Error saving to Supabase: {e}")
            return None

    @staticmethod
    def get_from_supabase(grade, category, subcategory, difficulty):
        """Supabaseからクイズ試行データを取得"""
        try:
            if supabase:
                data = supabase.table('quiz_attempts')\
                    .select('*')\
                    .eq('grade', grade)\
                    .eq('category', category)\
                    .eq('subcategory', subcategory)\
                    .eq('difficulty', difficulty)\
                    .execute()
                return data.data
            return []
        except Exception as e:
            print(f"Error fetching from Supabase: {e}")
            return []

    def get_percentage(self):
        """正答率を計算"""
        if self.total_questions == 0:
            return 0
        return (self.score / self.total_questions) * 100

    @staticmethod
    def get_stats(grade, category, subcategory, difficulty):
        """統計情報を取得"""
        try:
            if supabase:
                data = QuizAttempt.get_from_supabase(grade, category, subcategory, difficulty)
                if not data:
                    return {'attempts': 0, 'avg_score': 0, 'highest_score': 0}
                
                attempts = len(data)
                scores = [attempt['score'] / attempt['total_questions'] * 100 for attempt in data]
                avg_score = sum(scores) / len(scores) if scores else 0
                highest_score = max(scores) if scores else 0
                
                return {
                    'attempts': attempts,
                    'avg_score': avg_score,
                    'highest_score': highest_score
                }
            return {'attempts': 0, 'avg_score': 0, 'highest_score': 0}
        except Exception as e:
            print(f"Error getting stats from Supabase: {e}")
            return {'attempts': 0, 'avg_score': 0, 'highest_score': 0}

    @staticmethod
    def get_question_stats(grade, category, subcategory, difficulty):
        """問題別の統計情報を取得"""
        try:
            if supabase:
                data = QuizAttempt.get_from_supabase(grade, category, subcategory, difficulty)
                question_stats = {}
                
                for attempt in data:
                    if not attempt.get('quiz_history'):
                        continue
                    
                    for history in attempt['quiz_history']:
                        q_text = history.get('question', '')
                        if not q_text:
                            continue
                            
                        if q_text not in question_stats:
                            question_stats[q_text] = {'correct': 0, 'total': 0}
                            
                        question_stats[q_text]['total'] += 1
                        if history.get('is_correct', False):
                            question_stats[q_text]['correct'] += 1
                
                return question_stats
            return {}
        except Exception as e:
            print(f"Error getting question stats from Supabase: {e}")
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
