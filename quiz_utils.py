import json
import os
from typing import Dict, List, Optional

def load_quiz_data(grade: int, category: str, subcategory: Optional[str] = None, difficulty: Optional[str] = None) -> Dict:
    """
    指定された学年、カテゴリ、サブカテゴリ、難易度のクイズデータを読み込む
    
    Args:
        grade (int): 学年 (1-6)
        category (str): カテゴリ (japanese, math, etc.)
        subcategory (str, optional): サブカテゴリ (kanji, calculation, etc.)
        difficulty (str, optional): 難易度 (easy, medium, hard)
    
    Returns:
        Dict: クイズデータ
    """
    file_path = f"quiz_data/grade_{grade}/{category}.json"
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Quiz data not found for grade {grade} and category {category}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if subcategory:
        if subcategory not in data:
            raise ValueError(f"Subcategory {subcategory} not found")
        data = data[subcategory]
        
        if difficulty:
            if difficulty not in data:
                raise ValueError(f"Difficulty {difficulty} not found")
            data = data[difficulty]
    
    return data

def get_available_categories(grade: int) -> List[str]:
    """
    指定された学年で利用可能なカテゴリの一覧を取得
    
    Args:
        grade (int): 学年 (1-6)
    
    Returns:
        List[str]: カテゴリの一覧
    """
    grade_dir = f"quiz_data/grade_{grade}"
    if not os.path.exists(grade_dir):
        return []
    
    return [f.split('.')[0] for f in os.listdir(grade_dir) if f.endswith('.json')]

def get_available_subcategories(grade: int, category: str) -> List[str]:
    """
    指定された学年とカテゴリで利用可能なサブカテゴリの一覧を取得
    
    Args:
        grade (int): 学年 (1-6)
        category (str): カテゴリ
    
    Returns:
        List[str]: サブカテゴリの一覧
    """
    try:
        data = load_quiz_data(grade, category)
        return list(data.keys())
    except FileNotFoundError:
        return []

def get_available_difficulties(grade: int, category: str, subcategory: str) -> List[str]:
    """
    指定された学年、カテゴリ、サブカテゴリで利用可能な難易度の一覧を取得
    
    Args:
        grade (int): 学年 (1-6)
        category (str): カテゴリ
        subcategory (str): サブカテゴリ
    
    Returns:
        List[str]: 難易度の一覧
    """
    try:
        data = load_quiz_data(grade, category, subcategory)
        return list(data.keys())
    except (FileNotFoundError, ValueError):
        return [] 