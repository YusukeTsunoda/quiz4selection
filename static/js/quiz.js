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
            console.log('[Submit] Is last question:', data.isLastQuestion);
            console.log('[Submit] Redirect URL:', data.redirectUrl);
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
            
            const response = await submitAnswer(selectedIndex);
            console.log('[Response] Full response object:', response);
            
            if (response.success) {
                console.log('[Feedback] Starting answer feedback display');
                if (response.isCorrect) {
                    selectedOption.classList.add('correct');
                    scoreDisplay.textContent = `スコア: ${response.currentScore}問`;
                    console.log('[Feedback] Showing correct answer');
                } else {
                    selectedOption.classList.add('incorrect');
                    const correctIndex = optionsContainer.dataset.correct;
                    if (options[correctIndex]) {
                        options[correctIndex].classList.add('correct');
                    }
                    console.log('[Feedback] Showing incorrect answer');
                }

                const wait = (ms) => new Promise(resolve => {
                    console.log(`[Timer] Starting ${ms}ms wait`);
                    setTimeout(() => {
                        console.log(`[Timer] ${ms}ms wait completed`);
                        resolve();
                    }, ms);
                });

                try {
                    const rawQuestionData = optionsContainer.dataset.questionData;
                    console.log('[Data] Raw question data:', rawQuestionData);
                    
                    let questionData = null;
                    try {
                        questionData = JSON.parse(rawQuestionData);
                        console.log('[Data] Parsed question data:', questionData);
                    } catch (parseError) {
                        console.error('[Data] JSON parse error:', parseError);
                    }
                    
                    if (questionData && (!response.isCorrect || questionData.explanation)) {
                        console.log('[Explanation] Adding explanation to DOM');
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
                        console.log('[Explanation] Explanation added successfully');
                    }

                } catch (error) {
                    console.error('[Error] Error handling explanation:', error);
                    console.error('[Error] Stack trace:', error.stack);
                }

                console.log('[Timer] Starting 1.5s display timer');
                const displayStartTime = Date.now();
                
                try {
                    await wait(1500);
                    const actualDisplayDuration = Date.now() - displayStartTime;
                    console.log(`[Timer] Actual display duration: ${actualDisplayDuration}ms`);
                } catch (error) {
                    console.error('[Timer] Error in wait:', error);
                }
                
                console.log('[Transition] Starting transition');
                const quizContainer = document.querySelector('.quiz-container');
                if (quizContainer) {
                    quizContainer.classList.add('fade');
                    
                    try {
                        await wait(100);
                        console.log('[Transition] Fade out complete');
                        
                        if (response.isLastQuestion) {
                            console.log('[Navigation] Redirecting to result page');
                            window.location.href = '/result';
                        } else {
                            console.log('[Navigation] Moving to next question');
                            window.location.href = '/next_question';
                        }
                    } catch (error) {
                        console.error('[Transition] Error during transition:', error);
                    }
                }
            } else {
                console.error('[Error] Server returned error:', response.error);
                isAnswered = false;
            }
        } catch (error) {
            console.error('[Error] Error in click handler:', error);
            console.error('[Error] Stack trace:', error.stack);
            isAnswered = false;
        }
    }

    optionsContainer.addEventListener('click', handleOptionClick);
    
    const quizContainer = document.querySelector('.quiz-container');
    if (quizContainer) {
        quizContainer.classList.add('show');
        console.log('[Init] Quiz container shown');
    }
});
