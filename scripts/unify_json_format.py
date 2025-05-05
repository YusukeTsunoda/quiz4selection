#!/usr/bin/env python3
"""
JSONデータフォーマット統一スクリプト

quiz_data ディレクトリ内の全ての questions.json ファイルを確認し、
キー名を統一するスクリプトです。

統一するキー名:
- question: 問題文（文字列）
- options: 選択肢の配列（文字列の配列）
- correct_answer_index: 正解の選択肢のインデックス（数値、0始まり）
- explanation: 解説文（文字列、任意）
- hint: ヒント（文字列、任意）

使用方法:
python unify_json_format.py

注意:
- 実行前にデータのバックアップを取ることを強く推奨します
- 空のJSONファイル([])はそのまま維持されます
"""

import os
import json
import logging
from pathlib import Path

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unify_json_format.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# キー名のマッピング
KEY_MAPPING = {
    # 現在のキー名: 新しいキー名
    'question': 'question',
    'options': 'options',
    'correct_answer_index': 'correct_answer_index',
    'correct': 'correct_answer_index',  # 古いキー名がある場合
    'correct_index': 'correct_answer_index',  # 古いキー名がある場合
    'explanation': 'explanation',
    'hint': 'hint'
}

# 必須キー
REQUIRED_KEYS = ['question', 'options', 'correct_answer_index']

# 任意キー
OPTIONAL_KEYS = ['explanation', 'hint']

def unify_json_format(json_file_path):
    """
    指定されたJSONファイルのフォーマットを統一する
    
    Args:
        json_file_path: JSONファイルのパス
        
    Returns:
        bool: 変更があったかどうか
    """
    try:
        # JSONファイルを読み込む
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 空のJSONファイルはスキップ
        if not data:
            logger.info(f"空のJSONファイルをスキップ: {json_file_path}")
            return False
            
        modified = False
        
        # 各問題のキー名を統一
        for i, question_data in enumerate(data):
            new_question_data = {}
            
            # キー名のマッピングに従って変換
            for old_key, value in question_data.items():
                if old_key in KEY_MAPPING:
                    new_key = KEY_MAPPING[old_key]
                    new_question_data[new_key] = value
                    if old_key != new_key:
                        modified = True
                        logger.debug(f"キー名を変更: {old_key} -> {new_key}")
                else:
                    # マッピングにないキーはそのまま維持
                    new_question_data[old_key] = value
            
            # 必須キーの存在確認
            for key in REQUIRED_KEYS:
                if key not in new_question_data:
                    logger.warning(f"必須キー '{key}' が問題 {i+1} に存在しません: {json_file_path}")
            
            # データを更新
            data[i] = new_question_data
        
        # 変更があった場合のみファイルを上書き
        if modified:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"JSONフォーマットを統一しました: {json_file_path}")
            return True
        else:
            logger.info(f"変更なし: {json_file_path}")
            return False
            
    except json.JSONDecodeError as e:
        logger.error(f"JSONの解析エラー: {json_file_path} - {e}")
        return False
    except Exception as e:
        logger.error(f"予期せぬエラー: {json_file_path} - {e}")
        return False

def process_all_json_files(base_dir):
    """
    指定されたディレクトリ以下の全てのquestions.jsonファイルを処理する
    
    Args:
        base_dir: 基準ディレクトリ
        
    Returns:
        tuple: (処理したファイル数, 変更したファイル数)
    """
    processed_count = 0
    modified_count = 0
    
    # 全てのquestions.jsonファイルを再帰的に検索
    for json_file in Path(base_dir).glob('**/questions.json'):
        processed_count += 1
        if unify_json_format(str(json_file)):
            modified_count += 1
    
    return processed_count, modified_count

def main():
    """メイン関数"""
    logger.info("JSONデータフォーマット統一スクリプトを開始します")
    
    # スクリプトのディレクトリを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # quiz_dataディレクトリのパスを構築
    quiz_data_dir = os.path.join(os.path.dirname(script_dir), 'quiz_data')
    
    if not os.path.exists(quiz_data_dir):
        logger.error(f"quiz_dataディレクトリが見つかりません: {quiz_data_dir}")
        return
    
    logger.info(f"quiz_dataディレクトリを処理します: {quiz_data_dir}")
    
    # 全てのJSONファイルを処理
    processed_count, modified_count = process_all_json_files(quiz_data_dir)
    
    logger.info(f"処理完了: {processed_count}ファイルを処理し、{modified_count}ファイルを変更しました")

if __name__ == "__main__":
    main()
