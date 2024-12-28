import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/quiz_app?sslmode=disable'
    SQLALCHEMY_TRACK_MODIFICATIONS = False