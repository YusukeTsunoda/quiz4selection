import os
import socket
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 環境変数の読み込み
load_dotenv()

def analyze_db_url(db_url):
    """接続文字列の解析とデバッグ"""
    try:
        if not db_url:
            logger.error("Database URL is None")
            return

        # 機密情報をマスク
        masked_url = db_url.replace(
            db_url.split('@')[0], '***:***'
        ) if '@' in db_url else db_url
        logger.info(f"Analyzing Database URL: {masked_url}")

        # URLの各部分を解析
        parsed = urlparse(db_url)
        logger.info(f"Scheme: {parsed.scheme}")
        logger.info(f"Host: {parsed.hostname}")
        logger.info(f"Port: {parsed.port}")
        logger.info(f"Path: {parsed.path}")
        logger.info(f"Query params: {parsed.query}")

    except Exception as e:
        logger.error(f"Error analyzing database URL: {e}")

def update_db_url_params(db_url):
    """データベースURLのクエリパラメータを安全に更新"""
    if not db_url:
        return db_url
        
    try:
        # URLをパース
        parsed = urlparse(db_url)
        # 既存のクエリパラメータを取得
        params = parse_qs(parsed.query)
        
        # sslmodeパラメータを追加/更新
        params['sslmode'] = ['require']
        
        # 新しいクエリ文字列を作成
        new_query = urlencode(params, doseq=True)
        
        # URLを再構築
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
    except Exception as e:
        logger.error(f"Error updating database URL parameters: {e}")
        return db_url

class Config:
    """アプリケーション設定クラス"""
    def __init__(self):
        self.FLASK_ENV = 'production' if os.getenv('VERCEL') else os.getenv('FLASK_ENV', 'development')
        
        if self.FLASK_ENV == 'development':
            db_url = os.getenv('LOCAL_DATABASE_URL')
        else:
            # 本番環境用の接続文字列を取得
            db_url = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
            if db_url:
                # クエリパラメータを安全に更新
                db_url = update_db_url_params(db_url)
        
        # 接続文字列の解析
        analyze_db_url(db_url)
        self.SQLALCHEMY_DATABASE_URI = db_url
        
        self.SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }
        
        # SSL設定はすでにURLに含まれているため、connect_argsからは削除
        if self.FLASK_ENV != 'development':
            self.SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {}
        
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
