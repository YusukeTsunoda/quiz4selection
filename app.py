import os
import sys
import json
import random
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from models import db, QuizAttempt, User
from config import Config, supabase, is_development
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from functools import wraps
import commands  # コマンドをインポート
from extensions import db, migrate
from flask_login import LoginManager, current_user, login_user, logout_user, login_required

# .envファイルを読み込む
load_dotenv()

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# アプリケーションの初期化
app = Flask(__name__)

# 設定の読み込み
try:
    app.config.from_object(Config())
    logger.info("Application configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load application configuration: {e}")
    sys.exit(1)

# データベースの初期化
try:
    db.init_app(app)
    migrate.init_app(app, db)  # マイグレーションの初期化を追加
    with app.app_context():
        # データベース接続のテスト
        try:
            db.engine.connect().close()
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            sys.exit(1)
        
        # データベーステーブルの作成
        db.create_all()
        logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    sys.exit(1)

# テンプレートで使用する関数を登録
@app.context_processor
def utility_processor():
    return {
        'get_subcategories': get_subcategories,
        'CATEGORY_NAMES': CATEGORY_NAMES,
        'SUBCATEGORY_NAMES': SUBCATEGORY_NAMES
    }

# コマンドの登録
commands.init_app(app)

# データベース接続エラーハンドリング
def get_db():
    """データベース接続を取得する関数"""
    try:
        if not hasattr(g, 'db_conn'):
            g.db_conn = db.engine.connect()
        return g.db_conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
    raise
            
@app.teardown_appcontext
def close_db(error):
    """データベース接続を閉じる関数"""
    db_conn = getattr(g, 'db_conn', None)
    if db_conn is not None:
        db_conn.close()

def init_app():
    """アプリケーションの初期化"""
    with app.app_context():
        try:
            # データベースの作成
            db.create_all()
            # 接続テスト
            with get_db() as conn:
                conn.execute('SELECT 1')
            logger.info('Database connection successful')
        except Exception as e:
            logger.error(f'Database initialization error: {e}')
            sys.exit(1)

# 各ルートでのデータベースエラーハンドリング
@app.errorhandler(SQLAlchemyError)
def handle_db_error(error):
    """データベースエラーのハンドリング"""
    logger.error(f"Database error occurred: {error}")
    db.session.rollback()
    return "データベースエラーが発生しました。しばらく待ってから再試行してください。", 500

# カテゴリーと科目名の対応
CATEGORY_NAMES = {
    'japanese': '国語',
    'math': '算数',
    'science': '理科',
    'society': '社会',
    'life': '生活'
}

# サブカテゴリーの日本語名
SUBCATEGORY_NAMES = {
    'japanese': {
        'hiragana': 'ひらがな・カタカナの読み書き（清音、濁音、半濁音、長音、促音、拗音）',
        'kanji': '漢字の読み書き',
        'story': '物語文の読解',
        'explanation': '説明文の読解',
        'speech': 'スピーチの仕方',
        'composition': '作文',
        'letter': '手紙の書き方',
        'diary': '日記の書き方',
        'reading': '音読と朗読',
        'compound': '熟語の意味と使い方',
        'grammar': '主語と述語の関係',
        'summary': '文章の要旨をとらえる',
        'idioms': '慣用句・ことわざの理解と使用',
        'literature': '文学的な文章の読解',
        'comparison': '複数の資料を比較して読む',
        'discussion': '討論や話し合いの進め方',
        'language': '日本語の特質',
        'expression': '表現の工夫'
    },
    'math': {
        'numbers': '数と計算（1から100までの数の理解）',
        'addition': 'たし算',
        'subtraction': 'ひき算',
        'multiplication': 'かけ算',
        'division': 'わり算',
        'mult_2digit': '2桁×1桁の計算',
        'div_remainder': 'あまりのあるわり算',
        'shapes': '図形',
        'measurement': '長さ・かさの単位と測定',
        'time': '時刻と時間',
        'counting': 'ものの個数の数え方や分類',
        'large_numbers': '大きな数',
        'rounding': '概数と四捨五入',
        'decimals': '小数',
        'fractions': '分数',
        'angles': '角度',
        'area': '面積',
        'volume': '体積',
        'parallel_lines': '垂直と平行',
        'patterns': '変わり方調べ',
        'line_graphs': '折れ線グラフ',
        'integers': '整数の性質',
        'mult_div': '分数のかけ算・わり算',
        'congruence': '合同な図形',
        'percentage': '百分率とグラフ',
        'proportion': '比例',
        'circle_area': '円の面積',
        'scale': '縮図と拡大図',
        'ratio': '比とその利用',
        'data': 'データの調べ方',
        'probability': '場合の数と確率',
        'algebra': '文字を使った式',
        'abacus': 'そろばん'
    },
    'science': {
        'insects': '昆虫と植物の観察',
        'plants': '植物の育ち方',
        'light': '光の性質',
        'sound': '音の性質',
        'magnets': '磁石の性質',
        'electricity': '電気のはたらき',
        'force': '風やゴムの働き',
        'materials': '物の重さと体積',
        'sun': '太陽と地面の様子',
        'seasonal_changes': '季節と生き物',
        'weather': '天気の様子',
        'moon_stars': '月と星',
        'human_body': '人の体のつくりと運動',
        'volume_temp': '物の体積と温度',
        'water_states': '水のすがた',
        'flowers': '花のつくりと実',
        'animals': '動物の誕生',
        'fish': '魚のたんじょう',
        'typhoon': '台風と気象情報',
        'water_flow': '流れる水の働き',
        'electromagnet': '電磁石の性質',
        'pendulum': '振り子の運動',
        'ecosystem': '生物のつながり',
        'combustion': '燃焼の仕組み',
        'solution': '水溶液の性質',
        'lever': 'てこの規則性',
        'earth': '大地のつくりと変化'
    },
    'society': {
        'community': '身近な地域の様子',
        'map': '地図の読み方の基礎',
        'city': '市の様子と特徴',
        'public_service': '消防署や警察署の働き',
        'supermarket': 'スーパーマーケットの仕組み',
        'shopping': '商店街と大型店',
        'industry': '農家や工場の仕事',
        'culture': '昔の道具と暮らし',
        'prefectures': '都道府県と地方区分',
        'map_symbols': '地図記号の読み方',
        'local_geography': '自分たちの県の地理と産業',
        'water_resources': '水源と水道',
        'environment': 'ごみ処理と環境保護',
        'disaster_prevention': '災害から人々を守る工夫',
        'traditional_culture': '伝統文化と地域の発展',
        'regional_industry': '特色ある地域の産業',
        'geography': '国土の位置と地形の特色',
        'agriculture': '気候と農業や水産業との関係',
        'information': '情報産業とわたしたちの生活',
        'transportation': '運輸・通信と貿易',
        'disaster': '国土の自然災害の防止',
        'fishery': '我が国の農業や水産業',
        'manufacturing': '我が国の工業生産',
        'history_ancient': '歴史：縄文～古墳時代',
        'history_asuka': '歴史：飛鳥～奈良時代',
        'history_heian': '歴史：平安時代',
        'history_kamakura': '歴史：鎌倉時代',
        'history_muromachi': '歴史：室町時代',
        'history_azuchi': '歴史：安土桃山時代',
        'history_edo': '歴史：江戸時代',
        'history_meiji': '歴史：明治時代',
        'history_taisho': '歴史：大正時代',
        'history_modern': '歴史：昭和・平成時代',
        'constitution': '政治：日本国憲法',
        'government': '政治：国会・内閣・裁判所',
        'local': '政治：地方自治',
        'un': '政治：国際連合の働き',
        'international': '政治：世界の中の日本'
    },
    'life': {
        'school': '学校生活に慣れる（学校の施設や規則、友達との関わり）',
        'family': '家族や地域との関わり（自分の家族、通学路、公共施設）',
        'seasons': '季節と生活',
        'nature': '自然との触れ合い',
        'safety': '安全な生活',
        'growth': '自分の成長',
        'community': '地域との関わり'
    }
}

