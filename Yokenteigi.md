# 多肢選択式クイズアプリケーション要件定義書

## 1. システム概要

### 1.1 目的
- ユーザーが様々なカテゴリーと難易度でクイズに挑戦できる
- 学習進捗を追跡・確認できる
- クイズの履歴を確認し、復習できる
- 苦手分野を特定し、効率的な学習を支援する

### 1.2 主要機能

#### クイズ実施機能
- 学年選択（1-6年）
- カテゴリー選択（国語、算数、理科、社会）
- サブカテゴリー選択（カテゴリー別の詳細分野）
- 難易度選択（easy, medium, hard）
- 問題の優先順位付け出題
  - 未回答の問題を優先
  - 低正答率の問題を次に優先
  - その他の問題を最後に出題
- 選択肢のランダム表示
- 即時採点・フィードバック

#### 進捗管理機能
- カテゴリー別の進捗表示
- サブカテゴリー別の進捗表示
- 難易度別の統計情報
  - 受験回数
  - 平均スコア
  - 最高スコア
- 問題ごとの正答率表示

#### 履歴確認機能
- カテゴリー・難易度別の履歴表示
- 各問題の詳細表示
  - 問題文
  - 選択した回答
  - 正解
  - 正誤判定
  - 解説
- 問題ごとの正答率履歴

---

## 2. データベース設計

### 2.1 テーブル構成

#### クイズ履歴（QuizAttempt）
- **ID**（主キー）
- **ユーザーID**（外部キー）
- **学年**
- **カテゴリー**
- **サブカテゴリー**
- **難易度**
- **スコア**
- **総問題数**
- **問題履歴**（JSON）
- **タイムスタンプ**

#### ユーザー（User）
- **ID**（主キー）
- **ユーザー名**
- **メールアドレス**
- **パスワードハッシュ**
- **学年**
- **作成日時**
- **更新日時**

---

## 3. 画面設計

### 3.1 画面一覧

#### 学年選択画面
- 学年一覧表示（1-6年）
- ダッシュボードへのリンク

#### カテゴリー選択画面
- カテゴリー一覧表示
- 選択中の学年表示
- ダッシュボードへのリンク

#### サブカテゴリー選択画面
- サブカテゴリー一覧表示
- 選択中の学年とカテゴリーの表示
- カテゴリー選択への戻るリンク

#### 難易度選択画面
- 難易度一覧表示
- 選択中の学年、カテゴリー、サブカテゴリーの表示
- 各難易度の説明
- サブカテゴリー選択への戻るリンク
- 統計情報の表示

#### クイズ画面
- 進捗バー
- 現在のスコア
- 問題文
- 選択肢（ランダム表示）
- 問題番号
- タイマー（オプション）

#### 結果画面
- 最終スコア
- 不正解問題の復習セクション
  - 問題文
  - 選択した回答
  - 正解
  - 解説
- 再チャレンジボタン
- ダッシュボードへのリンク

#### ダッシュボード
- 学年別進捗
- カテゴリー別進捗
- サブカテゴリー別進捗
- 難易度別統計
- 詳細履歴へのリンク
- 問題ごとの正答率グラフ

#### クイズ履歴画面
- 実施日時
- 学年
- カテゴリー
- サブカテゴリー
- 難易度
- スコア
- 各問題の詳細
  - 問題文
  - 選択した回答
  - 正解
  - 解説
  - 正答率

---

## 4. 非機能要件

### 4.1 性能要件
- ページ遷移：**1秒以内**
- クイズ採点：**即時（1秒以内）**
- データベース応答：**2秒以内**
- 問題データのキャッシュ：**5分**

### 4.2 セキュリティ要件
- **SQLインジェクション対策**
- **XSS対策**
- **CSRF対策**
- **セッション管理**
- **入力値のサニタイズ**

### 4.3 UI/UX要件
- **レスポンシブデザイン**
- **直感的な操作性**
- **アニメーションによる視覚的フィードバック**
- **エラー時の適切なメッセージ表示**
- **ローディング表示**

---

## 5. 使用技術

### 5.1 バックエンド
- **Python（Flask 2.2.5）**
- **PostgreSQL 16**
- **SQLAlchemy 1.4.46**
- **Flask-SQLAlchemy 2.5.1**
- **Flask-Migrate 4.0.4**
- **Flask-Login 0.6.2**
- **Werkzeug 2.2.3**

### 5.2 フロントエンド
- **HTML/CSS**
- **JavaScript**
- **Bootstrap 5**
- **Chart.js**（統計グラフ表示用）

### 5.3 開発環境
- **Replit**
- **Git（バージョン管理）**
- **python-dotenv 1.0.0**（環境変数管理）

---

## 6. プロジェクトの全体構成

