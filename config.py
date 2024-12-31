import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


# Supabase設定
SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev_key_for_quiz_app')
    if os.getenv('FLASK_ENV') == 'development':
        SQLALCHEMY_DATABASE_URI = os.getenv('LOCAL_DATABASE_URL')
    else:
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def init_app(app):
        pass