# 学年ごとのカテゴリーとサブカテゴリー
GRADE_CATEGORIES = {
    1: {
        'japanese': [
            'hiragana',    # ひらがな・カタカナの読み書き（清音、濁音、半濁音、長音、促音、拗音）
            'kanji',       # 漢字の読み書き（80字程度の基本的な漢字）
            'story',       # 物語文の読解（場面の様子や登場人物の気持ちを考える）
            'explanation', # 簡単な説明文の読解（文章の順序を理解する）
            'speech',      # スピーチや挨拶の仕方
            'composition'  # 簡単な作文（経験したことを書く）
        ],
        'math': [
            'numbers',     # 数と計算（1から100までの数の理解）
            'addition',    # たし算（1桁同士の計算）
            'subtraction', # ひき算（1桁同士の計算）
            'shapes',      # 図形（身の回りにある形、まる・さんかく・しかく）
            'measurement', # 大きさくらべ（長さ、かさの比較）
            'time',        # 時計の読み方（時刻の理解）
            'counting'     # ものの個数の数え方や分類の仕方
        ],
        'life': [
            'school',      # 学校生活に慣れる（学校の施設や規則、友達との関わり）
            'family',      # 家族や地域との関わり（自分の家族、通学路、公共施設）
            'seasons',     # 季節と生活
            'nature',      # 自然との触れ合い
            'safety',      # 安全な生活
            'growth'       # 自分の成長
        ]
    },
    2: {
        'japanese': [
            'story',       # 物語文の読解（場面の様子、登場人物の行動）
            'explanation', # 説明文の読解（主な内容、つながり）
            'kanji',       # 漢字の読み書き（160字程度）
            'composition', # 作文（順序を考えて書く）
            'letter',      # 手紙の書き方
            'diary',       # 日記の書き方
            'speech'       # スピーチの仕方
        ],
        'math': [
            'addition',       # たし算（2桁、3桁の計算）
            'subtraction',    # ひき算（2桁、3桁の計算）
            'multiplication', # かけ算（九九の導入）
            'measurement',    # 長さ・かさの単位（cm、m、L、dL、mL）
            'time',          # 時間の計算
            'shapes'         # 図形（三角形、四角形、箱の形）
        ],
        'life': [
            'seasons',     # 季節と生活の変化
            'community',   # 地域との関わり
            'nature',      # 動植物の観察
            'growth'       # 成長の記録
        ]
    },
    3: {
        'japanese': [
            'kanji',       # 漢字の読み書き（配当漢字約200字）
            'story',       # 物語文の読解（あらすじ、登場人物）
            'explanation', # 説明文の読解（段落、要点）
            'speech',      # スピーチの仕方
            'reading',     # 音読と朗読
            'composition', # 作文の書き方
            'compound',    # 熟語の意味と使い方
            'grammar'      # 主語と述語の関係
        ],
        'math': [
            'multiplication', # かけ算九九の完成
            'division',      # わり算の導入と計算
            'mult_2digit',   # 2桁×1桁の計算
            'div_remainder', # あまりのあるわり算
            'time',          # 時間の計算
            'measurement',   # 長さ・重さの単位
            'shapes',        # 円と球
            'statistics',    # 表とグラフ（棒グラフ）
            'abacus'        # そろばん
        ],
        'science': [
            'insects',     # 昆虫と植物の観察
            'plants',      # 植物の育ち方
            'light',       # 光の性質
            'sound',       # 音の性質
            'magnets',     # 磁石の性質
            'sun',         # 太陽と地面の様子
            'force',       # 風やゴムの働き
            'materials'    # 物の重さと体積
        ],
        'society': [
            'community',     # 身近な地域の様子
            'map',          # 地図の読み方の基礎
            'city',         # 市の様子と特徴
            'public_service', # 消防署や警察署の働き
            'supermarket',   # スーパーマーケットの仕組み
            'shopping',      # 商店街と大型店
            'industry',      # 農家や工場の仕事
            'culture'        # 昔の道具と暮らし
        ]
    },
    4: {
        'japanese': [
            'kanji',       # 漢字の読み書き（配当漢字約200字）
            'summary',     # 文章の要旨をとらえる
            'story',       # 物語文の登場人物の心情理解
            'explanation', # 説明文の段落構成と中心文
            'idioms',      # 慣用句・ことわざの理解と使用
            'letter',      # 手紙の書き方
            'composition'  # 作文・感想文の書き方
        ],
        'math': [
            'large_numbers',  # 大きな数（1億までの数）
            'rounding',      # 概数と四捨五入
            'decimals',      # 小数（小数第3位まで）
            'fractions',     # 分数（真分数・仮分数・帯分数）
            'angles',        # 角度の測定と作図
            'area',          # 面積（正方形・長方形）
            'parallel_lines', # 垂直と平行
            'patterns',      # 変わり方調べ（数量関係）
            'line_graphs'    # 折れ線グラフ
        ],
        'science': [
            'seasonal_changes', # 季節と生き物（春夏秋冬の生き物の活動、1年を通した変化）
            'weather',         # 天気の様子（1日の気温変化、天気の変化と気温、水の蒸発と結露、雲と雨の関係）
            'electricity',     # 電気のはたらき（回路、光・音・熱・動き、乾電池の直列・並列）
            'moon_stars',      # 月と星（月の満ち欠け、星の明るさや色、星座の観察）
            'human_body',      # 人の体のつくりと運動（骨と筋肉、呼吸、血液循環）
            'volume_temp',     # 物の体積と温度（温度による体積変化、水の三態変化）
            'water_states',    # 水のすがた（固体・液体・気体、水の循環）
            'materials'        # 物の重さと体積（物の形と重さ、空気の重さ、水に溶けた物）
        ],
        'society': [
            'prefectures',        # 都道府県と地方区分
            'map_symbols',        # 地図記号の読み方
            'local_geography',    # 自分たちの県の地理と産業
            'water_resources',    # 水源と水道
            'environment',        # ごみ処理と環境保護
            'disaster_prevention', # 災害から人々を守る工夫
            'traditional_culture', # 伝統文化と地域の発展
            'regional_industry'    # 特色ある地域の産業
        ]
    },
    5: {
        'japanese': [
            'kanji',       # 漢字の読み書き（配当漢字約185字）
            'literature',  # 文学的な文章の読解（登場人物の心情、情景描写）
            'explanation', # 説明文の論理的な構成の理解
            'summary',     # 要約文の作成
            'comparison',  # 複数の資料を比較して読む
            'language',    # 和語・漢語・外来語の使い分け
            'composition', # 文章の構成を考えた作文
            'discussion'   # 討論や話し合いの進め方
        ],
        'math': [
            'integers',     # 整数の性質（約数・倍数）
            'fractions',    # 分数のたし算・ひき算
            'mult_div',     # 分数のかけ算・わり算
            'decimals',     # 小数のかけ算・わり算
            'congruence',   # 合同な図形
            'area',         # 図形の面積（三角形、平行四辺形）
            'volume',       # 体積（立方体、直方体）
            'percentage',   # 百分率とグラフ
            'proportion'    # 比例の考え方
        ],
        'science': [
            'plants',         # 植物の発芽と成長
            'flowers',        # 花のつくりと実
            'animals',        # 動物の誕生
            'fish',          # 魚のたんじょう
            'weather',        # 雲と天気の変化
            'typhoon',       # 台風と気象情報
            'water_flow',     # 流れる水の働き
            'electromagnet',  # 電磁石の性質
            'pendulum'       # 振り子の運動
        ],
        'society': [
            'geography',      # 国土の位置と地形の特色
            'agriculture',    # 気候と農業や水産業との関係
            'industry',      # 工業生産と工業地域
            'information',   # 情報産業とわたしたちの生活
            'transportation', # 運輸・通信と貿易
            'environment',   # わたしたちの生活と環境
            'disaster',      # 国土の自然災害の防止
            'fishery',       # 我が国の農業や水産業
            'manufacturing'  # 我が国の工業生産
        ]
    },
    6: {
        'japanese': [
            'kanji',       # 漢字の読み書き（配当漢字約190字）
            'literature',  # 文学的な文章の批評的な読み方
            'explanation', # 説明文や論説文の論理的な構造理解
            'comparison',  # 複数の資料を関連付けて読む
            'expression',  # 表現の工夫（比喩、反復など）
            'composition', # 文章の構成を工夫した作文
            'discussion', # 話し合いの効果的な進め方
            'language'    # 日本語の特質（語感、敬語）
        ],
        'math': [
            'fractions',     # 分数の計算（加減乗除）
            'algebra',       # 文字を使った式
            'circle_area',   # 円の面積
            'volume',        # 角柱と円柱の体積
            'scale',         # 縮図と拡大図
            'ratio',         # 比とその利用
            'proportion',    # 比例と反比例
            'data',          # データの調べ方（平均値、中央値など）
            'probability'    # 場合の数と確率
        ],
        'science': [
            'plants',        # 植物の養分と水の通り道
            'ecosystem',     # 生物のつながり（食物連鎖）
            'human_body',    # 人の体のつくりと働き
            'combustion',    # 燃焼の仕組み
            'solution',      # 水溶液の性質
            'lever',         # てこの規則性
            'electricity',   # 電気の利用
            'earth',         # 大地のつくりと変化
            'moon_stars'     # 月と太陽（月の満ち欠け）
        ],
        'society': [
            'history_ancient',     # 歴史：縄文～古墳時代
            'history_asuka',       # 歴史：飛鳥～奈良時代
            'history_heian',       # 歴史：平安時代
            'history_kamakura',    # 歴史：鎌倉時代
            'history_muromachi',   # 歴史：室町時代
            'history_azuchi',      # 歴史：安土桃山時代
            'history_edo',         # 歴史：江戸時代
            'history_meiji',       # 歴史：明治時代
            'history_taisho',      # 歴史：大正時代
            'history_modern',      # 歴史：昭和・平成時代
            'constitution',        # 政治：日本国憲法
            'government',          # 政治：国会・内閣・裁判所
            'local',              # 政治：地方自治
            'un',                 # 政治：国際連合の働き
            'international'       # 政治：世界の中の日本
        ]
    }
}

