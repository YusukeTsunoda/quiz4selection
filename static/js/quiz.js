document.addEventListener('DOMContentLoaded', function() {
    const optionsContainer = document.querySelector('.options-container');
    const progressFill = document.querySelector('.progress-fill');
    const scoreDisplay = document.querySelector('.score-display');
    let isAnswered = false;

    function updateProgress(current, total) {
        const progress = (current / total) * 100;
        progressFill.style.width = `${progress}%`;
    }

    async function submitAnswer(selectedIndex) {
        try {
            const response = await fetch('/submit_answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ selected: selectedIndex })
            });
            return await response.json();
        } catch (error) {
            console.error('Error submitting answer:', error);
            return { success: false };
        }
    }

    async function handleOptionClick(event) {
        if (!event.target.classList.contains('option') || isAnswered) return;
        
        isAnswered = true;
        const selectedOption = event.target;
        const options = document.querySelectorAll('.option');
        
        options.forEach(option => {
            option.classList.remove('selected');
        });
        
        selectedOption.classList.add('selected');
        
        const selectedIndex = Array.from(options).indexOf(selectedOption);
        const correctIndex = parseInt(optionsContainer.dataset.correct);
        
        try {
            // Submit answer to server and get response
            const response = await submitAnswer(selectedIndex);
            
            if (selectedIndex === correctIndex) {
                selectedOption.classList.add('correct');
                const currentScore = parseInt(scoreDisplay.textContent.split(': ')[1]);
                scoreDisplay.textContent = `Score: ${currentScore + 1}`;
            } else {
                selectedOption.classList.add('incorrect');
                options[correctIndex].classList.add('correct');
            }
            
            // Wait for animation
            setTimeout(() => {
                const container = document.querySelector('.quiz-container');
                container.classList.add('fade');
                
                // Check if this is the last question
                if (response.isLastQuestion) {
                    window.location.href = '/next_question';
                } else {
                    setTimeout(() => {
                        window.location.href = '/next_question';
                    }, 200);
                }
            }, 500);
        } catch (error) {
            console.error('Error handling answer:', error);
        }
    }

    optionsContainer.addEventListener('click', handleOptionClick);
    
    // Show content with fade-in effect
    document.querySelector('.quiz-container').classList.add('show');
});
