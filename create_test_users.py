from app import app
from models import db, User
from datetime import datetime

def create_test_users():
    """開発環境用のテストユーザーを作成"""
    users = [
        {
            'id': 'dev-student-1',
            'username': 'tanaka_ichiro',
            'email': 'tanaka1@example.com',
            'is_admin': False,
            'allowed_grades': [1],  # 1年生のみ
            'allowed_subjects': {
                'japanese': ['kanji', 'reading'],
                'math': ['calculation']
            }
        },
        {
            'id': 'dev-student-3',
            'username': 'suzuki_hanako',
            'email': 'suzuki3@example.com',
            'is_admin': False,
            'allowed_grades': [3],  # 3年生のみ
            'allowed_subjects': {
                'japanese': ['kanji', 'reading', 'grammar'],
                'math': ['calculation', 'figure'],
                'science': ['physics']
            }
        },
        {
            'id': 'dev-student-5',
            'username': 'sato_taro',
            'email': 'sato5@example.com',
            'is_admin': False,
            'allowed_grades': [5],  # 5年生のみ
            'allowed_subjects': {
                'japanese': ['kanji', 'reading', 'grammar', 'writing'],
                'math': ['calculation', 'figure', 'measurement'],
                'science': ['physics', 'chemistry'],
                'society': ['history', 'geography']
            }
        },
        {
            'id': 'dev-parent',
            'username': 'yamada_parent',
            'email': 'yamada_p@example.com',
            'is_admin': False,
            'allowed_grades': [1, 2, 3, 4, 5, 6],  # 全学年
            'allowed_subjects': {
                'japanese': ['kanji', 'reading', 'grammar', 'writing'],
                'math': ['calculation', 'figure', 'measurement', 'graph'],
                'science': ['physics', 'chemistry', 'biology', 'earth_science'],
                'society': ['history', 'geography', 'civics', 'current_events', 'prefectures']
            }
        },
        {
            'id': 'dev-teacher',
            'username': 'sensei',
            'email': 'teacher@example.com',
            'is_admin': True,  # 教師は管理者権限を持つ
            'allowed_grades': [1, 2, 3, 4, 5, 6],  # 全学年
            'allowed_subjects': {
                'japanese': ['kanji', 'reading', 'grammar', 'writing'],
                'math': ['calculation', 'figure', 'measurement', 'graph'],
                'science': ['physics', 'chemistry', 'biology', 'earth_science'],
                'society': ['history', 'geography', 'civics', 'current_events', 'prefectures']
            }
        }
    ]

    with app.app_context():
        for user_data in users:
            # 既存ユーザーをチェック
            existing_user = User.query.filter_by(email=user_data['email']).first()
            if existing_user:
                print(f"User {user_data['email']} already exists")
                continue

            # 新しいユーザーを作成
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                is_admin=user_data['is_admin'],
                allowed_grades=user_data['allowed_grades'],
                allowed_subjects=user_data['allowed_subjects'],
                created_at=datetime.utcnow()
            )
            db.session.add(user)
            print(f"Created user: {user_data['email']}")

        try:
            db.session.commit()
            print("All test users created successfully")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating test users: {e}")

if __name__ == '__main__':
    create_test_users() 