from flask_login import UserMixin
from datetime import datetime
from extensions import db
from sqlalchemy import func, JSON, desc
import logging
import json

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
            # 既存の回答履歴を取得
            attempts = cls.query.filter_by(
                grade=grade,
                category=category,
                subcategory=subcategory,
                difficulty=difficulty
            ).order_by(desc(cls.timestamp)).all()

            # 問題データを読み込む
            quiz_file = f'quiz_data/grade_{grade}/{category}.json'
            with open(quiz_file, 'r', encoding='utf-8') as f:
                quiz_data = json.load(f)

            # 該当するカテゴリと難易度の全問題を取得
            all_questions = quiz_data.get(subcategory, {}).get(difficulty, [])
            question_stats = {}

            # まず全問題を統計情報に追加（未回答状態で）
            for q in all_questions:
                question = q.get('question')
                if question:
                    question_stats[question] = {
                        'attempts': 0,
                        'correct': 0,
                        'total_time': 0,
                        'recent_answers': [],
                        'is_answered': False  # 回答済みフラグを追加
                    }

            # 回答履歴から統計情報を更新
            for attempt in attempts:
                if not attempt.quiz_history:
                    continue

                for history in attempt.quiz_history:
                    question = history.get('question')
                    if not question or question not in question_stats:
                        continue

                    stats = question_stats[question]
                    stats['attempts'] += 1
                    stats['is_answered'] = True  # 回答済みとマーク
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

            # 平均時間と正答率を計算
            for stats in question_stats.values():
                if stats['attempts'] > 0:
                    stats['avg_time'] = stats['total_time'] / stats['attempts']
                    stats['correct_rate'] = stats['correct'] / stats['attempts']
                else:
                    stats['avg_time'] = 0
                    stats['correct_rate'] = 0

            # 問題を出題済みと未出題で分類してソート
            sorted_stats = {}
            
            # 1. 出題済みの問題を追加（正答率の高い順）
            answered_questions = {q: stats for q, stats in question_stats.items() if stats['is_answered']}
            sorted_answered = sorted(
                answered_questions.items(),
                key=lambda x: (x[1]['correct_rate'], x[1]['attempts']),
                reverse=True
            )
            for question, stats in sorted_answered:
                sorted_stats[question] = stats

            # 2. 未出題の問題を追加
            unanswered_questions = {q: stats for q, stats in question_stats.items() if not stats['is_answered']}
            sorted_unanswered = sorted(unanswered_questions.items(), key=lambda x: x[0])  # 問題文でソート
            for question, stats in sorted_unanswered:
                sorted_stats[question] = stats

            return sorted_stats

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
