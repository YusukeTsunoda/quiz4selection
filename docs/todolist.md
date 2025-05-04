## Quiz4selection アプリ改善 ToDoリストと詳細手順

以下に、提案された改善点に基づいたToDoリストと、各タスクを実行するための詳細な手順を示します。

### ToDoリスト

| カテゴリ                   | タスク                                                              | 優先度 | 担当   | ステータス |
| :------------------------- | :------------------------------------------------------------------ | :----- | :----- | :--------- |
| **アプリ開発エキスパート** |                                                                     |        |        |            |
|                            | **1. データベース構成と設定管理**                                       | 高     | 開発者 | 未着手     |
|                            | **2. Supabaseクライアントの実装**                                       | 高     | 開発者 | 未着手     |
|                            | **3. テストコードの導入と拡充**                                         | 中     | 開発者 | 未着手     |
|                            | **4. エラーハンドリングとロギングの強化**                               | 高     | 開発者 | 未着手     |
|                            | **5. コードのモジュール化 (Blueprints導入)**                          | 低     | 開発者 | 未着手     |
|                            | **6. クイズデータ読み込み戦略の見直しとJSONフォーマット統一**             | 中     | 開発者 | 未着手     |
|                            | **7. 依存関係管理の統一**                                             | 中     | 開発者 | 未着手     |
| **マーケティングエキスパート** |                                                                     |        |        |            |
|                            | **8. UI/UXの改善**                                                  | 中     | 両方   | 未着手     |
|                            | **9. ゲーミフィケーション導入**                                       | 中     | 両方   | 未着手     |
|                            | **10. コンテンツ（クイズ問題）の拡充と品質向上**                      | 高     | 両方   | 未着手     |
|                            | **11. アプリ名の再検討と差別化**                                        | 低     | マーケター | 未着手     |
|                            | **12. 保護者向け機能の検討**                                          | 低     | 両方   | 未着手     |

---

### 詳細手順

#### 1. データベース構成と設定管理 (優先度: 高)

*   **目的:** 本番環境で安定稼働するデータベース構成を確立し、設定情報を安全かつ効率的に管理する。
*   **フェーズ:** 設計・実装

*   **ステップ 1.1: 本番用DBの選定と設定**
    *   **プロンプト例:** 「Supabase Postgresを本番データベースとして使用します。必要な接続情報を確認し、Vercelの環境変数に設定する方法を教えてください。」
    *   **修正内容:** SupabaseプロジェクトダッシュボードでDB接続URIを確認。Vercelプロジェクトの環境変数設定画面で `DATABASE_URL` として登録。
    *   **ゴール:** Vercel環境変数に本番DBの接続情報が安全に設定されている。

*   **ステップ 1.2: `config.py` の修正**
    *   **プロンプト例:** 「`config.py` を修正し、環境変数 `DATABASE_URL` を確実に読み込むようにしてください。デフォルトのSQLite設定は開発用であることを明記するか、コメントアウトしてください。」
    *   **修正内容:**
        ```python
        # config.py
        import os
        import logging
        from dotenv import load_dotenv

        load_dotenv()
        logger = logging.getLogger(__name__)

        # ... (is_development 関数など) ...

        class Config:
            def __init__(self):
                # 環境変数からDATABASE_URLを取得。なければ開発用のSQLiteをデフォルトに（要検討）
                self.SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
                if not self.SQLALCHEMY_DATABASE_URI:
                     # 開発環境でのみSQLiteを使う場合は is_development() で判定するなど
                     logger.warning("DATABASE_URL not set. Falling back to SQLite for development.")
                     self.SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/quiz.db'
                else:
                     # PostgreSQLの場合、Heroku等で 'postgres://' を 'postgresql://' に置換する必要がある場合がある
                     if self.SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
                         self.SQLALCHEMY_DATABASE_URI = self.SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
                     logger.info(f"Using database: {self.SQLALCHEMY_DATABASE_URI.split('@')[1] if '@' in self.SQLALCHEMY_DATABASE_URI else self.SQLALCHEMY_DATABASE_URI}") # パスワード等はログに出さない

                self.SQLALCHEMY_TRACK_MODIFICATIONS = False
                self.SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-fallback') # フォールバックも安全なものに
                if self.SECRET_KEY == 'dev-secret-key-fallback':
                    logger.warning("FLASK_SECRET_KEY is not set securely. Using fallback.")
                self.DEBUG = is_development()
                # ... (Supabase関連の設定は次のタスクで) ...
        ```
    *   **ゴール:** `config.py` が環境変数 `DATABASE_URL` を正しく読み込み、本番/開発で適切なDB URIが設定される。`SECRET_KEY` も環境変数から読み込まれる。

