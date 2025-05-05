import os
import json
import logging
from flask import current_app
from extensions import cache

# ロガーの設定
logger = logging.getLogger(__name__)

def get_questions_path(grade, category, subcategory, difficulty):
    """
    指定されたパラメータに基づいてクイズデータのJSONファイルパスを生成します。
    
    Args:
        grade (int): 学年 (1-6)
        category (str): カテゴリー (例: 'math', 'japanese')
        subcategory (str): サブカテゴリー (例: 'addition', 'kanji')
        difficulty (str): 難易度 ('easy', 'medium', 'hard')
        
    Returns:
        str: JSONファイルの絶対パス
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(
        base_dir, 
        f'grade_{grade}', 
        category, 
        subcategory, 
        difficulty, 
        'questions.json'
    )
    return file_path

@cache.memoize(timeout=3600)  # 1時間キャッシュ
def load_questions_from_file(file_path):
    """
    指定されたパスからJSONファイルを読み込みます。
    結果はキャッシュされ、次回以降のアクセスが高速化されます。
    
    Args:
        file_path (str): JSONファイルの絶対パス
        
    Returns:
        list: 問題のリスト。ファイルが存在しない場合は空のリスト。
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"問題ファイルが見つかりません: {file_path}")
            return []
            
        with open(file_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
            logger.info(f"問題を読み込みました: {file_path} ({len(questions)}問)")
            return questions
            
    except json.JSONDecodeError as e:
        logger.error(f"JSONの解析エラー: {file_path} - {e}")
        return []
    except Exception as e:
        logger.error(f"問題の読み込みエラー: {file_path} - {e}")
        return []

def get_questions(grade, category, subcategory, difficulty):
    """
    指定されたパラメータに基づいてクイズの問題を読み込みます。
    必要なときに個別にJSONファイルを読み込むことでメモリ使用量を削減します。
    結果はキャッシュされ、次回以降のアクセスが高速化されます。
    
    Args:
        grade (int): 学年 (1-6)
        category (str): カテゴリー (例: 'math', 'japanese')
        subcategory (str): サブカテゴリー (例: 'addition', 'kanji')
        difficulty (str): 難易度 ('easy', 'medium', 'hard')
        
    Returns:
        list: 問題のリスト。ファイルが存在しない場合は空のリスト。
    """
    file_path = get_questions_path(grade, category, subcategory, difficulty)
    return load_questions_from_file(file_path)

def get_available_categories(grade):
    """
    指定された学年で利用可能なカテゴリーのリストを取得します。
    
    Args:
        grade (int): 学年 (1-6)
        
    Returns:
        list: 利用可能なカテゴリーのリスト
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    grade_dir = os.path.join(base_dir, f'grade_{grade}')
    
    if not os.path.exists(grade_dir):
        logger.warning(f"学年ディレクトリが見つかりません: {grade_dir}")
        return []
        
    return [d for d in os.listdir(grade_dir) 
            if os.path.isdir(os.path.join(grade_dir, d))]

def get_available_subcategories(grade, category):
    """
    指定された学年とカテゴリーで利用可能なサブカテゴリーのリストを取得します。
    
    Args:
        grade (int): 学年 (1-6)
        category (str): カテゴリー (例: 'math', 'japanese')
        
    Returns:
        list: 利用可能なサブカテゴリーのリスト
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    category_dir = os.path.join(base_dir, f'grade_{grade}', category)
    
    if not os.path.exists(category_dir):
        logger.warning(f"カテゴリーディレクトリが見つかりません: {category_dir}")
        return []
        
    return [d for d in os.listdir(category_dir) 
            if os.path.isdir(os.path.join(category_dir, d))]

def get_available_difficulties(grade, category, subcategory):
    """
    指定された学年、カテゴリー、サブカテゴリーで利用可能な難易度のリストを取得します。
    
    Args:
        grade (int): 学年 (1-6)
        category (str): カテゴリー (例: 'math', 'japanese')
        subcategory (str): サブカテゴリー (例: 'addition', 'kanji')
        
    Returns:
        list: 利用可能な難易度のリスト
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    subcategory_dir = os.path.join(base_dir, f'grade_{grade}', category, subcategory)
    
    if not os.path.exists(subcategory_dir):
        logger.warning(f"サブカテゴリーディレクトリが見つかりません: {subcategory_dir}")
        return []
        
    return [d for d in os.listdir(subcategory_dir) 
            if os.path.isdir(os.path.join(subcategory_dir, d))]
