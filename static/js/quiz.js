document.addEventListener('DOMContentLoaded', function() {
    const optionsContainer = document.querySelector('.options-container');
    console.log('Options container:', optionsContainer);
    if (!optionsContainer) return;

    const progressFill = document.querySelector('.progress-fill');
    const scoreDisplay = document.querySelector('.score-display');
    let isAnswered = false;

    async function submitAnswer(selectedIndex) {
        console.log('Submitting answer:', selectedIndex);
        try {
            const response = await fetch('/submit_answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ answer: selectedIndex })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Server response:', data);
            return data;
        } catch (error) {
            console.error('Error submitting answer:', error);
            return { success: false, error: error.message };
        }
    }

    async function handleOptionClick(event) {
        const clickedElement = event.target;
        console.log('Clicked element:', clickedElement);
        
        if (!clickedElement.classList.contains('option') || isAnswered) {
            console.log('Click ignored - not an option or already answered');
            return;
        }
        
        isAnswered = true;
        const selectedOption = clickedElement;
        const options = document.querySelectorAll('.option');
        
        try {
            const selectedIndex = parseInt(selectedOption.dataset.index);
            console.log('Selected index:', selectedIndex);
            
            options.forEach(option => option.classList.remove('selected'));
            selectedOption.classList.add('selected');
            
            const response = await submitAnswer(selectedIndex);
            console.log('Submit response:', response);
            
            if (response.success) {
                // 正解・不正解の表示
                if (response.isCorrect) {
                    selectedOption.classList.add('correct');
                    scoreDisplay.textContent = `スコア: ${response.currentScore}問`;
                } else {
                    selectedOption.classList.add('incorrect');
                    // 正解の選択肢を取得して緑色で表示
                    const correctIndex = optionsContainer.dataset.correct;
                    if (options[correctIndex]) {
                        options[correctIndex].classList.add('correct');
                    }
                }
                
                // 解説文の表示（不正解の場合は必ず表示）
                try {
                    const questionData = JSON.parse(optionsContainer.dataset.questionData);
                    console.log('Question data for explanation:', questionData);
                    
                    // 不正解の場合、または解説がある場合に表示
                    if (!response.isCorrect || (questionData && questionData.explanation)) {
                        const explanationDiv = document.createElement('div');
                        explanationDiv.className = 'explanation mt-3 p-3 rounded';
                        
                        // 正解・不正解に応じて異なるスタイルとメッセージを表示
                        if (response.isCorrect) {
                            explanationDiv.classList.add('correct-message');
                            explanationDiv.innerHTML = `
                                <h4 class="text-success mb-3">正解！</h4>
                                <p class="mb-0">${questionData.explanation}</p>
                            `;
                        } else {
                            explanationDiv.classList.add('incorrect-message');
                            explanationDiv.innerHTML = `
                                <h4 class="text-danger mb-3">不正解</h4>
                                <p class="mb-0">${questionData.explanation || '正しい答えを確認してください。'}</p>
                            `;
                        }
                        
                        // 既存の解説があれば削除
                        const existingExplanation = document.querySelector('.explanation');
                        if (existingExplanation) {
                            existingExplanation.remove();
                        }
                        
                        // 新しい解説を追加
                        optionsContainer.insertAdjacentElement('afterend', explanationDiv);
                    }
                    
                    // 解説を表示してから遷移処理を実行
                    setTimeout(async () => {
                        const quizContainer = document.querySelector('.quiz-container');
                        if (quizContainer) {
                            quizContainer.classList.add('fade');
                            
                            // 確実に遷移処理を実行
                            setTimeout(() => {
                                try {
                                    if (response.isLastQuestion && response.redirectUrl) {
                                        console.log('Quiz completed, redirecting to:', response.redirectUrl);
                                        window.location.replace(response.redirectUrl);
                                    } else {
                                        console.log('Moving to next question');
                                        window.location.replace('/next_question');
                                    }
                                } catch (error) {
                                    console.error('Redirect error:', error);
                                    // フォールバック：直接URLに遷移
                                    if (response.isLastQuestion) {
                                        window.location.href = '/result';
                                    } else {
                                        window.location.href = '/next_question';
                                    }
                                }
                            }, 500);
                        }
                    }, 3000);
                } catch (error) {
                    console.error('Error handling explanation:', error);
                    // エラー時は即座に遷移
                    if (response.isLastQuestion && response.redirectUrl) {
                        window.location.replace(response.redirectUrl);
                    } else {
                        window.location.replace('/next_question');
                    }
                }
            } else {
                console.error('Server returned error:', response.error);
                isAnswered = false;
            }
        } catch (error) {
            console.error('Error in click handler:', error);
            console.error('Error details:', error.stack);
            isAnswered = false;
        }
    }

    optionsContainer.addEventListener('click', handleOptionClick);
    
    // 初期表示時のフェードイン
    const quizContainer = document.querySelector('.quiz-container');
    if (quizContainer) {
        quizContainer.classList.add('show');
    }
});
