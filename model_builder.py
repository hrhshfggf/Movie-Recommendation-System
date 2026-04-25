import os, ast, pickle
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR  = os.path.join(BASE_DIR, 'models')

def find_csv(name):
    for p in [os.path.join(BASE_DIR, 'data', name), os.path.join(BASE_DIR, name)]:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"Cannot find {name} in {BASE_DIR}/data/ or {BASE_DIR}/")

movie_csv   = find_csv('tmdb_5000_movies.csv')
credits_csv = find_csv('tmdb_5000_credits.csv')

print(f"[✓] Movies  : {movie_csv}")
print(f"[✓] Credits : {credits_csv}")

movies  = pd.read_csv(movie_csv)
credits = pd.read_csv(credits_csv)

if 'movie_id' in credits.columns:
    credits = credits.rename(columns={'movie_id': 'id'})

if 'title' in credits.columns:
    movies = movies.merge(credits, on='title', suffixes=('', '_credits'))
else:
    movies = movies.merge(credits, on='id', suffixes=('', '_credits'))

needed = ['movie_id', 'title', 'overview', 'genres', 'keywords', 'cast', 'crew', 'vote_average']
if 'movie_id' not in movies.columns and 'id' in movies.columns:
    movies = movies.rename(columns={'id': 'movie_id'})

movies = movies[needed]
movies.dropna(inplace=True)
movies.reset_index(drop=True, inplace=True)
print(f"[✓] Rows after merge & dropna: {len(movies)}")

def convert(text):
    try:
        return [i['name'] for i in ast.literal_eval(text)]
    except Exception:
        return []

def convert_cast(text, limit=3):
    try:
        return [i['name'] for i in ast.literal_eval(text)[:limit]]
    except Exception:
        return []

def fetch_director(text):
    try:
        for i in ast.literal_eval(text):
            if i.get('job') == 'Director':
                return [i['name']]
    except Exception:
        pass
    return []

def collapse(lst):
    return [str(i).replace(' ', '') for i in lst]

movies['genres']   = movies['genres'].apply(convert)
movies['keywords'] = movies['keywords'].apply(convert)
movies['cast']     = movies['cast'].apply(convert_cast)
movies['crew']     = movies['crew'].apply(fetch_director)

for col in ['cast', 'crew', 'genres', 'keywords']:
    movies[col] = movies[col].apply(collapse)

movies['overview_display'] = movies['overview']
movies['overview']         = movies['overview'].apply(lambda x: x.split())

movies['tags'] = (movies['overview'] + movies['genres'] +
                  movies['keywords'] + movies['cast']   + movies['crew'])

new_df = movies[['movie_id', 'title', 'tags', 'vote_average', 'overview_display']].copy()
new_df['tags'] = new_df['tags'].apply(lambda x: ' '.join(x).lower())

print("[…] Vectorising tags (this may take ~30 s for 4800 movies)…")
cv         = CountVectorizer(max_features=5000, stop_words='english')
vectors    = cv.fit_transform(new_df['tags'])
similarity = cosine_similarity(vectors)
print(f"[✓] Similarity matrix shape: {similarity.shape}")

os.makedirs(MODELS_DIR, exist_ok=True)

movie_dict_path  = os.path.join(MODELS_DIR, 'movie_dict.pkl')
similarity_path  = os.path.join(MODELS_DIR, 'similarity.pkl')
pickle.dump(new_df.to_dict(),  open(movie_dict_path,  'wb'))
pickle.dump(similarity,        open(similarity_path,  'wb'))

print(f"[✓] Saved  → {movie_dict_path}")
print(f"[✓] Saved  → {similarity_path}")
print("\n✅  Done! You can now run:  streamlit run app.py")