*   **ステップ 1.3: 開発環境の `.env` 設定**
    *   **プロンプト例:** 「ローカル開発用の `.env` ファイルに必要な環境変数（`DATABASE_URL` [SQLite or ローカルDB], `FLASK_SECRET_KEY`）を記述する例を示してください。`.gitignore` に `.env` が含まれているかも確認してください。」
    *   **修正内容:** プロジェクトルートに `.env` ファイルを作成（または確認）。
        ```dotenv
        # .env
        FLASK_SECRET_KEY='あなたの_非常に_安全な_開発用_シークレットキー'
        # 開発用DBがSQLiteの場合
        # DATABASE_URL='sqlite:///instance/quiz.db'
        # ローカルPostgreSQLの場合 (例)
        DATABASE_URL='postgresql://user:password@localhost:5432/quiz_dev_db'
        # Supabase関連 (次のタスクで設定)
        SUPABASE_URL='あなたの_Supabase_URL'
        SUPABASE_KEY='あなたの_Supabase_Anon_Key'
        IS_DEVELOPMENT='true'
        ```
        `.gitignore` に `.env` が含まれていることを確認。
    *   **ゴール:** ローカル開発に必要な環境変数が `.env` で管理され、Gitリポジトリに含まれない。

*   **ステップ 1.4: 本番DBへのマイグレーション適用**
    *   **プロンプト例:** 「Vercelデプロイプロセス（または手動デプロイ後）で、本番データベースに対してFlask-Migrateのマイグレーション (`flask db upgrade`) を実行する方法を教えてください。」
    *   **修正内容:** Vercelのビルドコマンドやデプロイ後のスクリプト、または一時的なSSH接続などで `flask db upgrade` を実行する手順を確認・設定。
    *   **ゴール:** 本番データベースに最新のスキーマが適用されている。

#### 2. Supabaseクライアントの実装 (優先度: 高)

*   **目的:** ダミークライアントを実際の `supabase-py` クライアントに置き換え、認証機能を有効化する。
*   **フェーズ:** 実装

*   **ステップ 2.1: `supabase-py` のインストール確認**
    *   **プロンプト例:** 「`requirements.txt` または `pyproject.toml` に `supabase-py` が正しく記載されているか確認してください。」
    *   **修正内容:** `requirements.txt` / `pyproject.toml` を確認。なければ追加 (`pip install supabase` または `uv add supabase`)。
    *   **ゴール:** 依存関係に `supabase-py` が含まれている。

*   **ステップ 2.2: `config.py` でのクライアント初期化**
    *   **プロンプト例:** 「`config.py` から `DummySupabaseClient` を削除し、環境変数 `SUPABASE_URL` と `SUPABASE_KEY` を使って `supabase-py` の `Client` を初期化するコードを追加してください。環境変数がない場合のエラーハンドリングも含めてください。」
    *   **修正内容:** `config.py` を修正（上記タスク1.2のコード例に統合済み）。`DummySupabaseClient` のクラス定義と `supabase = DummySupabaseClient()` の行を削除。実際の `create_client` を呼び出すコードを追加。
    *   **ゴール:** `config.py` で実際の Supabase クライアントが初期化され、アプリケーション全体から利用可能になる。環境変数未設定時にはエラーが発生する。

*   **ステップ 2.3: 環境変数の設定**
    *   **プロンプト例:** 「ローカル開発用の `.env` ファイルと、Vercelの環境変数設定に `SUPABASE_URL` と `SUPABASE_KEY` を設定する手順を説明してください。」
    *   **修正内容:**
        *   `.env` ファイルに Supabase プロジェクトの URL と Anon Key を追加。
        *   Vercel プロジェクトの環境変数設定画面で `SUPABASE_URL` と `SUPABASE_KEY` を設定。
    *   **ゴール:** ローカルおよび本番環境で Supabase の接続情報が環境変数経由で利用可能になる。

