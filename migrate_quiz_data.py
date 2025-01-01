import os
import json
import shutil
from pathlib import Path

# 定数定義
GRADES = range(1, 7)
CATEGORIES = ['japanese', 'math', 'science', 'society']
DIFFICULTIES = ['easy', 'medium', 'hard']

def create_folder_structure():
    """新しいフォルダ構造を作成"""
    base_dir = Path('quiz_data')
    
    # 既存のquiz_dataフォルダをバックアップ
    if base_dir.exists():
        shutil.copytree(base_dir, base_dir.with_name('quiz_data_backup'))
    
    # 各階層のフォルダを作成
    for grade in GRADES:
        grade_dir = base_dir / f'grade_{grade}'
        for category in CATEGORIES:
            category_dir = grade_dir / category
            
            # 学年とカテゴリに応じたサブカテゴリを取得
            subcategories = get_subcategories(grade, category)
            
            for subcategory in subcategories:
                subcategory_dir = category_dir / subcategory
                for difficulty in DIFFICULTIES:
                    difficulty_dir = subcategory_dir / difficulty
                    difficulty_dir.mkdir(parents=True, exist_ok=True)

def get_subcategories(grade, category):
    """学年とカテゴリに応じたサブカテゴリを取得"""
    GRADE_CATEGORIES = {
        1: {
            'japanese': ['kanji', 'reading', 'writing'],
            'math': ['calculation', 'figure'],
            'science': [],
            'society': []
        },
        2: {
            'japanese': ['kanji', 'reading', 'writing', 'grammar'],
            'math': ['calculation', 'figure', 'measurement'],
            'science': [],
            'society': []
        },
        3: {
            'japanese': ['kanji', 'reading', 'writing', 'grammar'],
            'math': ['calculation', 'figure', 'measurement', 'graph'],
            'science': ['physics', 'biology'],
            'society': ['geography', 'prefectures']
        },
        4: {
            'japanese': ['kanji', 'reading', 'writing', 'grammar'],
            'math': ['calculation', 'figure', 'measurement', 'graph'],
            'science': ['physics', 'chemistry', 'biology'],
            'society': ['geography', 'history', 'prefectures']
        },
        5: {
            'japanese': ['kanji', 'reading', 'writing', 'grammar', 'hyakuninishu'],
            'math': ['calculation', 'figure', 'measurement', 'graph'],
            'science': ['physics', 'chemistry', 'biology', 'earth_science'],
            'society': ['geography', 'history', 'civics', 'current_events', 'prefectures']
        },
        6: {
            'japanese': ['kanji', 'reading', 'writing', 'grammar', 'hyakuninishu'],
            'math': ['calculation', 'figure', 'measurement', 'graph'],
            'science': ['physics', 'chemistry', 'biology', 'earth_science'],
            'society': ['geography', 'history', 'civics', 'current_events', 'prefectures']
        }
    }
    return GRADE_CATEGORIES.get(grade, {}).get(category, [])

def migrate_quiz_data():
    """既存の問題データを新しい構造に移行"""
    base_dir = Path('quiz_data')
    
    # 各学年のフォルダをチェック
    for grade in GRADES:
        grade_dir = base_dir / f'grade_{grade}'
        if not grade_dir.exists():
            continue
        
        # 各カテゴリのJSONファイルを処理
        for category in CATEGORIES:
            json_file = grade_dir / f'{category}.json'
            if not json_file.exists():
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 各サブカテゴリの問題を新しい場所に移動
                for subcategory, subcategory_data in data.items():
                    for difficulty, questions in subcategory_data.items():
                        # 新しいファイルパスを作成
                        new_dir = grade_dir / category / subcategory / difficulty
                        new_file = new_dir / 'questions.json'
                        
                        # ディレクトリが存在することを確認
                        new_dir.mkdir(parents=True, exist_ok=True)
                        
                        # 問題データを保存
                        with open(new_file, 'w', encoding='utf-8') as f:
                            json.dump(questions, f, ensure_ascii=False, indent=2)
                
                # 元のJSONファイルを削除
                json_file.unlink()
                
            except Exception as e:
                print(f"Error processing {json_file}: {e}")

if __name__ == '__main__':
    print("Creating new folder structure...")
    create_folder_structure()
    
    print("Migrating quiz data...")
    migrate_quiz_data()
    
    print("Migration completed!") 