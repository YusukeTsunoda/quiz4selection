document.addEventListener('DOMContentLoaded', function() {
    console.log('Quiz.js loaded and initialized'); // 初期化確認用ログ
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
                console.log('Starting answer feedback display'); // 表示開始ログ
                // 正解・不正解の表示
                if (response.isCorrect) {
                    selectedOption.classList.add('correct');
                    scoreDisplay.textContent = `スコア: ${response.currentScore}問`;
                    console.log('Showing correct answer feedback');
                } else {
                    selectedOption.classList.add('incorrect');
                    // 正解の選択肢を取得して緑色で表示
                    const correctIndex = optionsContainer.dataset.correct;
                    if (options[correctIndex]) {
                        options[correctIndex].classList.add('correct');
                    }
                    console.log('Showing incorrect answer feedback');
                }

                // 表示時間の処理を Promise でラップ
                const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

                try {
                    // データセットから問題データを取得
                    const rawQuestionData = optionsContainer.dataset.questionData;
                    console.log('Raw question data:', rawQuestionData);
                    
                    // JSONデータをパース（エラーハンドリング付き）
                    let questionData = null;
                    try {
                        questionData = JSON.parse(rawQuestionData.replace(/^"/, '').replace(/"$/, ''));
                        console.log('Parsed question data:', questionData);
                    } catch (parseError) {
                        console.error('JSON parse error:', parseError);
                    }
                    
                    // 解説の表示（questionDataが正しくパースできた場合のみ）
                    if (questionData && (!response.isCorrect || questionData.explanation)) {
                        const explanationDiv = document.createElement('div');
                        explanationDiv.className = 'explanation mt-3 p-3 rounded';
                        
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
                        
                        const existingExplanation = document.querySelector('.explanation');
                        if (existingExplanation) {
                            existingExplanation.remove();
                        }
                        
                        optionsContainer.insertAdjacentElement('afterend', explanationDiv);
                        console.log('Explanation added to DOM');
                    }

                } catch (error) {
                    console.error('Error handling explanation:', error);
                    console.error('Error details:', error.stack);
                }

                // 解説の表示有無に関わらず、1.5秒の表示時間を確保
                console.log('Starting display timer (1.5s)');
                const displayStartTime = Date.now();
                
                await wait(1500);
                
                const actualDisplayDuration = Date.now() - displayStartTime;
                console.log(`Actual display duration: ${actualDisplayDuration}ms`);
                
                // フェードアウトと遷移
                console.log('Starting transition');
                const quizContainer = document.querySelector('.quiz-container');
                if (quizContainer) {
                    quizContainer.classList.add('fade');
                    
                    // フェードアウト完了を待機
                    await wait(100);
                    
                    console.log('Fade out complete, redirecting...');
                    
                    if (response.isLastQuestion) {
                        console.log('Quiz completed, redirecting to result page');
                        window.location.href = '/result';
                    } else {
                        console.log('Moving to next question');
                        window.location.href = '/next_question';
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
        console.log('Quiz container shown');
    }
});
