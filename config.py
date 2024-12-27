import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # データベース設定
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    if DATABASE_URL.startswith('postgres://postgres:WV1fxjSD4aznmIYj@db.cujvnutaucgrhleclmpq.supabase.co:5432/postgres'):
        DATABASE_URL = DATABASE_URL.replace('postgres://postgres:WV1fxjSD4aznmIYj@db.cujvnutaucgrhleclmpq.supabase.co:5432/postgres', 'postgresql://postgres:WV1fxjSD4aznmIYj@db.cujvnutaucgrhleclmpq.supabase.co:5432/postgres', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # セキュリティ設定
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev_key_for_quiz_app')