*   **ステップ 2.4: 認証関連コードの確認・修正**
    *   **プロンプト例:** 「`app.py` や関連する認証処理（サインアップ、ログイン、ログアウト、パスワードリセットなど）で、ダミークライアントのメソッド呼び出しを、実際の `supabase.auth.sign_up` や `supabase.auth.sign_in_with_password` などに置き換える必要があります。該当箇所を確認し、修正例を示してください。」
    *   **修正内容:** `app.py` 内の `/signup`, `/login`, `/logout`, `/reset-password` などのルート関数を確認し、`supabase.auth` の適切なメソッド呼び出しに修正する。エラーハンドリング（例: メールアドレス重複、パスワード間違い）も実装する。
    *   **ゴール:** アプリケーションの認証機能が Supabase Authentication を使って実際に動作する。

#### 3. テストコードの導入と拡充 (優先度: 中)

*   **目的:** アプリケーションの品質を担保し、リファクタリングや機能追加時のデグレードを防ぐ。
*   **フェーズ:** 実装・テスト

*   **ステップ 3.1: テストフレームワークの導入**
    *   **プロンプト例:** 「`pytest` と `pytest-flask` を使ってテスト環境をセットアップする手順を教えてください。必要なパッケージのインストール方法も示してください。」
    *   **修正内容:**
        *   `pip install pytest pytest-flask` または `uv add pytest pytest-flask --dev` を実行。
        *   プロジェクトルートに `tests/` ディレクトリを作成。
        *   `tests/conftest.py` を作成し、テスト用の `app` と `client` フィクスチャを定義。
        ```python
        # tests/conftest.py
        import pytest
        from app import app as flask_app # app.pyのFlaskインスタンス

        @pytest.fixture(scope='session')
        def app():
            """Session-wide test `Flask` application."""
            config_override = {
                "TESTING": True,
                # テスト用DB設定など
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", # インメモリDBを使用する例
                "WTF_CSRF_ENABLED": False, # フォームテストでCSRFを無効化
                "SECRET_KEY": "test-secret-key",
                # Supabaseのモック化などが必要な場合、ここで設定
            }
            flask_app.config.update(config_override)

            # ここでテスト用DBのセットアップなどを行う場合がある
            # with flask_app.app_context():
            #     db.create_all()

            yield flask_app

            # ここでテスト用DBのクリーンアップなどを行う場合がある
            # with flask_app.app_context():
            #     db.drop_all()


        @pytest.fixture()
        def client(app):
            """A test client for the app."""
            return app.test_client()

        @pytest.fixture()
        def runner(app):
            """A test runner for the app's Click commands."""
            return app.test_cli_runner()
        ```
    *   **ゴール:** `pytest` が実行可能になり、基本的なテストフィクスチャが準備されている。

*   **ステップ 3.2: 主要ルートのテスト作成**
    *   **プロンプト例:** 「`/`, `/grade_select`, `/login` などの主要なルートに対して、正常なレスポンスコード (200) が返ってくるか、特定のHTML要素が含まれているかを確認する `pytest` のテストコード例を作成してください。」
    *   **修正内容:** `tests/test_app.py` を作成し、テストケースを追加。
        ```python
        # tests/test_app.py
        def test_index_route(client):
            response = client.get('/')
            assert response.status_code == 302 # ログインしていない場合、ログインページへリダイレクトされる想定
            # またはログイン後のトップページをテスト
            # assert b'学年を選択' in response.data # 例

        def test_grade_select_route(client):
            # このルートにアクセスするにはログインが必要かもしれない
            # ログイン処理をモックするか、テストユーザーでログインする処理が必要
            # response = client.get('/grade_select')
            # assert response.status_code == 200
            # assert b'どの学年？' in response.data
            pass # 実装はログイン状態に依存

        def test_login_page(client):
            response = client.get('/login')
            assert response.status_code == 200
            assert b'ログイン' in response.data
        ```
    *   **ゴール:** 主要なページの表示確認テストが実装され、`pytest` で実行できる。

