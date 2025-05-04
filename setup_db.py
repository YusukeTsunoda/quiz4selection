from app import app, db

with app.app_context():
    # データベースの初期化
    db.create_all()
    print("データベーステーブルを作成しました") 