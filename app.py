from flask import Flask, render_template, request, jsonify, session
import requests
import random

app = Flask(__name__)
app.secret_key = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIxZTBmNDMyYzNhZWQ5MzA3NzM1YTZmODQ5NDQ1NTcwNyIsIm5iZiI6MTc0ODYyNTI1MC42ODQsInN1YiI6IjY4MzllNzYyNzc3NTljMmM1Mjk2OTEwMiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.mPktZSlelngEJhhlnJUIuiT1j7vIosptO678ShLay1c'  # Change this for production!

# --- IMPORTANT: Configure your TMDB API Key here ---
TMDB_API_KEY = 1e0f432c3aed9307735a6f8494455707  # Replace with your actual key
TMDB_BASE_URL = 'https://api.themoviedb.org/3'

def fetch_from_tmdb(endpoint, params=None):
    if params is None:
        params = {}
    params['api_key'] = TMDB_API_KEY
    try:
        response = requests.get(f"{TMDB_BASE_URL}{endpoint}", params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"TMDB API request error: {e}")
        return None

def get_popular_actors(count=200): # Get a larger pool of popular actors
    data = fetch_from_tmdb('/person/popular', {'language': 'en-US', 'page': 1})
    if data and 'results' in data:
        # Filter out actors with very few known credits to improve game quality
        popular_actors = [actor for actor in data['results'] if actor.get('known_for_department') == 'Acting' and actor.get('popularity', 0) > 10]
        # Fetch more pages if needed to get enough actors
        page = 2
        while len(popular_actors) < count and page <= 5: # Limit pages to avoid excessive calls
            data = fetch_from_tmdb('/person/popular', {'language': 'en-US', 'page': page})
            if data and 'results' in data:
                popular_actors.extend([actor for actor in data['results'] if actor.get('known_for_department') == 'Acting' and actor.get('popularity', 0) > 10])
            else:
                break
            page += 1
        return popular_actors
    return []

def get_actor_credits(actor_id):
    data = fetch_from_tmdb(f'/person/{actor_id}/movie_credits', {'language': 'en-US'})
    if data and 'cast' in data:
        # Filter out movies where character name is missing or very minor (heuristic)
        return [movie for movie in data['cast'] if movie.get('character') and movie.get('vote_count', 0) > 10] # Ensure movie is somewhat known
    return []

def get_movie_cast(movie_id):
    data = fetch_from_tmdb(f'/movie/{movie_id}/credits', {'language': 'en-US'})
    if data and 'cast' in data:
        return [actor for actor in data['cast'] if actor.get('known_for_department') == 'Acting']
    return []

def find_next_link(current_actor_id, previous_actor_id=None):
    actor_credits = get_actor_credits(current_actor_id)
    if not actor_credits:
        return None

    random.shuffle(actor_credits) # Shuffle to get different movies

    for movie in actor_credits:
        movie_id = movie['id']
        movie_title = movie['title']
        movie_cast = get_movie_cast(movie_id)
        if not movie_cast:
            continue

        potential_next_actors = [
            actor for actor in movie_cast
            if actor['id'] != current_actor_id and \
               (previous_actor_id is None or actor['id'] != previous_actor_id) and \
               actor.get('popularity', 0) > 5 # Ensure next actor is somewhat known
        ]
        
        if potential_next_actors:
            next_actor = random.choice(potential_next_actors)
            return {
                'actor_id': next_actor['id'],
                'actor_name': next_actor['name'],
                'connecting_movie_id': movie_id,
                'connecting_movie_title': movie_title
            }
    return None # Could not find a suitable next link

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start_game', methods=['GET'])
def start_game():
    popular_actors = get_popular_actors(20) # Get a decent pool
    if not popular_actors or len(popular_actors) < 2 :
        return jsonify({'error': 'Could not fetch enough popular actors from TMDB.'}), 500

    actor1 = random.choice(popular_actors)
    actor1_id = actor1['id']
    actor1_name = actor1['name']

    next_link_info = find_next_link(actor1_id)
    if not next_link_info:
        # Try with a different starting actor if the first one fails immediately
        for _ in range(5): # Try a few times
            actor1 = random.choice(popular_actors)
            if actor1['id'] == actor1_id: continue # Avoid same actor
            actor1_id = actor1['id']
            actor1_name = actor1['name']
            next_link_info = find_next_link(actor1_id)
            if next_link_info: break
        if not next_link_info:
             return jsonify({'error': 'Could not find a starting pair. Please try again.'}), 500


    session['current_actor_id'] = actor1_id
    session['current_actor_name'] = actor1_name
    session['next_actor_id'] = next_link_info['actor_id']
    session['next_actor_name'] = next_link_info['actor_name']
    # We don't strictly need to store the known connecting movie for validation if we re-check casts,
    # but it's good for debugging or potential hints.
    session['known_movie_for_pair'] = next_link_info['connecting_movie_title']
    session['score'] = 0
    session['chain'] = [actor1_name]


    return jsonify({
        'actor_a_name': actor1_name,
        'actor_b_name': next_link_info['actor_name'],
        'score': session['score'],
        'chain': session['chain']
    })