*   **ステップ 3.3: 認証機能のテスト作成**
    *   **プロンプト例:** 「サインアップ、ログイン、ログアウト機能のテストを作成したいです。テストユーザーの作成、ログイン成功/失敗、ログアウト後の状態を確認するテストコードの例を示してください。Supabaseの認証呼び出しはモック化する必要があるかもしれません。」
    *   **修正内容:** `tests/test_auth.py` を作成。`unittest.mock` を使って `supabase.auth` のメソッドをモック化し、テストケースを記述。
        ```python
        # tests/test_auth.py (一部抜粋、要unittest.mock)
        from unittest.mock import patch, MagicMock

        # @patch('app.supabase.auth') # app.py で supabase をインポートしている場合
        # def test_successful_login(mock_auth, client):
        #     # モックの設定: sign_in_with_password が成功時のレスポンスを返すように
        #     mock_session = MagicMock()
        #     mock_session.user = MagicMock(id='test-user-id')
        #     mock_auth.sign_in_with_password.return_value = MagicMock(session=mock_session)

        #     response = client.post('/login', data={'email': 'test@example.com', 'password': 'password'}, follow_redirects=True)
        #     assert response.status_code == 200
        #     assert b'ログアウト' in response.data # ログイン後ヘッダーが変わるなど
        #     # セッションにユーザーIDが格納されているか確認など
        #     with client.session_transaction() as sess:
        #         assert sess.get('user_id') is not None

        # def test_failed_login(mock_auth, client):
        #     # モックの設定: sign_in_with_password がエラーを発生させるように
        #     from gotrue.errors import AuthApiError
        #     mock_auth.sign_in_with_password.side_effect = AuthApiError("Invalid login credentials", status_code=400)

        #     response = client.post('/login', data={'email': 'wrong@example.com', 'password': 'wrong'}, follow_redirects=True)
        #     assert response.status_code == 200
        #     assert b'メールアドレスまたはパスワードが違います' in response.data # エラーメッセージ
        ```
    *   **ゴール:** 認証関連の主要なシナリオ（成功、失敗）がテストでカバーされている。

*   **ステップ 3.4: クイズロジックのテスト作成**
    *   **プロンプト例:** 「クイズの進行ロジック（問題表示、回答処理、スコア計算、結果表示）をテストしたいです。特定のクイズデータを使って、正解/不正解の場合のスコア変動や次の問題への遷移、最終結果が正しいかを確認するテストコードの例を示してください。」
    *   **修正内容:** `tests/test_quiz.py` を作成。テスト用のクイズデータを準備するかモックし、クイズ開始から終了までのセッションの流れをシミュレートするテストを記述。
    *   **ゴール:** クイズのコアロジックが正しく動作することがテストで確認できる。

*   **ステップ 3.5: (任意) CI連携**
    *   **プロンプト例:** 「GitHub Actionsを使って、リポジトリへのプッシュ時に自動で `pytest` を実行するワークフローファイルの例を作成してください。」
    *   **修正内容:** `.github/workflows/python-app.yml` を作成。
        ```yaml
        # .github/workflows/python-app.yml
        name: Python application test

        on: [push]

        jobs:
          build:
            runs-on: ubuntu-latest
            steps:
            - uses: actions/checkout@v4
            - name: Set up Python
              uses: actions/setup-python@v4
              with:
                python-version: '3.12' # プロジェクトで使用するバージョンに合わせる
            - name: Install dependencies
              run: |
                python -m pip install --upgrade pip
                # uvを使う場合
                pip install uv
                uv pip install -r requirements.txt # or uv pip install -p .[dev]
                # pipのみの場合
                # pip install -r requirements.txt
                # pip install pytest pytest-flask
            - name: Test with pytest
              run: |
                pytest
        ```
    *   **ゴール:** GitHubリポジトリへのプッシュをトリガーに、自動でテストが実行される。

#### 4. エラーハンドリングとロギングの強化 (優先度: 高)

*   **目的:** 予期せぬエラー発生時にユーザー体験を損なわず、開発者が問題を特定しやすくする。
*   **フェーズ:** 実装・テスト

