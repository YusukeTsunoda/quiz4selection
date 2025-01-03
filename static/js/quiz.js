document.addEventListener('DOMContentLoaded', function() {
    // 問題データの取得と解析
    const questionDataElement = document.getElementById('question-data');
    if (!questionDataElement) {
        console.error('[Debug] Question data element not found');
        return;
    }

    // クイズコンテナを表示
    const quizContainer = document.querySelector('.quiz-container');
    if (quizContainer) {
        quizContainer.classList.add('show');
    }

    const jsonContent = questionDataElement.textContent.trim();
    console.log('[Debug] Raw JSON content:', jsonContent);

    let questionData;
    try {
        questionData = JSON.parse(jsonContent);
        console.log('[Debug] Parsed question data:', questionData);
    } catch (e) {
        console.error('[Debug] Error parsing question data:', e);
        return;
    }

    // 問題データの検証
    if (!questionData || !questionData.options || !Array.isArray(questionData.options)) {
        console.error('[Debug] Invalid question data structure:', questionData);
        return;
    }

    // 正解のインデックスを取得
    const correctIndex = parseInt(questionData.correct);
    console.log('[Debug] Correct index:', correctIndex);

    // オプションコンテナの設定
    const optionsContainer = document.querySelector('.options-container');
    if (!optionsContainer) {
        console.error('[Debug] Options container not found');
        return;
    }

    // データ属性の設定
    optionsContainer.dataset.correct = correctIndex;
    const currentQuestion = parseInt(optionsContainer.dataset.currentQuestion) || 1;
    const totalQuestions = parseInt(optionsContainer.dataset.totalQuestions) || 10;
    console.log('[Debug] Initial progress setup:', { currentQuestion, totalQuestions });

    // 進捗状況の初期設定
    updateProgress(currentQuestion, totalQuestions);

    // クリック処理の設定
    const options = document.querySelectorAll('.option');
    options.forEach((option, index) => {
        option.addEventListener('click', async function() {
            if (option.classList.contains('selected') || option.classList.contains('disabled')) {
                console.log('[Debug] Option already selected or disabled');
                return;
            }

            console.log('[Debug] Option clicked:', {
                index: index,
                text: option.textContent.trim(),
                correctIndex: correctIndex
            });

            // 他のオプションを無効化
            options.forEach(opt => opt.classList.add('disabled'));

            // 選択したオプションをマーク
            option.classList.add('selected');

            try {
                // サーバーに回答を送信
                const response = await fetch('/submit_answer', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        selected: index
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const responseData = await response.json();
                console.log('[Debug] Server response:', responseData);

                if (!responseData.success) {
                    console.error('[Debug] Server error:', responseData.error);
                    return;
                }

                // 正解・不正解の表示
                if (responseData.isCorrect) {
                    option.classList.add('correct');
                    console.log('[Debug] Correct answer selected');
                    showExplanation(true, responseData.questionData.explanation);
                } else {
                    option.classList.add('incorrect');
                    const correctOption = options[correctIndex];
                    if (correctOption) {
                        correctOption.classList.add('correct');
                        console.log('[Debug] Showing correct answer:', correctIndex);
                    }
                    showExplanation(false, responseData.questionData.explanation);
                }

                // スコアと進捗状況の更新
                updateScore(responseData.currentScore, responseData.totalQuestions);
                updateProgress(responseData.currentQuestion, responseData.totalQuestions);

                // 最後の問題の場合
                if (responseData.isLastQuestion) {
                    console.log('[Debug] Last question completed');
                    setTimeout(() => {
                        window.location.href = responseData.redirectUrl;
                    }, 2000);
                } else {
                    // 次の問題データが含まれている場合、直接更新
                    if (responseData.nextQuestionData) {
                        setTimeout(() => {
                            updateQuestionDisplay(responseData.nextQuestionData);
                        }, 1500);
                    } else {
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    }
                }

            } catch (error) {
                console.error('[Debug] Error submitting answer:', error);
            }
        });
    });
});

// 解説を表示する関数
function showExplanation(isCorrect, explanation) {
    const questionContainer = document.querySelector('.question-container');
    if (!questionContainer) return;

    console.log('[Debug] Showing explanation:', explanation);

    const existingExplanation = document.querySelector('.explanation');
    if (existingExplanation) {
        existingExplanation.remove();
    }

    const explanationDiv = document.createElement('div');
    explanationDiv.className = `explanation ${isCorrect ? 'correct-message' : 'incorrect-message'}`;
    explanationDiv.textContent = explanation || (isCorrect ? '正解です！' : '不正解です。');
    questionContainer.appendChild(explanationDiv);
}

// スコアを更新する関数
function updateScore(currentScore, totalQuestions) {
    const scoreDisplay = document.querySelector('.score-display');
    if (scoreDisplay) {
        scoreDisplay.textContent = `正解数: ${currentScore}/${totalQuestions}`;
        console.log('[Debug] Score updated:', currentScore);
    }
}

// 進捗状況を更新する関数
function updateProgress(currentQuestion, totalQuestions) {
    console.log('[Debug] Updating progress:', { currentQuestion, totalQuestions });
    
    // 問題番号の更新
    const questionCounter = document.querySelector('.question-counter');
    if (questionCounter) {
        questionCounter.textContent = `問題 ${currentQuestion}/${totalQuestions}`;
        console.log('[Debug] Question counter updated:', questionCounter.textContent);
    }

    // プログレスバーの更新
    const progressFill = document.querySelector('.progress-fill');
    if (progressFill) {
        const percentage = (currentQuestion / totalQuestions) * 100;
        progressFill.style.width = `${percentage}%`;
        console.log('[Debug] Progress bar updated:', percentage + '%');
    }

    // データ属性の更新
    const optionsContainer = document.querySelector('.options-container');
    if (optionsContainer) {
        optionsContainer.dataset.currentQuestion = currentQuestion;
    }
}

// 問題表示を更新する関数
function updateQuestionDisplay(questionData) {
    console.log('[Debug] Updating question display:', questionData);

    // 問題文の更新
    const questionText = document.querySelector('.question-text');
    if (questionText) {
        questionText.textContent = questionData.question;
    }

    // 選択肢の更新
    const optionsContainer = document.querySelector('.options-container');
    if (optionsContainer) {
        // 既存の選択肢をクリア
        optionsContainer.innerHTML = '';
        
        // データ属性を更新
        optionsContainer.dataset.correct = questionData.correct;

        // 新しい選択肢を追加
        questionData.options.forEach((optionText, index) => {
            const option = document.createElement('button');
            option.className = 'option';
            option.textContent = optionText;
            
            // クリックイベントの設定
            option.addEventListener('click', async function() {
                if (option.classList.contains('selected') || option.classList.contains('disabled')) {
                    return;
                }

                // 他のオプションを無効化
                const allOptions = optionsContainer.querySelectorAll('.option');
                allOptions.forEach(opt => opt.classList.add('disabled'));

                // 選択したオプションをマーク
                option.classList.add('selected');

                try {
                    const response = await fetch('/submit_answer', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            selected: index
                        })
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const responseData = await response.json();
                    if (!responseData.success) {
                        console.error('[Debug] Server error:', responseData.error);
                        return;
                    }

                    // 正解・不正解の表示
                    if (responseData.isCorrect) {
                        option.classList.add('correct');
                        showExplanation(true, responseData.questionData.explanation);
                    } else {
                        option.classList.add('incorrect');
                        const correctOption = allOptions[questionData.correct];
                        if (correctOption) {
                            correctOption.classList.add('correct');
                        }
                        showExplanation(false, responseData.questionData.explanation);
                    }

                    // スコアと進捗状況の更新
                    updateScore(responseData.currentScore, responseData.totalQuestions);
                    updateProgress(responseData.currentQuestion, responseData.totalQuestions);

                    // 最後の問題の場合
                    if (responseData.isLastQuestion) {
                        setTimeout(() => {
                            window.location.href = responseData.redirectUrl;
                        }, 2000);
                    } else if (responseData.nextQuestionData) {
                        setTimeout(() => {
                            updateQuestionDisplay(responseData.nextQuestionData);
                        }, 1500);
                    }

                } catch (error) {
                    console.error('[Debug] Error submitting answer:', error);
                }
            });

            optionsContainer.appendChild(option);
        });
    }

    // 問題データ要素の更新
    const questionDataElement = document.getElementById('question-data');
    if (questionDataElement) {
        questionDataElement.textContent = JSON.stringify(questionData);
    }
}
