import logging
import sys
import os
from app import app, init_app

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if __name__ == "__main__":
    # アプリケーションの初期化
    with app.app_context():
        init_app()
    
    # ポート番号の設定
    port = int(os.environ.get('PORT', 5004))
    logger.info(f'Starting Flask application on port {port}...')
    
    # アプリケーションの起動
    app.run(host='0.0.0.0', port=port, debug=True)