以下のファイルがプロジェクトに含まれています：

- **`app.py`**  
  Flaskアプリケーションのメインファイル。ルーティング、ビュー関数、クイズロジック、セッション管理を含む。

- **`models.py`**  
  SQLAlchemyモデルの定義。ユーザーモデル、クイズ履歴モデル、スコア計算ロジックを含む。

- **`extensions.py`**  
  Flaskの拡張機能の初期化。データベース設定、マイグレーション管理を含む。

- **`quiz_data.py`**  
  クイズデータの管理。問題の取得、優先順位付け、統計計算を含む。

- **`config.py`**  
  環境変数、データベース設定、セキュリティ設定の管理。

- **`templates/`**  
  - base.html（ベーステンプレート）
  - grade_select.html（学年選択）
  - category_select.html（カテゴリー選択）
  - subcategory_select.html（サブカテゴリー選択）
  - difficulty_select.html（難易度選択）
  - quiz.html（クイズ画面）
  - result.html（結果画面）
  - dashboard.html（ダッシュボード）

- **`quiz_data/`**  
  学年別・カテゴリー別の問題データJSONファイル



# ローカル環境でFlaskアプリケーションを実行するための手順

## 必要なソフトウェア
---

## パッケージのインストール
1. 以下のコマンドで必要なパッケージをインストールします：

```bash
pip install flask flask-login flask-sqlalchemy psycopg2-binary sqlalchemy flask-migrate email-validator
```

2. .envファイルを作成します。
3. .envファイルを読み込めるようにします。

```bash
pip install python-dotenv
```

```app.pyファイルの先頭に以下のコードを追加
from dotenv import load_dotenv
load_dotenv()
```
---

## データベースのセットアップ

### データベース構造
このアプリケーションには以下の2つのテーブルが必要です：
- **users テーブル**：ユーザー情報を保存
- **quiz_attempts テーブル**：クイズの履歴を保存

### データベーススキーマの作成手順
1. まず、PostgreSQLデータベースを作成します。

```bash
psql -U postgres -p <password>
```
<password> : Tsuno202412
そして以下のSQLを実行：

```sql
CREATE TABLE users ( 
    id SERIAL PRIMARY KEY, 
    username VARCHAR(64) UNIQUE NOT NULL, 
    email VARCHAR(120) UNIQUE NOT NULL, 
    password_hash VARCHAR(256), 
    high_score INTEGER DEFAULT 0 
); 

CREATE TABLE quiz_attempts ( 
    id SERIAL PRIMARY KEY, 
    user_id INTEGER REFERENCES users(id), 
    category VARCHAR(50) NOT NULL, 
    difficulty VARCHAR(20) NOT NULL, 
    score INTEGER NOT NULL, 
    questions_history JSONB NOT NULL, 
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP 
);
```

### スキーマの確認方法
1. テーブル一覧の確認：

```bash
\dt
```

2. テーブル構造の確認：

```bash
\d users
\d quiz_attempts
```

3. データベースを終了します。
```bash
\q
```

### 環境変数の設定
以下の環境変数が設定されていることを確認：
- **DATABASE_URL**：自動的に設定されています
- **FLASK_SECRET_KEY**：セッション管理用の秘密鍵
これらの設定が完了すれば、アプリケーションはデータベースと正常に接続できるようになります。

### データベースのマイグレーション

```bash
flask db init
flask db migrate
flask db upgrade
```

FLASK_SECRET_KEYの設定:
任意の文字列を環境変数として設定する必要があります。

アプリケーションの起動:

python main.py
アプリケーションは http://localhost:5000 で起動します。


SQLALCHEMY_DATABASE_URI
DATABASE_URL
FLASK_SECRET_KEY
dev_key_for_quiz_app

注意点:
全てのファイルを同じディレクトリ構造で保存してください
static/とtemplates/のディレクトリ構造は維持してください
DATABASE_URLとFLASK_SECRET_KEYの環境変数を適切に設定してください
PostgreSQLの認証情報は環境に合わせて調整してください
もし環境変数の設定が難しい場合は、Replitの環境で実行することをお勧めします。Replitではこれらの設定が簡単に行えます。



# クイズ履歴ページに、各回の５問の回答結果とは別に、各問題のみにフォーカスして、複数回回答してた場合、問題文と正しい答に対して、回答した時間と選択した選択肢の内容、あっていた場合は緑、まちがっていた場合は赤で表示するようにしたい


