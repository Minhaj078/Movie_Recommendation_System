import os
import pickle
import sys
import re
import urllib.parse
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Ensure UTF-8 output on Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(BASE_DIR, 'artifacts')
MOVIES_DICT_PATH = os.path.join(ARTIFACTS_DIR, 'movies_dict.pkl')
SIMILARITY_PATH = os.path.join(ARTIFACTS_DIR, 'similarity.pkl')

movies_list = []
similarity_matrix = None
title_lookup = {}

def load_artifacts():
    global movies_list, similarity_matrix, title_lookup
    if not os.path.exists(MOVIES_DICT_PATH) or not os.path.exists(SIMILARITY_PATH):
        print("[!] Artifacts missing. Running builder...")
        from builder import build_recommendation_data
        build_recommendation_data()

    print("[+] Loading artifacts into memory...")
    with open(MOVIES_DICT_PATH, 'rb') as f:
        movies_list = pickle.load(f)
    
    with open(SIMILARITY_PATH, 'rb') as f:
        similarity_matrix = pickle.load(f)

    # Build fast case-insensitive title lookup map
    title_lookup = {m['title'].strip().lower(): idx for idx, m in enumerate(movies_list)}
    print(f"[+] Loaded {len(movies_list)} movies into memory!")

load_artifacts()

# Genre color map for visual poster styling
GENRE_GRADIENTS = {
    'Action': ('#dc2626', '#991b1b'),
    'Adventure': ('#d97706', '#92400e'),
    'Animation': ('#0284c7', '#0369a1'),
    'Comedy': ('#eab308', '#ca8a04'),
    'Crime': ('#475569', '#1e293b'),
    'Drama': ('#4f46e5', '#3730a3'),
    'Fantasy': ('#9333ea', '#6b21a8'),
    'Horror': ('#9f1239', '#4c0519'),
    'Romance': ('#db2777', '#9d174d'),
    'Science Fiction': ('#2563eb', '#1d4ed8'),
    'Thriller': ('#059669', '#047857'),
}

