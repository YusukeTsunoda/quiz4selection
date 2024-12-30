import os
import json
import random
import logging

logger = logging.getLogger(__name__)

# カテゴリーと科目の定義
CATEGORY_NAMES = {
    'japanese': '国語',
    'math': '算数',
    'science': '理科',
    'society': '社会'
}

SUBCATEGORY_NAMES = {
    'kanji': '漢字',
    'reading': '読解',
    'grammar': '文法',
    'writing': '作文',
    'calculation': '計算',
    'figure': '図形',
    'measurement': '測定',
    'graph': 'グラフ',
    'physics': '物理',
    'chemistry': '化学',
    'biology': '生物',
    'earth_science': '地学',
    'history': '歴史',
    'geography': '地理',
    'civics': '公民',
    'current_events': '時事',
    'prefectures': '都道府県'
}

def get_subcategories(grade, category):
    """指定された学年とカテゴリのサブカテゴリを取得"""
    # カテゴリに応じたサブカテゴリのマッピング
    category_subcategories = {
        'japanese': ['kanji', 'reading', 'grammar', 'writing'],
        'math': ['calculation', 'figure', 'measurement', 'graph'],
        'science': ['physics', 'chemistry', 'biology', 'earth_science'],
        'society': ['history', 'geography', 'civics', 'current_events', 'prefectures']
    }
    return category_subcategories.get(category, [])

def get_questions(grade, category, subcategory, difficulty):
    """指定された条件に基づいて問題を取得する"""
    try:
        logger.info(f"Getting questions for grade={grade}, category={category}, subcategory={subcategory}, difficulty={difficulty}")

        # 問題データを取得
        file_path = f'quiz_data/grade_{grade}/{category}.json'
        logger.info(f"Loading quiz data from: {file_path}")

        # ファイルの存在確認
        if not os.path.exists(file_path):
            logger.error(f"Quiz data file not found: {file_path}")
            return []

        # ファイルの読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Successfully loaded JSON data")

            # サブカテゴリの確認
            if subcategory not in data:
                logger.error(f"Subcategory {subcategory} not found in data")
                return []

            logger.info(f"Found subcategory {subcategory}")

            # 難易度の確認
            if difficulty not in data[subcategory]:
                logger.error(f"Difficulty {difficulty} not found in {subcategory}")
                return []

            all_questions = data[subcategory][difficulty]
            if not all_questions:
                logger.error(f"No questions found for {category}/{subcategory}/{difficulty}")
                return []

            # 利用可能な問題数を確認
            num_questions = len(all_questions)
            target_questions = min(10, num_questions)  # 10問または利用可能な全問題数の少ない方

            logger.info(f"Total available questions: {num_questions}")
            logger.info(f"Target number of questions: {target_questions}")

            # 問題をランダムに選択
            selected_questions = random.sample(all_questions, target_questions)
            logger.info(f"Successfully selected {len(selected_questions)} questions")

            return selected_questions

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error in get_questions: {e}")
        logger.exception("Full traceback:")
        return [] 