from app import app, db

<<<<<<< HEAD
def reset_database():
    with app.app_context():
        # 全てのテーブルを削除
        db.drop_all()
        # 全てのテーブルを作成
        db.create_all()
        print("Database has been reset successfully!")

if __name__ == "__main__":
    reset_database() 
=======
with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database reset completed successfully.") 
>>>>>>> ca349853c6a96ebe070137e810353321b3bdbb5c