*   **ステップ 4.1: グローバルエラーハンドラの実装**
    *   **プロンプト例:** 「Flaskで500エラー（サーバー内部エラー）と404エラー（Not Found）を捕捉し、それぞれ専用のエラーページ (`templates/500.html`, `templates/404.html`) を表示するエラーハンドラを `app.py` に実装してください。500エラー発生時にはエラー詳細をログに記録する処理も加えてください。」
    *   **修正内容:** `app.py` に `@app.errorhandler(500)` と `@app.errorhandler(404)` デコレータを使った関数を追加（上記タスク1.4のコード例参照）。`templates/500.html` と `templates/404.html` を作成。
    *   **ゴール:** 未捕捉の例外や存在しないURLへのアクセス時に、カスタムエラーページが表示され、500エラーの情報がログに出力される。

*   **ステップ 4.2: ファイルI/Oエラー処理**
    *   **プロンプト例:** 「クイズデータをJSONファイルから読み込む関数 (`quiz_data/loader.py` の `load_questions_from_file`) で、ファイルが存在しない場合 (`FileNotFoundError`) やJSONの形式が不正な場合 (`json.JSONDecodeError`) のエラーハンドリングを追加してください。エラー発生時はログに警告またはエラーを出力し、`None` または空リストを返すようにしてください。」
    *   **修正内容:** `quiz_data/loader.py` (または相当するファイル) のファイル読み込み部分を `try...except` で囲む。
        ```python
        # quiz_data/loader.py 内 load_questions_from_file 関数
        import logging
        logger = logging.getLogger(__name__)
        # ... (関数定義) ...
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # データ検証ロジック (任意)
                    data = json.load(f)
                    # Pydantic等での検証処理
                    return data
            except FileNotFoundError:
                logger.warning(f"Question file not found: {file_path}")
                return None
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON format in {file_path}: {e}")
                return None
            except Exception as e: # その他の予期せぬエラー
                logger.error(f"Error loading question file {file_path}: {e}", exc_info=True)
                return None
        ```
    *   **ゴール:** クイズデータファイルの読み込みエラーが発生してもアプリがクラッシュせず、適切なログが出力される。

*   **ステップ 4.3: データベースエラー処理**
    *   **プロンプト例:** 「Flask-SQLAlchemyを使ったデータベース操作（例: `db.session.add()`, `db.session.commit()`, `User.query.get()` など）を行う箇所で、`SQLAlchemyError` を捕捉する `try...except` ブロックを追加する例を示してください。エラー発生時は `db.session.rollback()` を呼び出し、エラーログを出力し、ユーザーにエラーメッセージを表示するかリダイレクトする処理を入れてください。」
    *   **修正内容:** `app.py` やモデル操作を行う箇所でDB操作を `try...except` で囲む。
        ```python
        # app.py 内のDB操作例
        from sqlalchemy.exc import SQLAlchemyError
        from flask import flash

        # ... logger, db の設定 ...

        @app.route('/some_db_operation', methods=['POST'])
        def some_db_op():
            try:
                # ... DB操作 ...
                new_data = SomeModel(...)
                db.session.add(new_data)
                db.session.commit()
                flash('データを保存しました', 'success')
                return redirect(url_for('...'))
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Database error: {e}", exc_info=True)
                flash('データベースエラーが発生しました。', 'danger')
                return redirect(url_for('...')) # エラー時のリダイレクト先
            except Exception as e: # その他のエラーも捕捉
                db.session.rollback()
                logger.error(f"Unexpected error during DB operation: {e}", exc_info=True)
                flash('予期せぬエラーが発生しました。', 'danger')
                return redirect(url_for('...'))
        ```
    *   **ゴール:** データベース関連のエラーが発生した場合に、トランザクションがロールバックされ、エラーが記録され、ユーザーにフィードバックが与えられる。

*   **ステップ 4.4: ロギング設定の確認と調整**
    *   **プロンプト例:** 「開発環境と本番環境で異なるロギングレベル（開発時はDEBUG、本番時はINFOやWARNING）を設定する方法を示してください。ログのフォーマット（タイムスタンプ、ログレベル、メッセージなどを含む）と出力先（コンソール、ファイル、またはVercelのログ機能）の設定方法も説明してください。」
    *   **修正内容:** アプリ初期化時 (`app.py` or `create_app`) にロギング設定を行う。
        ```python
        # app.py
        import logging
        from config import Config # Configクラスをインポート

        app = Flask(__name__)
        app.config.from_object(Config()) # 設定読み込み

        if not app.debug: # 本番環境 (DEBUG=False) の場合
            # VercelなどのPaaSは通常標準出力/エラー出力をログとして収集する
            # ファイルに出力したい場合は RotatingFileHandler などを使用
            logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
        else: # 開発環境 (DEBUG=True) の場合
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

        logger = logging.getLogger(__name__) # アプリケーションロガー取得

        # Werkzeugのログレベルも調整（必要に応じて）
        # logging.getLogger('werkzeug').setLevel(logging.INFO)

        # ... db, migrate, login_manager などの初期化 ...
        ```
    *   **ゴール:** 環境に応じて適切なレベル・フォーマット・出力先でログが出力される。

