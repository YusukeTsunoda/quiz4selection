# Quiz4selection リバースエンジニアリング仕様書

## 1. システム概要

### 1.1 目的

- 小学生向けの学習支援クイズアプリケーション
- 学年別、教科別、単元別の問題を提供
- 学習進捗の管理と成績の可視化

### 1.2 主要機能

1. ユーザー管理システム

   - ユーザー登録/ログイン
   - パスワードリセット
   - 管理者権限管理

2. クイズシステム

   - 学年/教科/単元/難易度選択
   - ランダム出題
   - 選択肢のシャッフル
   - 即時採点
   - 解説表示

3. 進捗管理システム

   - スコア記録
   - 履歴管理
   - 統計情報表示

4. 管理者機能
   - ユーザー権限管理
   - 問題データ管理
   - アクセス制御

## 2. 技術要件

### 2.1 認証・認可

- セッション管理必須
- ユーザー認証（メール/パスワード）
- 権限ベースのアクセス制御
- 管理者特権管理

### 2.2 データベース要件

#### ユーザーテーブル

- id: ユーザー ID
- email: メールアドレス
- username: ユーザー名
- is_admin: 管理者フラグ
- allowed_grades: 許可された学年
- allowed_subjects: 許可された教科

#### クイズ履歴テーブル

- user_id: ユーザー ID
- grade: 学年
- category: 教科
- subcategory: 単元
- difficulty: 難易度
- score: スコア
- total_questions: 問題数
- timestamp: 実施日時
- quiz_history: 詳細履歴

#### 問題履歴テーブル

- user_id: ユーザー ID
- question_text: 問題文
- is_correct: 正誤
- timestamp: 回答日時

### 2.3 ファイルシステム要件

#### 問題データ構造

```
quiz_data/
  grade_{1-6}/
    {category}/
      {subcategory}/
        {difficulty}/
          questions.json
```

### 2.4 セッション管理要件

必須セッション情報:

- questions: 問題リスト
- current_question: 現在の問題
- score: 現在のスコア
- quiz_history: クイズ履歴
- grade: 学年
- category: 教科
- subcategory: 単元
- difficulty: 難易度

### 2.5 フロントエンド要件

- レスポンシブデザイン
- プログレスバー表示
- アニメーション効果
- エラーハンドリング
- 非同期通信

## 3. API 仕様

### 3.1 認証 API

```
POST /login
POST /logout
POST /signup
POST /reset-password
```

### 3.2 クイズ API

```
GET /grade_select
GET /grade/<grade>/category
GET /grade/<grade>/category/<category>/subcategory
GET /grade/<grade>/category/<category>/subcategory/<subcategory>/difficulty
GET /start_quiz/<grade>/<category>/<subcategory>/<difficulty>
POST /submit_answer
GET /next_question
GET /result
```

### 3.3 管理者 API

```
GET /admin/subjects
GET /admin/subjects/<grade>
GET /admin/subjects/<grade>/<subject>
GET /admin/user/<user_id>
POST /admin/setup
```

## 4. 非機能要件

### 4.1 パフォーマンス要件

- ページロード時間: 3 秒以内
- API 応答時間: 1 秒以内
- 同時接続ユーザー数: 100 以上

### 4.2 セキュリティ要件

- CSRF 対策
- XSS 対策
- SQL インジェクション対策
- セッション管理
- パスワードハッシュ化
- 入力値バリデーション

### 4.3 可用性要件

- サービス稼働率: 99.9%
- バックアップ体制
- エラー検知・通知

### 4.4 保守性要件

- ログ出力
- エラーハンドリング
- コード分割
- 設定の外部化

## 5. 移行時の注意点

### 5.1 データ構造

- 問題データの JSON 形式を維持
- データベーススキーマの互換性確保
- セッション情報の構造維持

### 5.2 機能の互換性

- 選択肢シャッフルロジックの同一性確保
- スコア計算ロジックの一貫性
- 進捗管理システムの互換性

### 5.3 UI/UX

- レスポンシブデザインの維持
- アニメーション効果の再現
- エラーメッセージの一貫性

### 5.4 セキュリティ

- 認証システムの強化
- セッション管理の改善
- アクセス制御の厳密化

## 6. 推奨技術スタック（Next.js 版）

### 6.1 フロントエンド

- Next.js (App Router)
- TypeScript
- TailwindCSS
- React Query
- Zustand (状態管理)

### 6.2 バックエンド

- Next.js API Routes
- Prisma (ORM)
- NextAuth.js (認証)

### 6.3 データベース

- PostgreSQL
- Redis (セッション管理)

### 6.4 インフラ

- Vercel
- Supabase (認証/データベース)

### 6.5 開発環境

- ESLint
- Prettier
- Jest
- Cypress
