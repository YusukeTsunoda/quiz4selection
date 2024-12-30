import os
import json

def load_questions():
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
            
        # 各カテゴリのJSONファイルを読み込む
        for category_file in os.listdir(grade_path):
            if not category_file.endswith('.json'):
                continue
                
            category = category_file[:-5]  # .jsonを除去
            file_path = os.path.join(grade_path, category_file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if grade not in questions_by_category:
                        questions_by_category[grade] = {}
                    questions_by_category[grade][category] = data
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
                
    return questions_by_category

questions_by_category = load_questions()