#### 5. コードのモジュール化 (Blueprints導入) (優先度: 低)

*   **目的:** アプリケーションのコードベースを機能ごとに分割し、可読性と保守性を向上させる。
*   **フェーズ:** リファクタリング

*   **ステップ 5.1: Blueprint構成の設計**
    *   **プロンプト例:** 「現在の `app.py` の内容を分析し、機能を分割するためのBlueprint構成案（例: `auth`, `quiz`, `dashboard`, `admin`）を提案してください。それぞれのBlueprintが担当するルートの概要も示してください。」
    *   **修正内容:** `app.py` のルート定義を確認し、関連する機能をグループ化する設計を行う（コード修正なし、設計ドキュメント作成）。
    *   **ゴール:** アプリケーションの機能分割方針が決定している。

*   **ステップ 5.2: Blueprintファイルの作成とルート移動**
    *   **プロンプト例:** 「設計した `quiz` Blueprint を作成する手順を示してください。`myapp/quiz/` ディレクトリを作成し、`routes.py` に `Blueprint` オブジェクトを定義し、`app.py` からクイズ関連のルート定義（例: `/grade_select`, `/category_select` など）と関連インポートを移動するコード例を生成してください。」
    *   **修正内容:**
        *   `myapp/quiz/` ディレクトリ作成。
        *   `myapp/quiz/routes.py` を作成し、`Blueprint` を定義。
        *   `app.py` からクイズ関連のルート関数、ヘルパー関数、インポート文を `myapp/quiz/routes.py` に移動。`@app.route` を `@quiz_bp.route` に変更。
    *   **ゴール:** `quiz` 機能に関するルートとロジックが `myapp/quiz/routes.py` に分離されている。

*   **ステップ 5.3: Blueprintの登録**
    *   **プロンプト例:** 「`app.py` (または `create_app` ファクトリ) で、作成した `quiz_bp` Blueprint をアプリケーションに登録するコードを追加してください。必要であれば `url_prefix` を設定する方法も示してください。」
    *   **修正内容:** `app.py` に `from myapp.quiz.routes import quiz_bp` を追加し、`app.register_blueprint(quiz_bp)` を呼び出す。
    *   **ゴール:** Blueprint が Flask アプリケーションに登録され、分離したルートが機能する。

*   **ステップ 5.4: 他の機能のBlueprint化 (繰り返し)**
    *   **プロンプト例:** 「同様の手順で、`auth` Blueprint を作成し、認証関連のルート（`/login`, `/signup`, `/logout` など）を移動・登録する手順を示してください。」
    *   **修正内容:** ステップ5.2, 5.3 を `auth`, `dashboard` など他の機能グループについても繰り返す。
    *   **ゴール:** アプリケーションの主要機能が Blueprint ごとに整理されている。

#### 6. クイズデータ読み込み戦略の見直しとJSONフォーマット統一 (優先度: 中)

*   **目的:** アプリケーションの起動時間とメモリ使用量を改善し、データの一貫性を保つ。
*   **フェーズ:** 実装・コンテンツ作成

*   **ステップ 6.1: 遅延読み込み関数の実装**
    *   **プロンプト例:** 「`quiz_data` ディレクトリ内のJSONファイルを、必要になったタイミングで個別に読み込むためのヘルパー関数 `get_questions(grade, category, subcategory, difficulty)` を作成してください。ファイルパスを動的に生成し、JSONを読み込んで返すようにしてください。ファイルが存在しない場合の処理も含めてください。」
    *   **修正内容:** `quiz_data/loader.py` (または適切な場所) に `get_questions_path` と `get_questions` 関数を実装 (上記タスク4.2のコード例参照)。`quiz_data/__init__.py` の一括読み込み処理を削除またはコメントアウト。
    *   **ゴール:** 指定されたパラメータに基づいて対応するJSONファイルのみを読み込む関数が利用可能。

