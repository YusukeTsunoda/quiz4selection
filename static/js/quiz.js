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

    const jsonContent = questionDataElement.textContent;
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
    optionsContainer.dataset.correct = correctIndex;

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
                text: option.textContent,
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
                    // 正解の解説を表示
                    showExplanation(true, questionData.explanation);
                } else {
                    option.classList.add('incorrect');
                    // 正解のオプションを緑で表示
                    const correctOption = options[correctIndex];
                    if (correctOption) {
                        correctOption.classList.add('correct');
                        console.log('[Debug] Showing correct answer:', correctIndex);
                    } else {
                        console.error('[Debug] Correct option not found:', correctIndex);
                    }
                    // 不正解の解説を表示
                    showExplanation(false, questionData.explanation);
                }

                // スコアの更新
                const scoreDisplay = document.querySelector('.score-display');
                if (scoreDisplay) {
                    scoreDisplay.textContent = `正解数: ${responseData.currentScore}/${responseData.totalQuestions}`;
                }

                // 最後の問題の場合
                if (responseData.isLastQuestion) {
                    console.log('[Debug] Last question completed');
                    setTimeout(() => {
                        window.location.href = '/result';
                    }, 2000);
                } else {
                    // 次の問題への遷移
                    setTimeout(() => {
                        const quizContainer = document.querySelector('.quiz-container');
                        if (quizContainer) {
                            quizContainer.classList.add('fade');
                            setTimeout(() => {
                                window.location.reload();
                            }, 500);
                        }
                    }, 2000);
                }

            } catch (error) {
                console.error('[Debug] Error submitting answer:', error);
            }
        });
    });

    // 解説を表示する関数
    function showExplanation(isCorrect, explanation) {
        const questionContainer = document.querySelector('.question-container');
        if (!questionContainer) return;

        const existingExplanation = document.querySelector('.explanation');
        if (existingExplanation) {
            existingExplanation.remove();
        }

        const explanationDiv = document.createElement('div');
        explanationDiv.className = `explanation ${isCorrect ? 'correct-message' : 'incorrect-message'}`;
        explanationDiv.textContent = explanation || (isCorrect ? '正解です！' : '不正解です。');
        questionContainer.appendChild(explanationDiv);
    }
});
