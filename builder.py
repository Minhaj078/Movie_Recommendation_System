import pandas as pd
import numpy as np
import ast
import os
import pickle
import sys
import nltk
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Ensure UTF-8 output on Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def build_recommendation_data():
    print("[+] Loading TMDB 5000 datasets...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    movies_path = os.path.join(base_dir, 'tmdb_5000_movies.csv')
    credits_path = os.path.join(base_dir, 'tmdb_5000_credits.csv')

    if not os.path.exists(movies_path) or not os.path.exists(credits_path):
        raise FileNotFoundError("Dataset CSV files missing!")

    movies = pd.read_csv(movies_path)
    credits = pd.read_csv(credits_path)

    print("[+] Merging datasets on title...")
    movies = movies.merge(credits, on='title')

    # Select critical columns plus rich display metadata
    cols = ['movie_id', 'title', 'overview', 'genres', 'keywords', 'cast', 'crew', 
            'vote_average', 'vote_count', 'release_date', 'popularity', 'tagline', 'runtime']
    movies = movies[cols]

    # FIX BUG 2: Drop missing titles/overviews and explicitly reset DataFrame index
    movies.dropna(subset=['overview', 'title'], inplace=True)
    movies.reset_index(drop=True, inplace=True)

    def convert_json_field(obj):
        if not isinstance(obj, str): return []
        try:
            return [i['name'] for i in ast.literal_eval(obj)]
        except Exception:
            return []

    def convert_cast_field(obj):
        if not isinstance(obj, str): return []
        try:
            return [i['name'] for i in ast.literal_eval(obj)[:3]]
        except Exception:
            return []

    def fetch_director_field(obj):
        if not isinstance(obj, str): return []
        try:
            for i in ast.literal_eval(obj):
                if i.get('job') == 'Director':
                    return [i['name']]
        except Exception:
            pass
        return []

    print("[+] Cleaning & extracting features...")
    parsed_genres = movies['genres'].apply(convert_json_field)
    parsed_keywords = movies['keywords'].apply(convert_json_field)
    parsed_cast = movies['cast'].apply(convert_cast_field)
    parsed_crew = movies['crew'].apply(fetch_director_field)
    parsed_overview = movies['overview'].apply(lambda x: x.split() if isinstance(x, str) else [])

    # Preserve readable lists for UI metadata
    movies['genres_display'] = parsed_genres
    movies['keywords_display'] = parsed_keywords
    movies['cast_display'] = parsed_cast
    movies['director_display'] = parsed_crew

    # FIX BUG 1: Remove spaces inside multi-word tags cleanly for vector matching
    genres_clean = parsed_genres.apply(lambda x: [i.replace(" ", "") for i in x])
    keywords_clean = parsed_keywords.apply(lambda x: [i.replace(" ", "") for i in x])
    cast_clean = parsed_cast.apply(lambda x: [i.replace(" ", "") for i in x])
    crew_clean = parsed_crew.apply(lambda x: [i.replace(" ", "") for i in x])

    movies['tags'] = parsed_overview + genres_clean + keywords_clean + cast_clean + crew_clean
    movies['tags_str'] = movies['tags'].apply(lambda x: " ".join(x).lower())

    print("[+] Stemming text tags with NLTK PorterStemmer...")
    ps = PorterStemmer()
    def stem_text(text):
        return " ".join([ps.stem(word) for word in text.split()])

    movies['tags_stemmed'] = movies['tags_str'].apply(stem_text)

    print("[+] Vectorizing tags with CountVectorizer...")
    cv = CountVectorizer(max_features=5000, stop_words='english')
    vectors = cv.fit_transform(movies['tags_stemmed']).toarray()

    print("[+] Calculating Cosine Similarity Matrix...")
    similarity = cosine_similarity(vectors)

    # Prepare clean metadata dict for API export
    clean_movies = movies[['movie_id', 'title', 'overview', 'genres_display', 
                           'keywords_display', 'cast_display', 'director_display', 
                           'vote_average', 'vote_count', 'release_date', 'popularity', 
                           'tagline', 'runtime']].copy()
    
    clean_movies.rename(columns={
        'genres_display': 'genres',
        'keywords_display': 'keywords',
        'cast_display': 'cast',
        'director_display': 'director'
    }, inplace=True)

    print("[+] Saving model artifacts...")
    artifacts_dir = os.path.join(base_dir, 'artifacts')
    os.makedirs(artifacts_dir, exist_ok=True)

    movies_dict_path = os.path.join(artifacts_dir, 'movies_dict.pkl')
    similarity_path = os.path.join(artifacts_dir, 'similarity.pkl')

    with open(movies_dict_path, 'wb') as f:
        pickle.dump(clean_movies.to_dict(orient='records'), f)

    with open(similarity_path, 'wb') as f:
        pickle.dump(similarity, f)

    print("✅ Model build & export complete successfully!")
    print(f"Total Movies: {len(clean_movies)}")
    print(f"Similarity matrix shape: {similarity.shape}")

if __name__ == '__main__':
    build_recommendation_data()
