document.addEventListener('DOMContentLoaded', function() {
    const optionsContainer = document.querySelector('.options-container');
    if (!optionsContainer) {
        console.error('Options container not found');
        return;
    }

    const progressFill = document.querySelector('.progress-fill');
    const scoreDisplay = document.querySelector('.score-display');
    let isAnswered = false;
    let totalQuestions = parseInt(optionsContainer.dataset.totalQuestions) || 10;
    let currentScore = scoreDisplay ? parseInt(scoreDisplay.textContent.match(/\d+/)[0]) || 0 : 0;

    function wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function updateScoreDisplay(newScore) {
        if (scoreDisplay) {
            currentScore = newScore;
            scoreDisplay.textContent = `正解数: ${newScore}/${totalQuestions}`;
        }
    }

    function showExplanation(isCorrect, explanationText) {
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
    }

    async function submitAnswer(selectedIndex) {
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
            
            return await response.json();
        } catch (error) {
            console.error('Error submitting answer:', error);
            return { success: false, error: error.message };
        }
    }

    async function handleOptionClick(event) {
        const clickedElement = event.target;
        
        if (!clickedElement.classList.contains('option') || isAnswered) {
            return;
        }
        
        isAnswered = true;
        const selectedOption = clickedElement;
        const options = document.querySelectorAll('.option');
        
        try {
            const selectedIndex = parseInt(selectedOption.dataset.index);
            const response = await submitAnswer(selectedIndex);
            
            if (response.success) {
                if (response.isCorrect) {
                    selectedOption.classList.add('correct');
                    updateScoreDisplay(response.currentScore);
                } else {
                    selectedOption.classList.add('incorrect');
                    const correctIndex = parseInt(optionsContainer.dataset.correct);
                    if (options[correctIndex]) {
                        options[correctIndex].classList.add('correct');
                    }
                }

                // 解説の表示
                try {
                    // デバッグ用のJSONデータを取得
                    const debugDataElement = document.getElementById('debug-data');
                    if (!debugDataElement) {
                        throw new Error('Debug data element not found');
                    }

                    const jsonContent = debugDataElement.textContent.trim();
                    if (!jsonContent) {
                        throw new Error('Empty JSON content');
                    }

                    const questionData = JSON.parse(jsonContent);
                    const explanationText = questionData.explanation || '解説がありません';
                    showExplanation(response.isCorrect, explanationText);
                } catch (error) {
                    console.error('Error handling explanation:', error);
                    showExplanation(response.isCorrect, '解説の読み込みに失敗しました');
                }

                await wait(1500);
                
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
                console.error('Server response indicates failure:', response.error);
                isAnswered = false;
            }
        } catch (error) {
            console.error('Error handling answer:', error);
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
