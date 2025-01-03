document.addEventListener('DOMContentLoaded', function() {
    console.log('[Debug] DOM Content Loaded');
    
    // 問題データを取得
    const questionDataElement = document.getElementById('question-data');
    if (!questionDataElement) {
        console.error('[Debug] Question data element not found');
        return;
    }

    try {
        console.log('[Debug] Raw JSON content:', questionDataElement.textContent);
        const questionData = JSON.parse(questionDataElement.textContent);
        console.log('[Debug] Parsed question data:', questionData);

        // 正解のインデックスを保存
        const optionsContainer = document.querySelector('.options-container');
        if (optionsContainer) {
            const correctIndex = questionData.correct;
            optionsContainer.dataset.correct = correctIndex;
            console.log('[Debug] Correct index:', correctIndex);
        }

        // 初期の進捗状況を設定
        const currentQuestion = parseInt(document.getElementById('current_question').value);
        const totalQuestions = parseInt(document.getElementById('total_questions').value);
        console.log('[Debug] Initial progress setup:', {
            currentQuestion: currentQuestion,
            totalQuestions: totalQuestions
        });

        // 進捗状況を更新（0-basedのcurrentQuestionを使用）
        updateProgress(currentQuestion, totalQuestions);

        // 選択肢のイベントリスナーを設定
        setupOptionEventListeners();

        // クイズコンテナを表示
        const quizContainer = document.querySelector('.quiz-container');
        if (quizContainer) {
            setTimeout(() => {
                quizContainer.classList.add('show');
            }, 100);
        }
    } catch (error) {
        console.error('[Debug] Error initializing quiz:', error);
    }
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
    
    // 解説テキストの前に「解説:」を追加
    const explanationText = explanation || (isCorrect ? '正解です！' : '不正解です。');
    explanationDiv.textContent = `解説: ${explanationText}`;
    
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
    console.log('[Debug] updateProgress called with:', {
        currentQuestion: currentQuestion,
        totalQuestions: totalQuestions
    });

    // 最後の問題の場合は更新しない
    if (currentQuestion >= totalQuestions) {
        console.log('[Debug] Reached last question, skipping progress update');
        return;
    }

    // 1-basedの表示用の問題番号を計算（currentQuestionは0-based）
    const displayQuestion = currentQuestion + 1;
    console.log('[Debug] Display question number:', displayQuestion);

    // プログレスバーの更新
    const progressFill = document.querySelector('.progress-fill');
    if (progressFill) {
        const percentage = Math.min((displayQuestion / totalQuestions) * 100, 100);
        progressFill.style.width = `${percentage}%`;
        console.log('[Debug] Progress bar updated:', {
            percentage: percentage,
            width: progressFill.style.width
        });
    } else {
        console.warn('[Debug] Progress fill element not found');
    }

    // 問題番号の更新
    const questionCounter = document.querySelector('.question-counter');
    if (questionCounter) {
        const oldText = questionCounter.textContent;
        questionCounter.textContent = `問題 ${displayQuestion}/${totalQuestions}`;
        console.log('[Debug] Question counter updated:', {
            from: oldText,
            to: questionCounter.textContent,
            displayQuestion: displayQuestion,
            totalQuestions: totalQuestions
        });
    } else {
        console.warn('[Debug] Question counter element not found');
    }

    // 隠しフィールドの更新（0-basedの値を保存）
    const currentQuestionInput = document.getElementById('current_question');
    if (currentQuestionInput) {
        currentQuestionInput.value = currentQuestion;
        console.log('[Debug] Updated hidden current_question field:', {
            value: currentQuestion,
            displayValue: displayQuestion
        });
    }
}

// 問題表示を更新する関数
function updateQuestionDisplay(questionData) {
    console.log('[Debug] updateQuestionDisplay called with:', questionData);
    
    // 現在の問題番号を取得
    const currentQuestionInput = document.getElementById('current_question');
    const totalQuestionsInput = document.getElementById('total_questions');
    
    const currentQuestion = parseInt(currentQuestionInput.value);
    const totalQuestions = parseInt(totalQuestionsInput.value);
    
    console.log('[Debug] Question numbers:', {
        current: currentQuestion,
        total: totalQuestions
    });

    // 問題文を更新
    const questionElement = document.querySelector('.question-text');
    if (questionElement) {
        const oldText = questionElement.textContent;
        questionElement.textContent = questionData.question;
        console.log('[Debug] Question text updated:', {
            from: oldText,
            to: questionData.question
        });
    } else {
        console.warn('[Debug] Question text element not found');
    }

    // 選択肢を更新
    const optionsContainer = document.querySelector('.options-container');
    if (optionsContainer) {
        console.log('[Debug] Updating options container');
        optionsContainer.innerHTML = '';
        questionData.options.forEach((option, index) => {
            const button = document.createElement('div');
            button.className = 'option';
            button.textContent = option;
            button.dataset.index = index;
            button.dataset.value = option;
            optionsContainer.appendChild(button);
            console.log('[Debug] Added option:', {
                index: index,
                text: option
            });
        });

        // データ属性を更新
        optionsContainer.dataset.currentQuestion = currentQuestion;
        optionsContainer.dataset.totalQuestions = totalQuestions;
        
        // 進捗状況を更新
        updateProgress(currentQuestion, totalQuestions);
    } else {
        console.warn('[Debug] Options container not found');
    }

    // 説明文をクリア
    const explanationElement = document.querySelector('.explanation');
    if (explanationElement) {
        console.log('[Debug] Removing explanation element');
        explanationElement.remove();
    }

    // 選択肢のイベントリスナーを再設定
    console.log('[Debug] Setting up option event listeners');
    setupOptionEventListeners();
}

// 選択肢のイベントリスナーを設定する関数
function setupOptionEventListeners() {
    const options = document.querySelectorAll('.option');
    const optionsContainer = document.querySelector('.options-container');
    if (!optionsContainer) {
        console.error('[Debug] Options container not found');
        return;
    }
    
    const correctIndex = parseInt(optionsContainer.dataset.correct);
    console.log('[Debug] Setting up listeners with correct index:', correctIndex);

    options.forEach((option) => {
        option.addEventListener('click', async function() {
            if (option.classList.contains('selected') || option.classList.contains('disabled')) {
                console.log('[Debug] Option already selected or disabled');
                return;
            }

            // 他のオプションを無効化
            options.forEach(opt => opt.classList.add('disabled'));

            // 選択したオプションをマーク
            option.classList.add('selected');

            const index = parseInt(option.dataset.index);
            console.log('[Debug] Submitting answer:', {
                index: index,
                text: option.textContent.trim(),
                correctIndex: correctIndex
            });

            try {
                // サーバーに回答を送信
                const response = await fetch('/submit_answer', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        selected: index
                    }),
                    credentials: 'same-origin'
                });

                // レスポンスの詳細をログ出力
                console.log('[Debug] Response status:', response.status);
                console.log('[Debug] Response headers:', Object.fromEntries(response.headers.entries()));

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('[Debug] Error response:', errorText);
                    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
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

                // スコアの更新
                updateScore(responseData.currentScore, responseData.totalQuestions);

                // 最後の問題の場合
                if (responseData.isLastQuestion) {
                    console.log('[Debug] Last question completed');
                    setTimeout(() => {
                        window.location.href = responseData.redirectUrl;
                    }, 2000);
                } else {
                    // 次の問題データが含まれている場合、直接更新
                    if (responseData.nextQuestionData) {
                        // 進捗状況の更新は次の問題の表示後に行う
                        setTimeout(() => {
                            updateQuestionDisplay(responseData.nextQuestionData);
                            // 問題表示が完了してから進捗を更新
                            updateProgress(responseData.currentQuestion, responseData.totalQuestions);
                        }, 1500);
                    } else {
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    }
                }

            } catch (error) {
                console.error('[Debug] Error in submit_answer:', error);
                console.error('[Debug] Error stack:', error.stack);
                
                // エラーメッセージを表示
                showExplanation(false, 'エラーが発生しました。ページを更新してもう一度お試しください。');
                
                // 選択肢の無効化を解除
                options.forEach(opt => opt.classList.remove('disabled'));
                option.classList.remove('selected');
            }
        });
    });
}