def get_poster_url(movie):
    """
    Generates a high-quality responsive vector poster image.
    """
    title = str(movie.get('title', 'Movie'))
    year = str(movie.get('release_date', ''))[:4]
    if not year or year == 'nan': year = '2024'
    rating = movie.get('vote_average', 0.0)
    if not isinstance(rating, (int, float)): rating = 0.0

    genres = movie.get('genres', [])
    first_genre = genres[0] if genres else 'Drama'
    genre_str = ", ".join(genres[:2]) if genres else 'Cinema'

    c1, c2 = GENRE_GRADIENTS.get(first_genre, ('#4f46e5', '#1e1b4b'))

    # Clean title text for SVG rendering
    clean_title = re.sub(r'[^\w\s\-\:\'\!\?]', '', title)
    t1 = clean_title[:20]
    t2 = clean_title[20:40] if len(clean_title) > 20 else ''

    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='300' height='450' viewBox='0 0 300 450'>
      <defs>
        <linearGradient id='bgGrad' x1='0%' y1='0%' x2='100%' y2='100%'>
          <stop offset='0%' stop-color='{c1}' stop-opacity='0.9'/>
          <stop offset='50%' stop-color='{c2}' stop-opacity='0.95'/>
          <stop offset='100%' stop-color='#090d16'/>
        </linearGradient>
        <linearGradient id='accentGrad' x1='0%' y1='0%' x2='100%' y2='0%'>
          <stop offset='0%' stop-color='#6366f1'/>
          <stop offset='100%' stop-color='#ec4899'/>
        </linearGradient>
      </defs>
      <rect width='300' height='450' fill='url(#bgGrad)' rx='16'/>
      <rect x='12' y='12' width='276' height='426' fill='none' stroke='rgba(255,255,255,0.12)' stroke-width='1.5' rx='12'/>
      <circle cx='150' cy='140' r='55' fill='url(#accentGrad)' opacity='0.25'/>
      <circle cx='150' cy='140' r='38' fill='none' stroke='#818cf8' stroke-width='2' opacity='0.6'/>
      <polygon points='142,125 166,140 142,155' fill='#f8fafc'/>
      <text x='150' y='255' font-family='system-ui, -apple-system, sans-serif' font-weight='800' font-size='21' fill='#ffffff' text-anchor='middle'>{t1}</text>
      {f"<text x='150' y='282' font-family='system-ui, -apple-system, sans-serif' font-weight='700' font-size='16' fill='#cbd5e1' text-anchor='middle'>{t2}</text>" if t2 else ''}
      <text x='150' y='322' font-family='system-ui, -apple-system, sans-serif' font-weight='600' font-size='13' fill='#94a3b8' text-anchor='middle'>{year} • {genre_str}</text>
      <rect x='105' y='352' width='90' height='30' rx='15' fill='rgba(15,23,42,0.75)' stroke='rgba(255,255,255,0.2)' stroke-width='1'/>
      <text x='150' y='372' font-family='system-ui, -apple-system, sans-serif' font-weight='700' font-size='13' fill='#fbbf24' text-anchor='middle'>★ {rating:.1f} / 10</text>
    </svg>"""

    return f"data:image/svg+xml;charset=utf-8,{urllib.parse.quote(svg)}"

def format_movie_response(movie):
    m = dict(movie)
    m['poster_url'] = get_poster_url(m)
    return m

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    all_genres = set()
    for m in movies_list:
        for g in m.get('genres', []):
            all_genres.add(g)
    
    return jsonify({
        'total_movies': len(movies_list),
        'genres_count': len(all_genres),
        'genres': sorted(list(all_genres))
    })

@app.route('/api/movies', methods=['GET'])
def get_movies():
    try:
        page = max(1, int(request.args.get('page', 1)))
        limit = min(50, max(1, int(request.args.get('limit', 20))))
    except ValueError:
        page = 1
        limit = 20

    genre = request.args.get('genre', '').strip()
    sort_by = request.args.get('sort_by', 'popularity')

    filtered = movies_list
    if genre:
        filtered = [m for m in filtered if genre in m.get('genres', [])]

    if sort_by == 'popularity':
        filtered = sorted(filtered, key=lambda x: x.get('popularity', 0), reverse=True)
    elif sort_by == 'rating':
        filtered = sorted(filtered, key=lambda x: x.get('vote_average', 0), reverse=True)
    elif sort_by == 'title':
        filtered = sorted(filtered, key=lambda x: x.get('title', ''))

    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    page_items = [format_movie_response(m) for m in filtered[start_idx:end_idx]]

    return jsonify({
        'total': len(filtered),
        'page': page,
        'limit': limit,
        'movies': page_items
    })

@app.route('/api/search', methods=['GET'])
def search_movies():
    query = request.args.get('q', '').strip().lower()
    try:
        limit = min(20, max(1, int(request.args.get('limit', 8))))
    except ValueError:
        limit = 8

    if not query:
        return jsonify({'results': []})

    matches = []
    # Match prefix first, then substring
    for m in movies_list:
        t = m['title'].lower()
        if t.startswith(query):
            matches.append((0, m))
        elif query in t:
            matches.append((1, m))

    matches = sorted(matches, key=lambda x: (x[0], -x[1].get('popularity', 0)))[:limit]
    results = [format_movie_response(m[1]) for m in matches]
    return jsonify({'results': results})

@app.route('/api/recommend', methods=['GET'])
def recommend():
    title_query = request.args.get('title', '').strip()
    try:
        top_n = min(20, max(1, int(request.args.get('top', 5))))
    except ValueError:
        top_n = 5

    if not title_query:
        return jsonify({'error': 'Please enter a movie title.'}), 400

    query_lower = title_query.lower()
    
    # 1. Exact match lookup
    target_idx = title_lookup.get(query_lower)
    
    # 2. Substring fallback match
    if target_idx is None:
        for t, idx in title_lookup.items():
            if query_lower in t:
                target_idx = idx
                break

    if target_idx is None:
        # Get popular fallback suggestions
        popular = sorted(movies_list, key=lambda x: x.get('popularity', 0), reverse=True)[:5]
        return jsonify({
            'error': f'Movie "{title_query}" was not found in our database.',
            'query': title_query,
            'suggestions': [format_movie_response(m) for m in popular]
        }), 404

    target_movie = format_movie_response(movies_list[target_idx])
    
    # Compute distances from positional index
    distances = similarity_matrix[target_idx]
    
    # Sort positional indices by similarity score in descending order (excluding self)
    similar_indices = sorted(list(enumerate(distances)), key=lambda x: x[1], reverse=True)[1:top_n + 1]

    recommendations = []
    for idx, sim_score in similar_indices:
        m = format_movie_response(movies_list[idx])
        m['similarity_score'] = round(float(sim_score), 4)
        m['match_percentage'] = int(round(float(sim_score) * 100))
        recommendations.append(m)

    return jsonify({
        'target_movie': target_movie,
        'recommendations': recommendations,
        'total_recommended': len(recommendations)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Movie Recommendation API Server on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