*   **ステップ 6.2: Flask-Cachingの導入と適用**
    *   **プロンプト例:** 「Flask-Cachingをセットアップし、`get_questions` 関数のファイル読み込み結果をキャッシュする手順を教えてください。`app.py` での初期化と、`@cache.memoize()` デコレータの適用方法を示してください。」
    *   **修正内容:**
        *   `pip install Flask-Caching` または `uv add Flask-Caching`。
        *   `extensions.py` に `cache = Cache()` を追加。
        *   `app.py` で `cache.init_app(app, config={'CACHE_TYPE': 'SimpleCache'})` のように初期化 (キャッシュタイプは要件に応じて変更、例: `FileSystemCache`, `RedisCache`)。
        *   `quiz_data/loader.py` の `load_questions_from_file` 関数に `@cache.memoize(timeout=...)` デコレータを追加 (上記タスク4.2のコード例に統合可能)。
    *   **ゴール:** 一度読み込んだJSONデータがキャッシュされ、次回以降のアクセスが高速化される。

*   **ステップ 6.3: アプリケーションコードでの利用**
    *   **プロンプト例:** 「クイズを開始するルート関数で、以前の一括読み込みデータ `questions_by_category` を参照していた部分を、新しい `get_questions` ヘルパー関数呼び出しに置き換える修正例を示してください。」
    *   **修正内容:** `app.py` (または `quiz` Blueprint のルート) 内の、クイズ問題リストを取得する箇所を修正。
        ```python
        # app.py or quiz/routes.py
        from quiz_data.loader import get_questions # 新しい関数をインポート

        @quiz_bp.route('/start_quiz/<int:grade>/<category>/<subcategory>/<difficulty>')
        # @login_required など
        def start_quiz(grade, category, subcategory, difficulty):
            questions = get_questions(grade, category, subcategory, difficulty)
            if questions is None or not questions:
                flash('クイズが見つかりませんでした。', 'warning')
                return redirect(url_for('quiz.select_difficulty', ...)) # 適切なリダイレクト先

            # セッションにクイズ情報を保存
            session['questions'] = questions
            session['current_question'] = 0
            session['score'] = 0
            # ... 他のセッション情報 ...
            return redirect(url_for('quiz.show_question'))
        ```
    *   **ゴール:** アプリケーションが遅延読み込みとキャッシュを利用してクイズデータを取得するようになる。

*   **ステップ 6.4: JSONデータフォーマットの統一**
    *   **プロンプト例:** 「`quiz_data` ディレクトリ内の全ての `questions.json` ファイルを確認し、キー名 (`question`, `options`, `correct_index`, `explanation`, `hint` など) を統一する作業が必要です。統一すべきキー名のリストを提案してください。また、修正作業を効率化するためのスクリプトのアイデアはありますか？」
    *   **修正内容:**
        *   統一するキー名を決定 (例: `question`, `options` [リスト], `correct_index` [数値, 0始まり], `explanation` [文字列], `hint` [文字列, 任意])。
        *   全 `questions.json` ファイルを手動またはスクリプトで修正。
        *   (スクリプト例案) Pythonスクリプトで `quiz_data` 以下を再帰的に探索し、各JSONを読み込み、キー名を置換して上書き保存する。古いキー名と新しいキー名のマッピング辞書を用意する。
    *   **ゴール:** 全てのクイズデータJSONが統一されたフォーマットになっている。

