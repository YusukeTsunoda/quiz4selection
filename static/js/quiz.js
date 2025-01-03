document.addEventListener('DOMContentLoaded', function() {
    console.log('[Init] Quiz.js loaded and initialized');
    const optionsContainer = document.querySelector('.options-container');
    console.log('[Init] Options container:', optionsContainer);
    if (!optionsContainer) {
        console.error('[Init] Options container not found');
        return;
    }

    const progressFill = document.querySelector('.progress-fill');
    const scoreDisplay = document.querySelector('.score-display');
    let isAnswered = false;
    let totalQuestions = parseInt(optionsContainer.dataset.totalQuestions) || 10;
    console.log('[Init] Total questions:', totalQuestions);
    
    // 現在のスコアを取得
    let currentScore = scoreDisplay ? parseInt(scoreDisplay.textContent.match(/\d+/)[0]) || 0 : 0;
    console.log('[Init] Initial score:', currentScore);

    // wait関数の定義
    function wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // スコア表示を更新する関数
    function updateScoreDisplay(newScore) {
        console.log('[Score] Updating score display:', {
            oldScore: currentScore,
            newScore: newScore,
            totalQuestions: totalQuestions
        });
        
        if (scoreDisplay) {
            currentScore = newScore;
            scoreDisplay.textContent = `正解数: ${newScore}/${totalQuestions}`;
            console.log('[Score] Score display updated successfully');
        } else {
            console.error('[Score] Score display element not found');
        }
    }

    // 解説を表示する関数
    function showExplanation(isCorrect, explanationText) {
        console.log('[Explanation] Showing explanation:', {
            isCorrect: isCorrect,
            text: explanationText
        });

        const explanationDiv = document.createElement('div');
        explanationDiv.className = 'explanation mt-3 p-3 rounded';
        
        if (isCorrect) {
            explanationDiv.classList.add('correct-message');
            explanationDiv.innerHTML = `
                <h4 class="text-success mb-3">正解！</h4>
                <p class="mb-0">${explanationText}</p>
            `;
        } else {
            explanationDiv.classList.add('incorrect-message');
            explanationDiv.innerHTML = `
                <h4 class="text-danger mb-3">不正解</h4>
                <p class="mb-0">${explanationText}</p>
            `;
        }

        const existingExplanation = document.querySelector('.explanation');
        if (existingExplanation) {
            existingExplanation.remove();
        }

        optionsContainer.insertAdjacentElement('afterend', explanationDiv);
        console.log('[Explanation] Explanation div inserted');
    }

    async function submitAnswer(selectedIndex) {
        console.log('[Submit] Submitting answer:', selectedIndex);
        try {
            console.log('[Submit] Sending request to server...');
            const response = await fetch('/submit_answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ answer: selectedIndex })
            });
            
            if (!response.ok) {
                console.error('[Submit] Server returned error status:', response.status);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('[Submit] Server response:', data);
            return data;
        } catch (error) {
            console.error('[Submit] Error submitting answer:', error);
            return { success: false, error: error.message };
        }
    }

    async function handleOptionClick(event) {
        const clickedElement = event.target;
        console.log('[Click] Clicked element:', clickedElement);
        
        if (!clickedElement.classList.contains('option') || isAnswered) {
            console.log('[Click] Click ignored - not an option or already answered');
            return;
        }
        
        isAnswered = true;
        const selectedOption = clickedElement;
        const options = document.querySelectorAll('.option');
        
        try {
            const selectedIndex = parseInt(selectedOption.dataset.index);
            console.log('[Click] Selected index:', selectedIndex);
            
            options.forEach(option => option.classList.remove('selected'));
            selectedOption.classList.add('selected');
            
            console.log('[Submit] Before submitting answer');
            const response = await submitAnswer(selectedIndex);
            console.log('[Response] Full response object:', response);
            
            if (response.success) {
                console.log('[Feedback] Starting answer feedback display');
                
                if (response.isCorrect) {
                    selectedOption.classList.add('correct');
                    updateScoreDisplay(response.currentScore);
                } else {
                    selectedOption.classList.add('incorrect');
                    const correctIndex = parseInt(optionsContainer.dataset.correct);
                    console.log('[Debug] Correct index:', correctIndex);
                    if (options[correctIndex]) {
                        options[correctIndex].classList.add('correct');
                    }
                }

                // 解説の表示
                try {
                    const rawQuestionData = optionsContainer.dataset.questionData;
                    console.log('[Debug] Raw question data:', rawQuestionData);
                    
                    let explanationText = '解説がありません';
                    
                    if (rawQuestionData && typeof rawQuestionData === 'string') {
                        try {
                            // Python形式の文字列をJavaScript形式に変換
                            const jsonString = rawQuestionData
                                .replace(/'/g, '"')  // シングルクォートをダブルクォートに変換
                                .replace(/None/g, 'null')  // PythonのNoneをnullに変換
                                .replace(/True/g, 'true')  // PythonのTrueをtrueに変換
                                .replace(/False/g, 'false');  // PythonのFalseをfalseに変換
                            
                            console.log('[Debug] Converted JSON string:', jsonString);
                            
                            // JSONデータをパース
                            const questionData = JSON.parse(jsonString);
                            console.log('[Debug] Parsed question data:', questionData);
                            
                            // 解説テキストを取得
                            if (questionData && typeof questionData === 'object') {
                                explanationText = questionData.explanation || '解説がありません';
                                console.log('[Debug] Found explanation:', explanationText);
                            } else {
                                console.log('[Debug] Question data is not an object:', typeof questionData);
                            }
                        } catch (parseError) {
                            console.error('[Debug] JSON parse error:', parseError);
                            console.error('[Debug] Raw data causing error:', rawQuestionData);
                        }
                    } else {
                        console.log('[Debug] Invalid or missing question data');
                    }
                    
                    showExplanation(response.isCorrect, explanationText);

                } catch (error) {
                    console.error('[Debug] Error in explanation handling:', error);
                    console.error('[Debug] Error details:', error.message);
                    showExplanation(response.isCorrect, '解説の読み込みに失敗しました');
                }

                await wait(2500);
                
                const quizContainer = document.querySelector('.quiz-container');
                if (quizContainer) {
                    quizContainer.classList.add('fade');
                    await wait(100);
                    
                    if (response.isLastQuestion) {
                        window.location.href = '/result';
                    } else {
                        window.location.href = '/next_question';
                    }
                }
            } else {
                console.error('[Error] Server response indicates failure:', response.error);
                isAnswered = false;
            }
        } catch (error) {
            console.error('[Error] Critical error in click handler:', error);
            console.error('[Error] Stack trace:', error.stack);
            isAnswered = false;
        }
    }

    // イベントリスナーの設定
    const options = document.querySelectorAll('.option');
    options.forEach(option => {
        option.addEventListener('click', handleOptionClick);
    });

    // 初期表示時にフェードインアニメーション
    const quizContainer = document.querySelector('.quiz-container');
    if (quizContainer) {
        setTimeout(() => {
            quizContainer.classList.add('show');
        }, 100);
    }
});
