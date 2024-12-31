from app import app, db

def reset_database():
    with app.app_context():
        # 全てのテーブルを削除
        db.drop_all()
        # 全てのテーブルを作成
        db.create_all()
        print("Database has been reset successfully!")

if __name__ == "__main__":
    reset_database() 