具体的な実装の流れ：
1. models.py:
問題単位で履歴を集計するメソッドを追加
問題ごとの正答率を計算するメソッドを追加
app.py:
問題単位の履歴を取得するルートを追加
問題ごとの正答率を計算して返すロジックを追加
quiz_history.html:
タブ形式で「試行単位」と「問題単位」の表示を切り替えられるように修正
問題単位のビューを追加
各問題に対する時系列での回答履歴を表示
正解/不正解を色分けして表示
style.css:
タブ切り替えのスタイルを追加
問題単位の履歴表示用のスタイルを追加
時系列表示のためのスタイルを追加
この修正により、ユーザーは従来の試行単位での履歴表示と、問題単位での履歴表示を切り替えて確認できるようになります。問題単位の表示では、同じ問題に対する複数回の回答履歴を時系列で確認でき、各回答の正誤が色分けで一目で分かるようになります。

必要な修正について説明します：
models.pyの修正:
models.py:
  content: |-
    データベースモデルの定義
    機能:
    - クイズ履歴モデル
    - ユーザーモデル
    - 問題履歴の保存
    - スコア計算ロジック
    + 問題単位の履歴集計機能
    + 問題ごとの正答率計算

quiz_history.html:
  content: |-
    クイズ履歴ページ
    機能:
    - 過去の成績表示
    - 各問題の詳細表示
    - 正解・不正解の色分け表示
    - 選択した回答と正解の表示
    - タイムスタンプ表示
    - ダッシュボードへの戻るリンク
    + 問題単位の履歴タブ表示
    + 問題ごとの回答履歴一覧
    + 問題ごとの正答率表示
    + 時系列での回答履歴表示

style.css:
  content: |-
    アプリケーションのスタイル定義
    機能:
    - レイアウト
    - カラースキーム
    - レスポンシブデザイン
    - アニメーション効果
    - 正解/不正解の色分け
    - クイズ履歴のスタイリング
    + 問題単位の履歴表示スタイル
    + タブ切り替えのスタイル
    + 時系列表示のスタイル

app.py:
  content: |-
    Flaskアプリケーションのメインファイル
    機能:
    - ルーティング設定
    - アプリケーション初期化
    - ビュー関数の定義
    - セッション管理
    - クイズロジックの実装
    + 問題単位の履歴データ取得処理
    + 問題ごとの正答率計算処理

    supabaseとの連携
    Password: WV1fxjSD4aznmIYj



    # データベース設定
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "connect_args": {
            "sslmode": "require"
        }
    }
    
    # セキュリティ設定
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev_key_for_quiz_app')


    # 開発時の主な課題と解決策

    ## 1. データベース接続の問題
    ### 課題
    - Supabaseへの接続が不安定
    - DATABASE_URLの形式が正しく認識されない
    - SSL証明書関連のエラー

    ### 解決策
    - DATABASE_URLの'postgres://'を'postgresql://'に置換
    - SSL設定を明示的に指定
    ```python
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"sslmode": "require"}
    }
    ```

    ## 2. セッション管理の問題
    ### 課題
    - セッションデータの不整合
    - クイズ途中でのセッション切れ
    - 複数タブでの競合

    ### 解決策
    - セッションキーの明確な定義
    - セッション有効期限の適切な設定
    - セッションデータの構造化
    ```python
    SESSION_KEYS = [
        'questions', 'current_question', 'score',
        'quiz_history', 'grade', 'category',
        'subcategory', 'difficulty'
    ]
    ```

    ## 3. 問題優先順位付けの実装
    ### 課題
    - 未回答問題の特定が困難
    - 正答率計算の精度
    - パフォーマンスの低下

    ### 解決策
    - 3段階の優先順位システム実装
        1. 未回答問題
        2. 低正答率問題（50%未満）
        3. その他の問題
    - 問題統計のキャッシュ化
    - バッチ処理による集計

    ## 4. フロントエンド連携
    ### 課題
    - 非同期更新時のデータ不整合
    - 画面遷移の遅延
    - エラーメッセージの表示タイミング

    ### 解決策
    - Ajaxによる部分更新の実装
    - プログレスバーの表示
    - エラーハンドリングの統一化
    ```javascript
    function showError(message) {
        const errorDiv = document.getElementById('error-message');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 3000);
    }
    ```

    ## 5. データ整合性の確保
    ### 課題
    - トランザクション管理の複雑さ
    - 同時アクセス時のデータ競合
    - バックアップとリカバリ

    ### 解決策
    - SQLAlchemyのセッション管理の適切な利用
    - デッドロック対策の実装
    - 定期的なバックアップの自動化
    ```python
    try:
        db.session.begin_nested()
        # トランザクション処理
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Transaction failed: {e}")
    ```

     ## 6. supabaseとvercelの連携

    supabase側への連携としてdatabase_urlはdb.XXXX.supabase.coとする
    XXXX.supabase.coとすると、IP4のみのアクセスとなり、SSL証明書のエラーが発生する

    これでできるはず。