def get_subcategories(grade, category):
    """指定された学年とカテゴリのサブカテゴリを取得"""
    return GRADE_CATEGORIES.get(grade, {}).get(category, [])

def get_shuffled_question(question):
    """問題の選択肢をシャッフルする"""
    shuffled = question.copy()
    options = shuffled['options'].copy()
    correct = shuffled['correct']
    
    # 選択肢をシャッフル
    indices = list(range(len(options)))
    random.shuffle(indices)
    
    # 選択肢を並び替え
    shuffled['options'] = [options[i] for i in indices]
    # 正解のインデックスも更新
    shuffled['correct'] = indices.index(correct)
    
    return shuffled

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('ログインが必要です。', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('ログインが必要です。', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(session['user']['id'])
        if not user or not user.is_admin:
            flash('管理者権限が必要です。', 'error')
            return redirect(url_for('grade_select'))
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """ルートページのハンドラ"""
    return redirect(url_for('grade_select'))

@app.route('/grade_select')
@login_required
def grade_select():
    """学年選択ページを表示"""
    return render_template('grade_select.html')

@app.route('/grade/<int:grade>/category')
def select_category(grade):
    """カテゴリー選択ページを表示"""
    if grade < 1 or grade > 6:
        flash('無効な学年が選択されました')
        return redirect(url_for('grade_select'))
    
    return render_template('category_select.html', grade=grade)

@app.route('/grade/<int:grade>/category/<category>/subcategory')
def select_subcategory(grade, category):
    """サブカテゴリー選択ページを表示"""
    subcategories = get_subcategories(grade, category)
    return render_template('subcategory_select.html',
                           grade=grade,
                           category=category,
                           category_name=CATEGORY_NAMES[category],
                           subcategories=subcategories,
                           subcategory_names=SUBCATEGORY_NAMES[category])

@app.route('/grade/<int:grade>/category/<category>/subcategory/<subcategory>/difficulty')
def select_difficulty(grade, category, subcategory):
    """難易度選択画面を表示する"""
    try:
        if not current_user.is_authenticated:
            flash('ログインが必要です。', 'error')
            return redirect(url_for('login'))

        # 各難易度のクイズ統計を取得
        stats = {}
        for difficulty in ['easy', 'medium', 'hard']:
            # 問題データの存在確認と形式チェック
            file_path = f'quiz_data/grade_{grade}/{category}/{subcategory}/{difficulty}/questions.json'
            has_questions = False
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        questions = json.load(f)
                        if questions and isinstance(questions, list) and len(questions) > 0:
                            # 各問題の形式を確認
                            valid_format = all(
                                isinstance(q, dict) and 
                                'question' in q and 
                                'options' in q and 
                                ('correct' in q or 'correct_answer' in q) and 
                                isinstance(q['options'], list) 
                                for q in questions
                            )
                            has_questions = valid_format
                except Exception as e:
                    logger.error(f"Error reading questions from {file_path}: {e}")
                    has_questions = False

            # 統計情報の初期化
            stats[difficulty] = {
                'has_questions': has_questions,
                'attempts': 0,
                'avg_score': 0,
                'highest_score': 0
            }

            if has_questions:
                # クイズ履歴から統計を計算
                attempts = QuizAttempt.query.filter_by(
                    user_id=current_user.id,
                    grade=grade,
                    category=category,
                    subcategory=subcategory,
                    difficulty=difficulty
                ).all()

                if attempts:
                    stats[difficulty]['attempts'] = len(attempts)
                    total_score_percentage = sum((attempt.score / attempt.total_questions) * 100 for attempt in attempts)
                    stats[difficulty]['avg_score'] = total_score_percentage / len(attempts)
                    stats[difficulty]['highest_score'] = max((attempt.score / attempt.total_questions) * 100 for attempt in attempts)

        return render_template('difficulty_select.html',
                           grade=grade,
                           category=category,
                           subcategory=subcategory,
                           category_name=CATEGORY_NAMES[category],
                           subcategory_name=SUBCATEGORY_NAMES[category][subcategory],
                           stats=stats)

    except Exception as e:
        logger.error(f"Error in select_difficulty: {e}")
        flash('難易度選択画面の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('grade_select'))


@app.route('/start_quiz/<int:grade>/<category>/<subcategory>/<difficulty>')
@login_required
def start_quiz(grade, category, subcategory, difficulty):
    """クイズを開始する"""
    try:
        # ログイン情報を一時保存
        user_info = session.get('user')
        
        # クイズ関連のセッション情報のみをクリア
        quiz_keys = ['questions', 'current_question', 'score', 'quiz_history', 
                    'answered_questions', 'grade', 'category', 'subcategory', 'difficulty']
        for key in quiz_keys:
            if key in session:
                session.pop(key)
        
        # ログイン情報を復元
        session['user'] = user_info

        # 問題を取得
        questions = get_questions(grade, category, subcategory, difficulty)

        if not questions:
            flash('問題の取得に失敗しました。', 'error')
            return redirect(url_for('select_difficulty', grade=grade,
                            category=category, subcategory=subcategory))

        # セッションに情報を保存
        session['questions'] = questions
        session['current_question'] = 0
        session['score'] = 0
        session['quiz_history'] = []
        session['answered_questions'] = []
        session['grade'] = grade
        session['category'] = category
        session['subcategory'] = subcategory
        session['difficulty'] = difficulty

        # 最初の問題を表示
        first_question = questions[0]
        logger.info(f"First question data: {first_question}")
        
        # 問題データをJSONエンコード
        question_data_json = json.dumps(first_question, ensure_ascii=False)
        logger.info(f"Encoded question data: {question_data_json}")
        
        return render_template('quiz.html',
                            question=first_question['question'],
                            options=first_question['options'],
                            question_data=question_data_json,
                            current_question=0,
                            total_questions=len(questions),
                            score=0)

    except Exception as e:
        logger.error(f"Error in start_quiz: {e}")
        logger.exception("Full traceback:")
        flash('クイズの開始中にエラーが発生しました。', 'error')
        return redirect(url_for('grade_select'))


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'User not logged in'})

        data = request.get_json()
        logger.info(f"Received answer data: {data}")
        
        # answerとselectedの両方のキーをチェック
        selected_index = data.get('answer')
        if selected_index is None:
            selected_index = data.get('selected')
            
        # selected_indexがNoneの場合のエラーハンドリング
        if selected_index is None:
            logger.error("No answer received from client")
            return jsonify({'success': False, 'error': 'No answer selected'})
        
        current_question = session.get('current_question', 0)
        questions = session.get('questions', [])
        quiz_history = session.get('quiz_history', [])
        current_score = session.get('score', 0)

        if not questions or current_question >= len(questions):
            logger.error("Invalid question state")
            return jsonify({'success': False, 'error': 'Invalid question'})

        current_q = questions[current_question]
        correct_index = current_q.get('correct')
        logger.info(f"Question data: {current_q}")
        logger.info(f"Selected index: {selected_index}, Correct index: {correct_index}")
        
        # 型を合わせて比較（エラーハンドリングを追加）
        try:
            is_correct = int(selected_index) == int(correct_index)
            logger.info(f"Is correct: {is_correct}")
        except (ValueError, TypeError) as e:
            logger.error(f"Error comparing answers: {e}")
            return jsonify({'success': False, 'error': 'Invalid answer format'})
        
        if is_correct:
            current_score += 1
            session['score'] = current_score

        # 回答履歴を保存
        quiz_history.append({
            'question': current_q.get('question', ''),
            'user_answer': current_q['options'][int(selected_index)],
            'correct_answer': current_q['options'][int(correct_index)],
            'is_correct': is_correct,
            'options': current_q.get('options', []),
            'explanation': current_q.get('explanation', '')  # 解説を追加
        })
        session['quiz_history'] = quiz_history

        is_last_question = current_question == len(questions) - 1
        logger.info(f"Is last question: {is_last_question}")

        # 最後の問題の場合、QuizAttemptを保存
        if is_last_question:
            try:
                grade = session.get('grade')
                category = session.get('category')
                subcategory = session.get('subcategory')
                difficulty = session.get('difficulty')
                
                quiz_attempt = QuizAttempt(
                    user_id=current_user.id,
                    grade=grade,
                    category=category,
                    subcategory=subcategory,
                    difficulty=difficulty,
                    score=current_score,
                    total_questions=len(questions),
                    quiz_history=json.dumps(quiz_history)
                )
                db.session.add(quiz_attempt)
                db.session.commit()
                logger.info(f"Quiz attempt saved - User: {current_user.id}, Final score: {current_score}/{len(questions)}")
            except Exception as e:
                logger.error(f"Error saving quiz attempt: {e}")
                return jsonify({'success': False, 'error': 'Failed to save quiz attempt'})

        response_data = {
            'success': True,
            'isCorrect': is_correct,
            'currentScore': current_score,
            'isLastQuestion': is_last_question,
            'redirectUrl': url_for('result') if is_last_question else None
        }
        logger.info(f"Sending response: {response_data}")

        if not is_last_question:
            session['current_question'] = current_question + 1
                
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in submit_answer: {e}")
        logger.exception("Full traceback:")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/next_question', methods=['GET'])
def next_question():
    """次の問題を表示する"""
    try:
        questions = session.get('questions', [])
        current_question = session.get('current_question', 0)
        quiz_history = session.get('quiz_history', [])

        logger.info(f"Current question index: {current_question}")
        logger.info(f"Total questions: {len(questions)}")
        logger.info(f"Quiz history entries: {len(quiz_history)}")

        # 全問題が終了した場合
        if current_question >= len(questions):
            logger.info("Quiz completed, redirecting to result page")
            return redirect(url_for('result'))

        # 現在の問題を表示
        logger.info(f"Showing question {current_question + 1}")
        question_data = questions[current_question]
        # 問題データをJSONエンコード
        question_data_json = json.dumps(question_data, ensure_ascii=False)
        logger.info(f"Encoded question data: {question_data_json}")

        return render_template('quiz.html',
                               question=question_data['question'],
                               options=question_data['options'],
                               question_data=question_data_json,
                               current_question=current_question,
                               total_questions=len(questions),
                               score=session.get('score', 0))

    except Exception as e:
        logger.error(f"Error in next_question route: {e}")
        logger.exception("Full traceback:")
        return redirect(url_for('grade_select'))
    

@app.route('/dashboard')
@login_required
def dashboard():
    """学習成績ダッシュボードを表示"""
    try:
        if not current_user.is_authenticated:
            flash('ログインが必要です。', 'error')
            return redirect(url_for('login'))

        # セッションからユーザーIDを取得
        user_id = session.get('user', {}).get('id')
        if not user_id:
            flash('セッションが無効です。再度ログインしてください。', 'error')
            return redirect(url_for('login'))
            
        # クイズの試行履歴を取得
        quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).order_by(QuizAttempt.timestamp.desc()).all()
        
        # 進捗データの初期化
        progress = {grade: {} for grade in range(1, 7)}

        # 各学年、カテゴリー、サブカテゴリーごとの進捗を集計
        for grade in range(1, 7):
            # 学年ごとの利用可能なカテゴリーを取得
            available_categories = GRADE_CATEGORIES.get(grade, {}).keys()
            
            for category in available_categories:
                if category in CATEGORY_NAMES:
                    progress[grade][category] = {
                        'name': CATEGORY_NAMES[category],
                        'subcategories': {}
                    }

                    # 利用可能なサブカテゴリーを取得
                    for subcategory in get_subcategories(grade, category):
                        # クイズデータが存在するか確認
                        has_quiz_data = False
                        for difficulty in ['easy', 'medium', 'hard']:
                            file_path = f'quiz_data/grade_{grade}/{category}/{subcategory}/{difficulty}/questions.json'
                            if os.path.exists(file_path):
                                has_quiz_data = True
                                break
                        
                        if has_quiz_data:
                            # サブカテゴリー名の取得を安全に行う
                            subcategory_name = SUBCATEGORY_NAMES.get(category, {}).get(subcategory, subcategory)
                            progress[grade][category]['subcategories'][subcategory] = {
                                'name': subcategory_name,
                                'levels': {
                                    'easy': {'attempts': 0, 'avg_score': 0, 'highest_score': 0},
                                    'medium': {'attempts': 0, 'avg_score': 0, 'highest_score': 0},
                                    'hard': {'attempts': 0, 'avg_score': 0, 'highest_score': 0}
                                }
                            }

        # 試行履歴から統計を計算
        for attempt in quiz_attempts:
            grade = attempt.grade
            category = attempt.category
            subcategory = attempt.subcategory
            difficulty = attempt.difficulty
            
            # カテゴリーとサブカテゴリーが存在する場合のみ統計を更新
            if (category in progress.get(grade, {}) and 
                subcategory in progress[grade][category].get('subcategories', {})):
                
                score_percentage = (attempt.score / attempt.total_questions) * 100
                stats = progress[grade][category]['subcategories'][subcategory]['levels'][difficulty]
                stats['attempts'] += 1

                # 平均スコアの更新
                current_total = stats['avg_score'] * (stats['attempts'] - 1)
                stats['avg_score'] = (current_total + score_percentage) / stats['attempts']

                # 最高スコアの更新
                stats['highest_score'] = max(stats['highest_score'], score_percentage)

        # 難易度の日本語名
        difficulty_names = {
            'easy': '初級',
            'medium': '中級',
            'hard': '上級'
        }

        return render_template('dashboard.html',
                           progress=progress,
                           difficulty_names=difficulty_names,
                           quiz_attempts=quiz_attempts)

    except Exception as e:
        logger.error(f"Error in dashboard route: {e}")
        flash('ダッシュボードの表示中にエラーが発生しました。', 'error')
        return redirect(url_for('login'))
    

