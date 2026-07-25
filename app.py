import os
import pickle
import sys
import re
import json
import urllib.parse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Ensure UTF-8 output on Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_dotenv():
    # Simple manual env parser to avoid python-dotenv dependency
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip()

# Load env variables at startup
load_dotenv()
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')
if TMDB_API_KEY:
    print("[+] TMDB API Key resolved successfully.")
else:
    print("[!] No TMDB API Key found. Running with vector poster fallback mode.")

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

# Poster and Metadata Caching System
POSTER_CACHE_PATH = os.path.join(ARTIFACTS_DIR, 'poster_cache.json')
poster_cache = {}

def load_poster_cache():
    global poster_cache
    if os.path.exists(POSTER_CACHE_PATH):
        try:
            with open(POSTER_CACHE_PATH, 'r') as f:
                loaded = json.load(f)
            # Self-healing: Clean out any empty dicts from cache so they get retried
            poster_cache = {k: v for k, v in loaded.items() if v}
            print(f"[+] Loaded {len(poster_cache)} cached posters (cleaned {len(loaded) - len(poster_cache)} empty records) from {POSTER_CACHE_PATH}")
        except Exception as e:
            print(f"[!] Failed to load poster cache: {e}")
            poster_cache = {}
    else:
        print("[+] Poster cache file does not exist yet. Creating a new one...")
        poster_cache = {}

def save_poster_cache():
    try:
        with open(POSTER_CACHE_PATH, 'w') as f:
            json.dump(poster_cache, f)
    except Exception as e:
        print(f"[!] Failed to save poster cache: {e}")

load_poster_cache()

def fetch_tmdb_metadata(movie_id):
    """
    Fetches poster and metadata from TMDB using the movie's ID.
    Returns a dict with metadata, {"not_found": True} if 404, or None if network failed.
    """
    if not TMDB_API_KEY:
        return None
        
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
    
    # Try up to 2 times to handle temporary network/socket drops
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode('utf-8'))
                poster_path = data.get('poster_path')
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
                
                # Extract basic metadata
                metadata = {
                    'poster_url': poster_url,
                    'vote_average': data.get('vote_average'),
                    'release_date': data.get('release_date'),
                    'overview': data.get('overview'),
                    'genres': [g['name'] for g in data.get('genres', [])] if data.get('genres') else None,
                    'runtime': data.get('runtime')
                }
                # Remove None values so we only override if available
                return {k: v for k, v in metadata.items() if v is not None}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"[!] Movie ID {movie_id} not found on TMDB (404).")
                return {"not_found": True}
            print(f"[!] HTTP Error {e.code} for movie_id {movie_id}")
            return None
        except Exception as e:
            if attempt == 0:
                # Wait 200ms and retry
                import time
                time.sleep(0.2)
                continue
            print(f"[!] Network error fetching TMDB metadata for movie_id {movie_id}: {e}")
            return None

def enrich_movies_with_posters(movies_to_enrich):
    """
    Enriches a list of movie dicts with poster URLs and TMDB metadata.
    Uses cached values where available, and fetches missing ones in parallel.
    """
    global poster_cache
    
    missing_ids = []
    for m in movies_to_enrich:
        movie_id = str(m.get('movie_id'))
        if movie_id not in poster_cache and TMDB_API_KEY:
            missing_ids.append(m.get('movie_id'))
            
    if missing_ids:
        # Fetch missing in parallel using ThreadPoolExecutor
        print(f"[+] Fetching {len(missing_ids)} missing poster(s) in parallel from TMDB...")
        with ThreadPoolExecutor(max_workers=min(10, len(missing_ids))) as executor:
            results = list(executor.map(fetch_tmdb_metadata, missing_ids))
            
        # Update cache
        cache_updated = False
        for mid, meta in zip(missing_ids, results):
            if meta is not None:
                poster_cache[str(mid)] = meta
                cache_updated = True
                
        if cache_updated:
            save_poster_cache()
            
    # Apply cached/fetched metadata to the response objects
    enriched = []
    for m in movies_to_enrich:
        enriched_movie = dict(m)
        movie_id_str = str(enriched_movie.get('movie_id'))
        
        # Load from cache if exists
        cached_meta = poster_cache.get(movie_id_str, {})
        
        # Override fields if they are available in the cache and it's not a "not_found" marker
        if cached_meta and not cached_meta.get('not_found'):
            if cached_meta.get('poster_url'):
                enriched_movie['poster_url'] = cached_meta['poster_url']
            else:
                # If cached metadata doesn't have a poster path, fallback to SVG generator
                enriched_movie['poster_url'] = get_poster_url(enriched_movie)
            
            # Enrich with other fields if they are in the cache
            if cached_meta.get('vote_average') is not None:
                enriched_movie['vote_average'] = cached_meta['vote_average']
            if cached_meta.get('release_date'):
                enriched_movie['release_date'] = cached_meta['release_date']
            if cached_meta.get('overview'):
                enriched_movie['overview'] = cached_meta['overview']
            if cached_meta.get('genres'):
                enriched_movie['genres'] = cached_meta['genres']
            if cached_meta.get('runtime') is not None:
                enriched_movie['runtime'] = cached_meta['runtime']
        else:
            # Fallback to the SVG vector poster
            enriched_movie['poster_url'] = get_poster_url(enriched_movie)
            
        enriched.append(enriched_movie)
        
    return enriched

def format_movies_batch(movies):
    """
    Formats a list of movies, enriching them in batch with posters and metadata.
    """
    raw_dicts = [dict(m) for m in movies]
    return enrich_movies_with_posters(raw_dicts)

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
    page_items = format_movies_batch(filtered[start_idx:end_idx])

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
    results = format_movies_batch([m[1] for m in matches])
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
            'suggestions': format_movies_batch(popular)
        }), 404

    target_movie = format_movies_batch([movies_list[target_idx]])[0]
    
    # Compute distances from positional index
    distances = similarity_matrix[target_idx]
    
    # Sort positional indices by similarity score in descending order (excluding self)
    similar_indices = sorted(list(enumerate(distances)), key=lambda x: x[1], reverse=True)[1:top_n + 1]

    # Batch format recommended movies in parallel
    raw_recs = [movies_list[idx] for idx, _ in similar_indices]
    recommendations = format_movies_batch(raw_recs)
    
    # Inject similarity scores
    for m, (idx, sim_score) in zip(recommendations, similar_indices):
        m['similarity_score'] = round(float(sim_score), 4)
        m['match_percentage'] = int(round(float(sim_score) * 100))

    return jsonify({
        'target_movie': target_movie,
        'recommendations': recommendations,
        'total_recommended': len(recommendations)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Movie Recommendation API Server on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
