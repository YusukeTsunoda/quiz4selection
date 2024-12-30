import os
import json

def load_questions_by_category():
    questions = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for grade_dir in os.listdir(base_dir):
        if not grade_dir.startswith('grade_'):
            continue
            
        grade = int(grade_dir.split('_')[1])
        grade_path = os.path.join(base_dir, grade_dir)
        questions[grade] = {}
        
        for category_file in os.listdir(grade_path):
            if not category_file.endswith('.json'):
                continue
                
            category = category_file[:-5]  # Remove .json extension
            file_path = os.path.join(grade_path, category_file)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                questions[grade][category] = json.load(f)
    
    return questions

questions_by_category = load_questions_by_category() 