@app.route('/result')
def result():
    """クイズ結果を表示する"""
    try:
        # セッションから必要な情報を取得
        score = session.get('score', 0)
        total_questions = len(session.get('questions', []))
        quiz_history = session.get('quiz_history', [])

        if not quiz_history:
            logger.error("No quiz history found")
            flash('クイズ履歴が見つかりません。', 'error')
            return redirect(url_for('grade_select'))
    
        logger.info(f"Showing result page - Score: {score}/{total_questions}")

        return render_template('result.html',
                           score=score,
                           total_questions=total_questions,
                           quiz_history=quiz_history)

    except Exception as e:
        logger.error(f"Error in result route: {e}")
        flash('結果の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('grade_select'))
    

def get_questions(grade, category, subcategory, difficulty):
    """指定された条件に基づいて問題を取得する"""
    try:
        logger.info(
            f"Getting questions for grade={grade}, category={category}, subcategory={subcategory}, difficulty={difficulty}")

        # 問題データを取得
        questions, error = get_quiz_data(
            grade, category, subcategory, difficulty)
        if error:
            logger.error(f"Error getting quiz data: {error}")
            return []
        if not questions:
            logger.error("No questions returned from get_quiz_data")
            return []

        logger.info(f"Retrieved {len(questions)} questions from quiz data")

        # 問題をランダムに選択し、10問を選択
        if len(questions) > 10:
            selected_questions = random.sample(questions, 10)
            logger.info(
                f"Selected 10 random questions from {
                    len(questions)} available questions")
        else:
            selected_questions = questions
            logger.info(f"Using all {len(questions)} available questions")

        return selected_questions
    except Exception as e:
        logger.error(f"Error in get_questions: {e}")
        logger.exception("Full traceback:")
        return []


def get_quiz_data(grade, category, subcategory, difficulty):
    """クイズデータを取得する関数"""
    try:
        # 新しいフォルダ構造に基づいたファイルパス
        file_path = f'quiz_data/grade_{grade}/{category}/{subcategory}/{difficulty}/questions.json'
        logger.info(f"Loading quiz data from: {file_path}")

        # ファイルの存在確認
        if not os.path.exists(file_path):
            logger.error(f"Quiz data file not found: {file_path}")
            return None, "問題データファイルが見つかりません"

        # ファイルの読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Successfully loaded JSON data")

            if not data or not isinstance(data, list):
                logger.error("Invalid question data format")
                return None, "問題データの形式が正しくありません"

            # 問題をシャッフル
            shuffled_questions = [get_shuffled_question(q) for q in data]
            logger.info(f"Successfully loaded and shuffled {len(shuffled_questions)} questions")

            return shuffled_questions, None

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return None, "問題データの形式が正しくありません"
    except Exception as e:
        logger.error(f"Error in get_quiz_data: {e}")
        logger.exception("Full traceback:")
        return None, "問題データの読み込み中にエラーが発生しました"


@app.route('/quiz_history/<int:grade>/<category>/<subcategory>/<difficulty>')
@login_required
def quiz_history(grade, category, subcategory, difficulty):
    """特定の条件でのクイズ履歴を表示"""
    try:
        # クイズ履歴を取得
        attempts = QuizAttempt.query.filter_by(
            user_id=current_user.id,
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty
        ).order_by(QuizAttempt.timestamp.desc()).all()

        logger.info(f"Found {len(attempts)} attempts for user {current_user.id}")
        
        history_data = []
        for attempt in attempts:
            logger.info(f"Processing attempt {attempt.id}")
            try:
                if attempt.quiz_history:
                    # 文字列の場合はJSONとしてパース
                    if isinstance(attempt.quiz_history, str):
                        quiz_history = json.loads(attempt.quiz_history)
                    else:
                        quiz_history = attempt.quiz_history
                    
                    logger.info(f"Quiz history for attempt {attempt.id}: {quiz_history}")
                    
                    history_data.append({
                        'timestamp': attempt.timestamp,
                        'score': attempt.score,
                        'total_questions': attempt.total_questions,
                        'questions': quiz_history
                    })
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding quiz history for attempt {attempt.id}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing attempt {attempt.id}: {e}")
                continue

        logger.info(f"Processed {len(history_data)} history entries")

        # 問題データを取得して問題別統計を計算
        questions_data, error = get_quiz_data(grade, category, subcategory, difficulty)
        question_stats = {}
        
        if questions_data:
            # 問題ごとの統計を初期化
            for question in questions_data:
                question_text = question.get('question', '')
                question_stats[question_text] = {
                    'total_attempts': 0,
                    'correct_attempts': 0,
                    'percentage': 0,
                    'has_attempts': False  # 回答有無を追跡
                }
        
            # 履歴から統計を計算
            for entry in history_data:
                for question in entry['questions']:
                    question_text = question.get('question', '')
                    if question_text in question_stats:
                        question_stats[question_text]['total_attempts'] += 1
                        question_stats[question_text]['has_attempts'] = True
                        if question.get('is_correct', False):
                            question_stats[question_text]['correct_attempts'] += 1
        
            # 正答率を計算
            for stats in question_stats.values():
                if stats['total_attempts'] > 0:
                    stats['percentage'] = (stats['correct_attempts'] / stats['total_attempts']) * 100

            # 回答済みと未回答の問題に分類
            answered_questions = {q: stats for q, stats in question_stats.items() if stats['has_attempts']}
            unanswered_questions = {q: stats for q, stats in question_stats.items() if not stats['has_attempts']}

            # 回答済み問題を正答率でソート（降順）
            sorted_answered = dict(sorted(
                answered_questions.items(),
                key=lambda x: (x[1]['percentage'], x[1]['total_attempts']),
                reverse=True
            ))

            # 未回答問題をアルファベット順でソート
            sorted_unanswered = dict(sorted(unanswered_questions.items()))

            # 回答済み問題と未回答問題を結合
            question_stats = {**sorted_answered, **sorted_unanswered}
        
        return render_template(
            'quiz_history.html',
            history_data=history_data,
            question_stats=question_stats,
            grade=grade,
            category=category,
            subcategory=subcategory,
            difficulty=difficulty,
            category_name=CATEGORY_NAMES.get(category, category),
            subcategory_name=SUBCATEGORY_NAMES.get(category, {}).get(subcategory, subcategory)
        )

    except Exception as e:
        logger.error(f"Error in quiz_history route: {e}")
        flash('クイズ履歴の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('dashboard'))


@app.route('/signup', methods=['GET', 'POST'], endpoint='signup')
def signup():
    # セッションをクリア
    session.clear()
    
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            username = request.form['username']
            
            # メールアドレスの重複チェック
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('このメールアドレスは既に登録されています。', 'error')
                return render_template('signup.html')
            
            # ユーザー名の重複チェック
            existing_username = User.query.filter_by(username=username).first()
            if existing_username:
                flash('このユーザー名は既に使用されています。', 'error')
                return render_template('signup.html')
            
            if is_development():
                # 開発環境では認証をスキップ
                user_id = f'dev-{username}'
            else:
                # Supabaseでユーザー登録
                try:
                    response = supabase.auth.sign_up({
                        "email": email,
                        "password": password
                    })
                    user_id = response.user.id
                except Exception as auth_error:
                    logger.error(f"Supabase signup error: {auth_error}")
                    flash('アカウント登録に失敗しました。', 'error')
                    return render_template('signup.html')
            
            # ユーザーをデータベースに保存
            user = User(
                id=user_id,
                email=email,
                username=username,
                is_admin=False
            )
            db.session.add(user)
            db.session.commit()
            
            flash('アカウントが登録されました。ログインしてください。', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Error in signup: {e}")
            db.session.rollback()
            flash('登録に失敗しました。', 'error')
            return render_template('signup.html')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            
            if is_development():
                # 開発環境では認証をスキップ
                user = User.query.filter_by(email=email).first()
                if not user:
                    # 開発環境用のテストユーザーを作成
                    user = User(
                        id='dev-user-id',
                        email=email,
                        username=email.split('@')[0],
                        is_admin=False
                    )
                    db.session.add(user)
                    db.session.commit()
            else:
                # 本番環境での認証処理
                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    user = User.query.filter_by(email=email).first()
                    if not user:
                        flash('ユーザーが見つかりません。先にアカウント登録を行ってください。', 'error')
                        return redirect(url_for('signup'))
                except Exception as auth_error:
                    logger.error(f"Authentication error: {auth_error}")
                    flash('メールアドレスまたはパスワードが正しくありません。', 'error')
                    return render_template('login.html')
            
            # Flask-Loginでユーザーをログイン
            login_user(user)
            
            # セッションにユーザー情報を保存
            session['user'] = {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'is_admin': user.is_admin
            }
            
            flash('ログインしました。', 'success')
            return redirect(url_for('admin_dashboard' if user.is_admin else 'grade_select'))
            
        except Exception as e:
            logger.error(f"Error in login: {e}")
            flash('ログインに失敗しました。', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    try:
        # Supabaseからログアウト
        supabase.auth.sign_out()
        session.clear()
        flash('ログアウトしました。', 'success')
    except Exception as e:
        logger.error(f"Error in logout: {e}")
        flash('ログアウトに失敗しました。', 'error')
        
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    """管理者ダッシュボード"""
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin/dashboard.html', users=users)

@app.route('/admin/user/<user_id>', methods=['GET', 'POST'])
@admin_required
def admin_user_edit(user_id):
    """ユーザーの権限編集"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # 許可する学年を更新
            allowed_grades = [int(grade) for grade in request.form.getlist('grades[]')]
            user.allowed_grades = allowed_grades
            
            # 許可する科目とサブカテゴリを更新
            allowed_subjects = {}
            for grade in range(1, 7):
                for category in CATEGORY_NAMES.keys():
                    subcategories = request.form.getlist(f'subjects[{grade}][{category}][]')
                    if subcategories:
                        if category not in allowed_subjects:
                            allowed_subjects[category] = []
                        allowed_subjects[category].extend(subcategories)
            
            # 重複を除去
            for category in allowed_subjects:
                allowed_subjects[category] = list(set(allowed_subjects[category]))
            
            user.allowed_subjects = allowed_subjects
            db.session.commit()
            
            flash('ユーザー権限を更新しました。', 'success')
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            logger.error(f"Error updating user permissions: {e}")
            db.session.rollback()
            flash('ユーザー権限の更新に失敗しました。', 'error')
    
    return render_template('admin/user_edit.html',
                         user=user,
                         CATEGORY_NAMES=CATEGORY_NAMES,
                         SUBCATEGORY_NAMES=SUBCATEGORY_NAMES)

@app.route('/admin/setup', methods=['POST'])
def admin_setup():
    """本番環境での初期管理者セットアップ用エンドポイント"""
    try:
        # 環境変数から設定用のシークレットキーを取得
        setup_secret = os.environ.get('ADMIN_SETUP_SECRET')
        if not setup_secret:
            return jsonify({'error': 'ADMIN_SETUP_SECRET is not configured'}), 500

        # リクエストからシークレットキーとメールアドレスを取得
        data = request.get_json()
        if not data or data.get('secret') != setup_secret:
            return jsonify({'error': 'Invalid secret key'}), 403

        email = data.get('email')
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # ユーザーを検索
        user = User.get_by_email(email)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # 管理者に設定
        if user.promote_to_admin():
            return jsonify({'message': f'Successfully set {email} as admin'})
        else:
            return jsonify({'message': f'User {email} is already an admin'})

    except Exception as e:
        logger.error(f"Error in admin setup: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            
            # メールアドレスの存在確認
            user = User.get_by_email(email)
            if not user:
                flash('指定されたメールアドレスは登録されていません。', 'error')
                return redirect(url_for('reset_password'))
            
            # Supabaseでパスワードリセットメールを送信
            supabase.auth.reset_password_email(email)
            
            flash('パスワードリセットの手順をメールで送信しました。', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            logger.error(f"Error in reset_password: {e}")
            flash('パスワードリセットメールの送信に失敗しました。', 'error')
            
    return render_template('reset_password.html')

@app.route('/user/profile')
@login_required
def user_profile():
    """ユーザープロフィールページを表示"""
    user = User.query.get(session['user']['id'])
    return render_template('user_profile.html',
                         user=user,
                         CATEGORY_NAMES=CATEGORY_NAMES,
                         SUBCATEGORY_NAMES=SUBCATEGORY_NAMES)

@app.route('/admin/user/<user_id>/detail')
@admin_required
def admin_user_detail(user_id):
    """ユーザー詳細ページを表示（管理者用）"""
    user = User.query.get_or_404(user_id)
    quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).order_by(QuizAttempt.timestamp.desc()).limit(10).all()
    return render_template('admin/user_detail.html',
                         user=user,
                         quiz_attempts=quiz_attempts,
                         CATEGORY_NAMES=CATEGORY_NAMES,
                         SUBCATEGORY_NAMES=SUBCATEGORY_NAMES)

# LoginManagerの初期化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
