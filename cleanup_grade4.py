import os
import shutil

# 各教科の正しいサブカテゴリ
SUBJECT_SUBCATEGORIES = {
    'japanese': [
        'kanji',
        'reading_comprehension',
        'character_understanding',
        'paragraph_structure',
        'idioms',
        'letter_writing',
        'essay_writing'
    ],
    'math': [
        'large_numbers',
        'rounding',
        'decimals',
        'fractions',
        'angles',
        'area',
        'parallel_lines',
        'patterns',
        'line_graphs'
    ],
    'science': [
        'weather',
        'moon_stars',
        'electricity',
        'properties',
        'metals',
        'living_things',
        'seasonal_changes'
    ],
    'society': [
        'prefectures',
        'map_symbols',
        'local_geography',
        'water_resources',
        'environment',
        'disaster_prevention',
        'traditional_culture',
        'regional_industry'
    ]
}

def cleanup_subject_folders():
    base_path = 'quiz_data/grade_4'
    
    # 各教科フォルダをチェック
    for subject in SUBJECT_SUBCATEGORIES.keys():
        subject_path = os.path.join(base_path, subject)
        if not os.path.exists(subject_path):
            continue
            
        # フォルダ内の全サブカテゴリをチェック
        for item in os.listdir(subject_path):
            item_path = os.path.join(subject_path, item)
            if os.path.isdir(item_path):
                # このサブカテゴリがこの教科に属していない場合は削除
                if item not in SUBJECT_SUBCATEGORIES[subject]:
                    print(f"Removing {item_path}")
                    shutil.rmtree(item_path)

if __name__ == '__main__':
    cleanup_subject_folders() 