*   **ステップ 6.5: (任意) データ検証の導入**
    *   **プロンプト例:** 「Pydanticを使って、JSONファイルから読み込んだクイズデータの構造（必須キーの存在、データ型）を検証するモデルと、`load_questions_from_file` 関数での検証コード例を示してください。」
    *   **修正内容:**
        *   `pip install pydantic` or `uv add pydantic`.
        *   クイズデータのPydanticモデルを定義。
        ```python
        # quiz_data/models.py (新規作成)
        from pydantic import BaseModel, Field, validator
        from typing import List, Optional

        class QuestionModel(BaseModel):
            question: str
            options: List[str] = Field(..., min_items=2) # 最低2つの選択肢
            correct_index: int
            explanation: str
            hint: Optional[str] = None # ヒントは任意

            @validator('correct_index')
            def check_correct_index(cls, v, values):
                if 'options' in values and not (0 <= v < len(values['options'])):
                    raise ValueError('correct_index must be within the range of options')
                return v
        ```
        *   `load_questions_from_file` 関数内で読み込んだデータをモデルでパースして検証。
        ```python
        # quiz_data/loader.py 内 load_questions_from_file 関数
        from .models import QuestionModel # Pydanticモデルをインポート
        from pydantic import ValidationError
        # ...
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                # Pydanticで検証
                validated_data = [QuestionModel.parse_obj(q) for q in raw_data]
                return [q.dict() for q in validated_data] # 必要ならdictに戻す
            except ValidationError as e:
                logger.error(f"Data validation failed for {file_path}: {e}")
                return None
            # ... 他のexcept節 ...
        ```
    *   **ゴール:** 不正なフォーマットのJSONデータが読み込まれた場合にエラーが検知され、ログに記録される。

#### 7. 依存関係管理の統一 (優先度: 中)

*   **目的:** 依存関係の管理方法を統一し、環境構築の再現性を高める。
*   **フェーズ:** 環境整備

*   **ステップ 7.1: `pyproject.toml` への集約**
    *   **プロンプト例:** 「現在 `requirements.txt` に記載されている依存関係で、`pyproject.toml` の `[project.dependencies]` に記載されていないものがあれば、`pyproject.toml` に追加してください。開発時のみ必要なパッケージ（例: `pytest`）は `[project.optional-dependencies]` の `dev` などに記述してください。」
    *   **修正内容:** `requirements.txt` と `pyproject.toml` を比較し、`pyproject.toml` に不足している依存関係を追加。テスト関連などは `[project.optional-dependencies.dev]` に記述。
        ```toml
        # pyproject.toml
        [project]
        # ...
        dependencies = [
            "flask>=2.2.5,<3", # バージョン指定方法の統一
            "Werkzeug>=2.2.3,<3",
            "flask-migrate>=4.0.4,<5",
            "python-dotenv>=1.0.0,<2",
            "flask-login>=0.6.2,<1",
            "Flask-SQLAlchemy>=3.0.2,<4",
            "SQLAlchemy>=1.4.46,<2", # SQLAlchemy 2.0系への移行も検討
            "flask-caching>=2.0.2,<3",
            "dnspython>=2.0.0,<3", # バージョン指定の検討
            "supabase>=2.0.3,<3",
            "psycopg2-binary>=2.9.0", # DBドライバ
            "email-validator>=2.0.0", # 必要なら
            "pydantic>=1.10.0", # 任意
            # 他に必要なもの
        ]

        [project.optional-dependencies]
        dev = [
            "pytest",
            "pytest-flask",
            # 他の開発用ツール (例: black, flake8)
        ]
        # ...
        ```
    *   **ゴール:** 全ての依存関係が `pyproject.toml` に集約されている。

*   **ステップ 7.2: `uv.lock` の更新**
    *   **プロンプト例:** 「`pyproject.toml` を更新した後、`uv lock` コマンドを実行して `uv.lock` ファイルを最新の状態にする手順を教えてください。」
    *   **修正内容:** ターミナルで `uv lock` を実行。
    *   **ゴール:** `uv.lock` が `pyproject.toml` の内容に基づいて更新され、依存関係のバージョンが固定される。

*   **ステップ 7.3: `requirements.txt` の扱い**
    *   **プロンプト例:** 「依存関係を `pyproject.toml` に集約した場合、`requirements.txt` はどのように扱うべきですか？削除するべきか、`uv lock` コマンドで生成し直すべきか、ユースケースに応じて説明してください。」
    *   **修正内容:**
        *   Vercel などが `requirements.txt` を直接参照する場合は、`uv lock -o requirements.txt` で生成し、コミットする。
        *   `uv` を使ったデプロイプロセスが確立している場合は、`requirements.txt` は不要なため削除する。
    *   **ゴール:** 依存関係ファイルの整合性が取れ、不要なファイルが削除されるか、必要なファイルが正しく生成される。

---

(マーケティングエキスパート指摘分のToDo詳細手順は、文字数制限のため別コメントで記述します)