@app.route('/api/submit_movie', methods=['POST'])
def submit_movie():
    if TMDB_API_KEY == 'YOUR_TMDB_API_KEY':
        return jsonify({'error': 'TMDB API Key not configured on the server.'}), 500

    data = request.get_json()
    movie_title_guess = data.get('movie_title')

    if not movie_title_guess:
        return jsonify({'error': 'Movie title is required.'}), 400

    actor_a_id = session.get('current_actor_id')
    actor_b_id = session.get('next_actor_id')
    actor_a_name = session.get('current_actor_name')
    actor_b_name = session.get('next_actor_name')

    if not all([actor_a_id, actor_b_id, actor_a_name, actor_b_name]):
         return jsonify({'error': 'Game session error. Please restart.'}), 400

    # Search for the movie by title
    search_results = fetch_from_tmdb('/search/movie', {'query': movie_title_guess, 'language': 'en-US'})
    if not search_results or not search_results.get('results'):
        return jsonify({'correct': False, 'message': f"Movie '{movie_title_guess}' not found."})

    # Assume the first result is the one intended (simplification)
    guessed_movie_id = search_results['results'][0]['id']
    actual_movie_title = search_results['results'][0]['title'] # Use the title from TMDB for consistency

    movie_cast = get_movie_cast(guessed_movie_id)
    if not movie_cast:
        return jsonify({'correct': False, 'message': f"Could not fetch cast for '{actual_movie_title}'."})

    actor_a_in_movie = any(actor['id'] == actor_a_id for actor in movie_cast)
    actor_b_in_movie = any(actor['id'] == actor_b_id for actor in movie_cast)

    if actor_a_in_movie and actor_b_in_movie:
        session['score'] += 1
        session['chain'].append(f"---({actual_movie_title})---> {actor_b_name}")

        # Prepare next link
        previous_actor_id_for_next_link = actor_a_id # To avoid A-B-A loops if possible
        new_next_link_info = find_next_link(actor_b_id, previous_actor_id=previous_actor_id_for_next_link)

        if not new_next_link_info:
            return jsonify({
                'correct': True,
                'message': f"Correct! '{actor_a_name}' and '{actor_b_name}' were in '{actual_movie_title}'. You completed a great chain!",
                'game_over': True,
                'score': session['score'],
                'chain': session['chain']
            })

        session['current_actor_id'] = actor_b_id
        session['current_actor_name'] = actor_b_name
        session['next_actor_id'] = new_next_link_info['actor_id']
        session['next_actor_name'] = new_next_link_info['actor_name']
        session['known_movie_for_pair'] = new_next_link_info['connecting_movie_title']


        return jsonify({
            'correct': True,
            'message': f"Correct! '{actor_a_name}' and '{actor_b_name}' were in '{actual_movie_title}'.",
            'next_actor_a_name': actor_b_name,
            'next_actor_b_name': new_next_link_info['actor_name'],
            'score': session['score'],
            'chain': session['chain']
        })
    else:
        message = f"Incorrect. '{actor_a_name}' and '{actor_b_name}' were not both found in the main cast of '{actual_movie_title}'."
        if not actor_a_in_movie : message += f" '{actor_a_name}' was not found in the cast."
        if not actor_b_in_movie : message += f" '{actor_b_name}' was not found in the cast."
        return jsonify({
            'correct': False,
            'message': message,
            'score': session['score']
        })

if __name__ == '__main__':
    app.run(debug=True) # debug=True is for development ONLY
