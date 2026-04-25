import os
import json

def download_datasets():
    files = ['tmdb_5000_movies.csv', 'tmdb_5000_credits.csv']

    if all(os.path.exists(f) for f in files):
        print("[✓] CSV files already present in root.")
        return

    data_files = [os.path.join('data', f) for f in files]
    if all(os.path.exists(f) for f in data_files):
        print("[✓] CSV files already present in data/ folder.")
        return

    print("[…] CSV files not found. Downloading from Kaggle...")

    KAGGLE_USERNAME = os.environ.get('thanush09', '')
    KAGGLE_KEY      = os.environ.get('KGAT_e4eaa125abac16ca81f8c9ee373d42f2', '')

    if not KAGGLE_USERNAME or not KAGGLE_KEY:
        raise EnvironmentError(
            "KAGGLE_USERNAME and KAGGLE_KEY environment variables are not set.\n"
            "Add them in Streamlit Cloud → Settings → Secrets."
        )

    kaggle_dir = os.path.expanduser('~/.kaggle')
    os.makedirs(kaggle_dir, exist_ok=True)
    kaggle_json = os.path.join(kaggle_dir, 'kaggle.json')
    with open(kaggle_json, 'w') as f:
        json.dump({"username": KAGGLE_USERNAME, "key": KAGGLE_KEY}, f)
    os.chmod(kaggle_json, 0o600)

    os.system('pip install kaggle -q')
    result = os.system('kaggle datasets download -d tmdb/tmdb-movie-metadata --unzip')

    if result != 0:
        raise RuntimeError("Kaggle download failed. Check your KAGGLE_USERNAME and KAGGLE_KEY secrets.")

    print("[✓] Download complete!")

if __name__ == "__main__":
    download_datasets()
    
    