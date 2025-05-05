import os
import json
import logging
from .loader import get_questions, get_questions_path, get_available_categories, get_available_subcategories, get_available_difficulties

# ロガーの設定
logger = logging.getLogger(__name__)

# 注意: 以下の関数は後方互換性のために残していますが、
# 新しいコードでは loader.py の関数を直接使用することを推奨します

def load_questions():
    """
    すべての問題を一度に読み込む関数（レガシー）
    メモリ使用量が多いため、新しいコードでは get_questions() を使用してください
    
    Returns:
        dict: カテゴリー別の問題辞書
    """
    logger.warning("load_questions() は非推奨です。代わりに get_questions() を使用してください。")
    
    questions_by_category = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 各学年のディレクトリをスキャン
    for grade_dir in os.listdir(base_dir):
        if not grade_dir.startswith('grade_'):
            continue
            
        grade = int(grade_dir.split('_')[1])
        grade_path = os.path.join(base_dir, grade_dir)
        
        if not os.path.isdir(grade_path):
            continue
            
        # 各カテゴリのディレクトリをスキャン
        for category in os.listdir(grade_path):
            category_path = os.path.join(grade_path, category)
            
            if not os.path.isdir(category_path):
                continue
                
            # 各サブカテゴリのディレクトリをスキャン
            for subcategory in os.listdir(category_path):
                subcategory_path = os.path.join(category_path, subcategory)
                
                if not os.path.isdir(subcategory_path):
                    continue
                    
                # 各難易度のディレクトリをスキャン
                for difficulty in os.listdir(subcategory_path):
                    difficulty_path = os.path.join(subcategory_path, difficulty)
                    
                    if not os.path.isdir(difficulty_path):
                        continue
                        
                    # questions.jsonファイルを読み込む
                    file_path = os.path.join(difficulty_path, 'questions.json')
                    
                    if not os.path.exists(file_path):
                        continue
                        
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                            # 辞書構造を構築
                            if grade not in questions_by_category:
                                questions_by_category[grade] = {}
                                
                            if category not in questions_by_category[grade]:
                                questions_by_category[grade][category] = {}
                                
                            if subcategory not in questions_by_category[grade][category]:
                                questions_by_category[grade][category][subcategory] = {}
                                
                            questions_by_category[grade][category][subcategory][difficulty] = data
                            
                    except Exception as e:
                        logger.error(f"Error loading {file_path}: {e}")
                
    return questions_by_category

# 後方互換性のために残しておく（非推奨）
# 新しいコードでは直接 get_questions() を使用してください
questions_by_category = None
