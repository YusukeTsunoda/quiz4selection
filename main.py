import logging
import sys
import os
from app import app, init_app

if __name__ == "__main__":
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)

    try:
        # アプリケーションの初期化
        with app.app_context():
            init_app()
            
        # サーバーの起動
        port = int(os.environ.get('PORT', 5003))
        logger.info(f"Starting Flask application on port {port}...")
        app.run(host="0.0.0.0", port=port, debug=True)
    except Exception as e:
        logger.error(f"Failed to start Flask application: {e}")
        sys.exit(1)
