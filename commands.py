import click
from flask.cli import with_appcontext
from models import db, User, QuizAttempt, QuestionHistory
from config import supabase
import json

INITIAL_ADMIN_EMAIL = "tsunotsunoda@gmail.com"  # 初期管理者のメールアドレス

@click.command('init-admin')
@with_appcontext
def init_admin_command():
    """初期管理者を設定するコマンド"""
    try:
        # 初期管理者のユーザーを検索
        user = User.get_by_email(INITIAL_ADMIN_EMAIL)
        if not user:
            click.echo(f'エラー: 初期管理者ユーザー {INITIAL_ADMIN_EMAIL} が見つかりません', err=True)
            click.echo('先にユーザー登録を行ってください')
            return
            
        # 管理者に設定
        if user.promote_to_admin():
            click.echo(f'初期管理者を設定しました: {INITIAL_ADMIN_EMAIL}')
        else:
            click.echo(f'ユーザー {INITIAL_ADMIN_EMAIL} は既に管理者です')
        
    except Exception as e:
        click.echo(f'エラー: {str(e)}', err=True)

@click.command('promote-admin')
@click.argument('email')
@click.argument('admin_email')
@click.argument('admin_password')
@with_appcontext
def promote_admin_command(email, admin_email, admin_password):
    """既存のユーザーを管理者に昇格させるコマンド（管理者権限が必要）"""
    try:
        # 管理者の認証
        try:
            response = supabase.auth.sign_in_with_password({
                "email": admin_email,
                "password": admin_password
            })
            admin_user = User.get_by_email(admin_email)
            if not admin_user or not admin_user.is_admin:
                click.echo('エラー: 管理者権限がありません', err=True)
                return
        except Exception:
            click.echo('エラー: 管理者認証に失敗しました', err=True)
            return

        # 昇格対象ユーザーを検索
        user = User.get_by_email(email)
        if not user:
            click.echo(f'エラー: ユーザー {email} が見つかりません', err=True)
            return
            
        # 既に管理者の場合
        if user.is_admin:
            click.echo(f'ユーザー {email} は既に管理者です')
            return
            
        # 管理者に昇格
        if user.promote_to_admin():
            click.echo(f'ユーザー {email} を管理者に昇格させました')
        
    except Exception as e:
        click.echo(f'エラー: {str(e)}', err=True)
        
def init_app(app):
    """アプリケーションにコマンドを登録"""
    app.cli.add_command(init_admin_command)
    app.cli.add_command(promote_admin_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(migrate_question_history)

@click.command('create-admin')
@click.argument('email')
@click.argument('username')
@with_appcontext
def create_admin_command(email, username):
    """管理者ユーザーを作成するコマンド"""
    try:
        # メールアドレスの重複チェック
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if existing_user.is_admin:
                click.echo(f'ユーザー {email} は既に管理者です。')
                return
            else:
                # 既存ユーザーを管理者に昇格
                existing_user.is_admin = True
                db.session.commit()
                click.echo(f'既存ユーザー {email} を管理者に昇格させました。')
                return

        # 新しい管理者ユーザーを作成
        user = User(
            id=f'dev-admin-{username}',  # 開発環境用のID
            email=email,
            username=username,
            is_admin=True
        )
        db.session.add(user)
        db.session.commit()
        click.echo(f'管理者ユーザー {email} を作成しました。')

    except Exception as e:
        click.echo(f'エラーが発生しました: {str(e)}')
        db.session.rollback() 

@click.command('migrate-question-history')
@with_appcontext
def migrate_question_history():
    """既存のQuizAttemptから問題履歴を移行"""
    try:
        quiz_attempts = QuizAttempt.query.all()
        migrated_count = 0
        
        for attempt in quiz_attempts:
            try:
                # quiz_historyがJSON文字列の場合はパース
                if isinstance(attempt.quiz_history, str):
                    history_data = json.loads(attempt.quiz_history)
                else:
                    history_data = attempt.quiz_history
                
                # 各問題の履歴を処理
                for question_data in history_data:
                    question_text = question_data.get('question')
                    is_correct = question_data.get('is_correct')
                    
                    # 既存の履歴を検索または新規作成
                    history = QuestionHistory.query.filter_by(
                        user_id=attempt.user_id,
                        question_text=question_text
                    ).first()
                    
                    if not history:
                        history = QuestionHistory(
                            user_id=attempt.user_id,
                            grade=attempt.grade,
                            category=attempt.category,
                            subcategory=attempt.subcategory,
                            difficulty=attempt.difficulty,
                            question_text=question_text,
                            correct_count=1 if is_correct else 0,
                            attempt_count=1,
                            last_attempted_at=attempt.timestamp
                        )
                    else:
                        history.attempt_count += 1
                        if is_correct:
                            history.correct_count += 1
                        if attempt.timestamp > history.last_attempted_at:
                            history.last_attempted_at = attempt.timestamp
                    
                    db.session.add(history)
                    migrated_count += 1
                
                if migrated_count % 100 == 0:  # 100件ごとにコミット
                    db.session.commit()
                    print(f'Migrated {migrated_count} records')
            
            except Exception as e:
                print(f'Error processing attempt {attempt.id}: {e}')
                continue
        
        db.session.commit()
        print(f'Successfully migrated {migrated_count} question history records')
        
    except Exception as e:
        print(f'Migration failed: {e}')
        db.session.rollback() 