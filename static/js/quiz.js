document.addEventListener('DOMContentLoaded', function() {
    // クイズオプションのコンテナを取得
    const optionsContainer = document.querySelector('.options-container');
    if (!optionsContainer) return; // クイズページ以外では実行しない

    // プログレスバーとスコア表示を取得
    const progressFill = document.querySelector('.progress-fill');
    const scoreDisplay = document.querySelector('.score-display');
    let isAnswered = false; // 回答済みフラグ

    // プログレスバーの更新
    function updateProgress(current, total) {
        const progress = (current / total) * 100;
        progressFill.style.width = `${progress}%`;
    }

    // 回答をサーバーに送信する関数
    async function submitAnswer(selectedIndex) {
        try {
            const response = await fetch('/submit_answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ selected: selectedIndex })
            });
            return await response.json(); // レスポンスをJSON形式で返す
        } catch (error) {
            console.error('Error submitting answer:', error);
            return { success: false }; // エラー時は失敗を返す
        }
    }

    // オプションがクリックされたときの処理
    async function handleOptionClick(event) {
        if (!event.target.classList.contains('option') || isAnswered) return; // 既に回答済みの場合は無視
        
        isAnswered = true; // 回答済みフラグを立てる
        const selectedOption = event.target; // 選択されたオプション
        const options = document.querySelectorAll('.option'); // すべてのオプションを取得
        
        // 選択されたオプションを強調表示
        options.forEach(option => {
            option.classList.remove('selected');
        });
        
        selectedOption.classList.add('selected');
        
        const selectedIndex = Array.from(options).indexOf(selectedOption); // 選択されたオプションのインデックス
        const correctIndex = parseInt(optionsContainer.dataset.correct); // 正解のインデックス
        
        try {
            // 回答をサーバーに送信し、レスポンスを取得
            const response = await submitAnswer(selectedIndex);
            
            // 正解の場合
            if (selectedIndex === correctIndex) {
                selectedOption.classList.add('correct');
                const currentScore = parseInt(scoreDisplay.textContent.split(': ')[1]);
                scoreDisplay.textContent = `スコア: ${currentScore + 1}`; // スコアを更新
            } else {
                // 不正解の場合
                selectedOption.classList.add('incorrect');
                options[correctIndex].classList.add('correct'); // 正解を表示
            }
            
            // アニメーション後に次の問題へ遷移
            setTimeout(() => {
                const container = document.querySelector('.quiz-container');
                container.classList.add('fade');
                
                setTimeout(() => {
                    window.location.href = '/next_question'; // 次の問題へ遷移
                }, 100);
            }, 200);
        } catch (error) {
            console.error('Error handling answer:', error);
        }
    }

    optionsContainer.addEventListener('click', handleOptionClick); // オプションクリックイベントを追加
    
    // フェードイン効果を適用
    document.querySelector('.quiz-container').classList.add('show');
});
