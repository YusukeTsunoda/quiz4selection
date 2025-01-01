#!/bin/bash

# ベースディレクトリの設定
BASE_DIR="quiz_data"

# 教科リスト
SUBJECTS=("japanese" "math" "science" "society")
# 難易度リスト
DIFFICULTIES=("easy" "medium" "hard")

# 学年のループ
for GRADE in 5 6; do
    # 各教科のディレクトリをループ
    for SUBJECT in "${SUBJECTS[@]}"; do
        # 各教科のサブディレクトリを取得
        SUBCATEGORIES=$(ls "$BASE_DIR/grade_$GRADE/$SUBJECT/")
        
        for SUBCAT in $SUBCATEGORIES; do
            # 各難易度のディレクトリを作成し、空のJSONファイルを作成
            for DIFFICULTY in "${DIFFICULTIES[@]}"; do
                TARGET_DIR="$BASE_DIR/grade_$GRADE/$SUBJECT/$SUBCAT/$DIFFICULTY"
                mkdir -p "$TARGET_DIR"
                
                # 空の問題配列を持つJSONファイルの作成
                cat > "$TARGET_DIR/questions.json" << EOF
{
  "questions": [],
  "metadata": {
    "grade": $GRADE,
    "subject": "$SUBJECT",
    "category": "$SUBCAT",
    "difficulty": "$DIFFICULTY",
    "total_questions": 0
  }
}
EOF
                
                echo "Created: $TARGET_DIR/questions.json"
            done
        done
    done
done

echo "Quiz files generation completed!" 