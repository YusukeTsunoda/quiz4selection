from datetime import datetime
import json
import logging
from flask_sqlalchemy import SQLAlchemy
from extensions import db
from flask_login import UserMixin
import random
from sqlalchemy.dialects.postgresql import JSON as PostgresJSON
import os

logger = logging.getLogger(__name__)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    allowed_subjects = db.Column(PostgresJSON, default=lambda: {
        'japanese': ['kanji', 'reading', 'grammar', 'writing'],
        'math': ['calculation', 'figure', 'measurement', 'graph'],
        'science': ['physics', 'chemistry', 'biology', 'earth_science'],
        'society': ['history', 'geography', 'civics', 'current_events', 'prefectures']
    })
    allowed_grades = db.Column(PostgresJSON, default=lambda: list(range(1, 7)))
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True)

    def get_id(self):
        return str(self.id)

    @staticmethod
    def create_user(id, username, email):
        """ユーザーを作成する"""
        try:
            user = User(
                id=id,
                username=username,
                email=email,
                is_admin=False
            )
            db.session.add(user)
            db.session.commit()
            return user
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.session.rollback()
            raise

    @staticmethod
    def get_by_email(email):
        """メールアドレスでユーザーを検索"""
        return User.query.filter_by(email=email).first()

    def promote_to_admin(self):
        """ユーザーを管理者に昇格"""
        if not self.is_admin:
            self.is_admin = True
            db.session.commit()
            return True
        return False

class QuizAttempt(db.Model):
    """クイズの試行を記録するモデル"""
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    total_questions = db.Column(db.Integer, nullable=False, default=0)
    quiz_history = db.Column(PostgresJSON)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    @property
    def quiz_history_prop(self):
        """クイズ履歴をJSONとして取得"""
        if self.quiz_history is None:
            return []
        
        # すでにリスト型の場合はそのまま返す
        if isinstance(self.quiz_history, list):
            return self.quiz_history
            
        # 文字列の場合はJSONとしてパース
        try:
            return json.loads(self.quiz_history)
        except (TypeError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing quiz history: {e}")
            return []

    @quiz_history_prop.setter
    def quiz_history_prop(self, value):
        """クイズ履歴をJSON形式で保存"""
        if isinstance(value, str):
            self.quiz_history = value
        else:
            self.quiz_history = json.dumps(value)

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
        total_score_percentage = sum(
            attempt.score / attempt.total_questions * 100
            for attempt in attempts
        )
        highest_score_percentage = max(
            attempt.score / attempt.total_questions * 100
            for attempt in attempts
        )

        return {
            'attempts': total_attempts,
            'avg_score': total_score_percentage / total_attempts,
            'highest_score': highest_score_percentage
        }


class QuestionHistory(db.Model):
    __tablename__ = 'question_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    correct_count = db.Column(db.Integer, default=0)
    attempt_count = db.Column(db.Integer, default=0)
    last_attempted_at = db.Column(db.DateTime(timezone=True), default=db.func.now())
    created_at = db.Column(db.DateTime(timezone=True), default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=db.func.now(), onupdate=db.func.now())

    user = db.relationship('User', backref=db.backref('question_history', lazy=True))

    @property
    def correct_rate(self):
        """正答率を計算"""
        if self.attempt_count == 0:
            return 0
        return (self.correct_count / self.attempt_count) * 100

    @classmethod
    def get_questions_for_quiz(cls, user_id, grade, category, subcategory, difficulty, num_questions=10):
        """クイズ用の問題を選択"""
        # 問題データを読み込む
        try:
            from quiz_data.loader import get_questions
            all_questions = get_questions(grade, category, subcategory, difficulty)
            if not all_questions:
                logger.warning(f"問題が見つかりません: grade_{grade}/{category}/{subcategory}/{difficulty}")
                return []
        except Exception as e:
            logger.error(f"問題データの読み込みエラー: {e}")
            return []

        # ユーザーの問題履歴を取得
        history = cls.query.filter_by(
            user_id=user_id,
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty
        ).all()

        # 問題を分類
        unanswered = []  # 未回答問題
        low_correct_rate = []  # 低正答率問題
        high_correct_rate_low_attempts = []  # 高正答率・低回答数問題
        high_correct_rate_high_attempts = []  # 高正答率・高回答数問題

        history_dict = {h.question_text: h for h in history}

        for question in all_questions:
            q_text = question['question']
            if q_text not in history_dict:
                unanswered.append(question)
                continue

            h = history_dict[q_text]
            if h.correct_rate < 50:
                low_correct_rate.append(question)
            elif h.attempt_count < 3:
                high_correct_rate_low_attempts.append(question)
            else:
                high_correct_rate_high_attempts.append(question)

        # 優先順位に基づいて問題を選択
        selected = []
        remaining = num_questions

        # 1. 未回答問題から選択
        selected.extend(random.sample(unanswered, min(remaining, len(unanswered))))
        remaining = num_questions - len(selected)
        if remaining == 0:
            return selected

        # 2. 低正答率問題から選択
        selected.extend(random.sample(low_correct_rate, min(remaining, len(low_correct_rate))))
        remaining = num_questions - len(selected)
        if remaining == 0:
            return selected

        # 3. 高正答率・低回答数問題から選択
        selected.extend(random.sample(high_correct_rate_low_attempts, min(remaining, len(high_correct_rate_low_attempts))))
        remaining = num_questions - len(selected)
        if remaining == 0:
            return selected

        # 4. 高正答率・高回答数問題から選択
        selected.extend(random.sample(high_correct_rate_high_attempts, min(remaining, len(high_correct_rate_high_attempts))))

        # 必要な問題数に満たない場合、全問題からランダムに追加
        remaining = num_questions - len(selected)
        if remaining > 0:
            all_remaining = [q for q in all_questions if q not in selected]
            selected.extend(random.sample(all_remaining, min(remaining, len(all_remaining))))

        return selected

    @classmethod
    def update_question_history(cls, user_id, grade, category, subcategory, difficulty, question_text, is_correct):
        """問題の履歴を更新"""
        history = cls.query.filter_by(
            user_id=user_id,
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty,
            question_text=question_text
        ).first()

        if history is None:
            history = cls(
                user_id=user_id,
                grade=grade,
                category=category,
                subcategory=subcategory,
                difficulty=difficulty,
                question_text=question_text,
                correct_count=1 if is_correct else 0,
                attempt_count=1
            )
            db.session.add(history)
        else:
            history.attempt_count += 1
            if is_correct:
                history.correct_count += 1
            history.last_attempted_at = db.func.now()

        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Error updating question history: {e}")
            db.session.rollback()