document.addEventListener('DOMContentLoaded', () => {
    const actorANameEl = document.getElementById('actor-a');
    const actorBNameEl = document.getElementById('actor-b');
    const movieTitleInputEl = document.getElementById('movie-title-input');
    const submitButton = document.getElementById('submit-button');
    const startButton = document.getElementById('start-button');
    const messageTextEl = document.getElementById('message-text');
    const scoreEl = document.getElementById('score');
    const chainListEl = document.getElementById('chain-list');

    function updateChainDisplay(chain) {
        chainListEl.innerHTML = ''; // Clear previous chain
        if (chain && chain.length > 0) {
            chain.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item;
                chainListEl.appendChild(li);
            });
        }
    }
    
    async function startGame() {
        messageTextEl.textContent = 'Starting new game...';
        messageTextEl.className = '';
        actorANameEl.textContent = "Loading...";
        actorBNameEl.textContent = "Loading...";
        movieTitleInputEl.value = "";
        movieTitleInputEl.disabled = true;
        submitButton.disabled = true;


        try {
            const response = await fetch('/api/start_game');
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            if (data.error) {
                 messageTextEl.textContent = data.error;
                 messageTextEl.className = 'incorrect';
                 return;
            }

            actorANameEl.textContent = data.actor_a_name;
            actorBNameEl.textContent = data.actor_b_name;
            scoreEl.textContent = data.score;
            updateChainDisplay(data.chain);
            messageTextEl.textContent = 'Game started! Enter a movie title.';
            movieTitleInputEl.disabled = false;
            submitButton.disabled = false;
            movieTitleInputEl.focus();

        } catch (error) {
            messageTextEl.textContent = `Error starting game: ${error.message}`;
            messageTextEl.className = 'incorrect';
            console.error("Error starting game:", error);
        }
    }

    async function submitMovie() {
        const movieTitle = movieTitleInputEl.value.trim();
        if (!movieTitle) {
            messageTextEl.textContent = 'Please enter a movie title.';
            messageTextEl.className = 'incorrect';
            return;
        }

        messageTextEl.textContent = 'Checking...';
        messageTextEl.className = '';
        movieTitleInputEl.disabled = true;
        submitButton.disabled = true;

        try {
            const response = await fetch('/api/submit_movie', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ movie_title: movieTitle }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            messageTextEl.textContent = data.message;
            scoreEl.textContent = data.score;
            if (data.chain) {
                 updateChainDisplay(data.chain);
            }


            if (data.correct) {
                messageTextEl.className = 'correct';
                movieTitleInputEl.value = ''; // Clear input for next round

                if (data.game_over) {
                    messageTextEl.textContent += " Game Over! You found the end of this possible chain!";
                    movieTitleInputEl.disabled = true;
                    submitButton.disabled = true;
                } else if (data.next_actor_a_name && data.next_actor_b_name) {
                    actorANameEl.textContent = data.next_actor_a_name;
                    actorBNameEl.textContent = data.next_actor_b_name;
                    movieTitleInputEl.disabled = false;
                    submitButton.disabled = false;
                    movieTitleInputEl.focus();
                } else {
                     // Should not happen if not game_over, but handle it
                    messageTextEl.textContent = "Error: Next actors not provided.";
                    messageTextEl.className = 'incorrect';
                }
            } else {
                messageTextEl.className = 'incorrect';
                movieTitleInputEl.disabled = false; // Allow user to try again or enter new title
                submitButton.disabled = false;
                movieTitleInputEl.focus();
            }

        } catch (error) {
            messageTextEl.textContent = `Error submitting movie: ${error.message}`;
            messageTextEl.className = 'incorrect';
            console.error("Error submitting movie:", error);
            movieTitleInputEl.disabled = false;
            submitButton.disabled = false;
        }
    }

    startButton.addEventListener('click', startGame);
    submitButton.addEventListener('click', submitMovie);
    movieTitleInputEl.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            submitMovie();
        }
    });


    // Initially hide the game area until start is clicked, or auto-start
    // For this version, let's just make them click start.
    actorANameEl.textContent = "-";
    actorBNameEl.textContent = "-";
    movieTitleInputEl.disabled = true;
    submitButton.disabled = true;
    messageTextEl.textContent = "Click 'Start New Game' to begin!";
});