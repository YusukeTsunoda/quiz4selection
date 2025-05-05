#!/usr/bin/env python3
# scripts/rename_json_keys.py
# JSONファイル内のキー "correct" を "correct_answer_index" にリネーム

import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

QUIZ_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'quiz_data')

def rename_json_keys():
    """
    quiz_dataディレクトリ内のすべてのJSONファイルをスキャンし、
    'correct'キーを'correct_answer_index'に変更します。
    """
    total_files = 0
    modified_files = 0
    
    logger.info(f"スキャン開始: {QUIZ_DATA_DIR}")
    
    for root, dirs, files in os.walk(QUIZ_DATA_DIR):
        for fname in files:
            if not fname.endswith('.json'):
                continue
                
            total_files += 1
            path = os.path.join(root, fname)
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                logger.error(f"ファイル読み込みエラー {path}: {e}")
                continue
                
            changed = False
            # データがリストの場合
            if isinstance(data, list):
                for q in data:
                    if 'correct' in q:
                        q['correct_answer_index'] = q.pop('correct')
                        changed = True
                        
            # JSON書き込み
            if changed:
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    logger.info(f"更新完了: {path}")
                    modified_files += 1
                except Exception as e:
                    logger.error(f"ファイル書き込みエラー {path}: {e}")
    
    logger.info(f"処理完了: 合計{total_files}ファイル中、{modified_files}ファイルを更新しました")
    return total_files, modified_files

if __name__ == "__main__":
    rename_json_keys()
