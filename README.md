🎬 CineMatrix — Movie Recommendation System

A content-based machine learning recommendation engine built with Python, Scikit-learn, Matplotlib, and Streamlit.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Installation & Setup](#installation--setup)
6. [How to Run](#how-to-run)
7. [How It Works — The ML Pipeline](#how-it-works--the-ml-pipeline)
8. [File Descriptions](#file-descriptions)
9. [Analytics Dashboard](#analytics-dashboard)
10. [API Reference — TMDB](#api-reference--tmdb)
11. [Troubleshooting](#troubleshooting)
12. [Tech Stack](#tech-stack)

---

## Project Overview

Cenematrix is a movie recommendation system that uses content-based filtering to suggest films similar to one the user already likes. It analyses the genres, cast, director, keywords, and plot overview of a chosen movie and returns the 10 most mathematically similar films using cosine similarity.

The frontend is built entirely in Streamlit — a Python web framework — so no HTML, CSS, or JavaScript knowledge is required to run or modify it. The app is split into two phases:

- **Offline phase** (`model_builder.py`) — runs once to preprocess data and save the similarity matrix.
- **Online phase** (`app.py`) — loads the pre-built model at startup for millisecond-speed recommendations.

---

## Features

| Feature | Description |
| :--- | :--- |
| **Smart Search** | Searchable dropdown across all 4,803 movie titles — type to filter instantly. |
| **Content-Based Recommendations** | Returns 10 films most similar in plot, genres, cast, keywords, and director. |
| **Hover Overlay Cards** | Each movie card reveals cast, runtime, rating, and overview snippet on hover. |
| **Ratings on Cards** | IMDb rating and primary genre badge visible on every recommendation card. |
| **Click for Details** | "Details" opens a full movie page with poster, rating, runtime, year, overview, genres, director, and top 5 cast. |
| **Analytics & Charts Tab** | Full data dashboard with 6 Matplotlib charts + 1 interactive Streamlit bar chart + KPI row. |
| **Fast Loading** | Poster URLs cached in `models/poster_cache.pkl` — no repeat API calls ever. |
| **Dark Cinema Theme** | Deep-space dark UI (`#07070f`) with Poppins font, purple/blue gradient accents, and an animated pulse dot. |

---

## Project Structure

```text
cinematch_ai/
│
├── app.py                        ← Main Streamlit page (run this)
├── model_builder.py              ← ML training script (run once)
│
├── pages/
│   └── movie_detail.py           ← Movie detail page (auto-loaded by Streamlit)
│
├── models/                       ← Auto-created by model_builder.py
│   ├── movie_dict.pkl            ← Processed movie dataframe
│   ├── similarity.pkl            ← Cosine similarity matrix (4803 × 4803)
│   └── poster_cache.pkl          ← Auto-created: cached TMDB poster URLs
│
├── data/                         ← Put your CSV files here (or in root)
│   ├── tmdb_5000_movies.csv
│   └── tmdb_5000_credits.csv
│
└── README.md
```

> **Note:** The `pages/` folder is a Streamlit multi-page convention. Any `.py` file inside it is automatically registered as a separate navigable page, enabling `st.switch_page()` calls between the home page and the detail page.

---

## Prerequisites

- Python **3.10 or higher**
- pip (Python package manager)
- Internet connection (for poster images from TMDB)
- The two dataset CSV files:
  - `tmdb_5000_movies.csv`
  - `tmdb_5000_credits.csv`

---

## Installation & Setup

### Step 1 — Install required Python libraries

```bash
pip install streamlit pandas scikit-learn requests matplotlib
```

> `matplotlib` is required for the Analytics & Charts tab. All other libraries are needed for core functionality.

### Step 2 — Place CSV files

Put both CSV files in the **root folder** of the project (same folder as `app.py`), or inside a `data/` subfolder. The app checks both locations automatically.

```text
cinematch_ai/
├── tmdb_5000_movies.csv    ← here, OR inside data/
├── tmdb_5000_credits.csv   ← here, OR inside data/
├── app.py
└── ...
```

### Step 3 — Create the `pages/` folder and place `movie_detail.py`

```text
cinematch_ai/
└── pages/
    └── movie_detail.py
```

---

## How to Run

### Step 1 — Build the ML model (run ONCE)

```bash
python model_builder.py
```

What this does:
- Reads and merges both CSV files on the `title` column (falls back to `id` if needed)
- Extracts genres, cast (top 3 only), director, keywords, and overview for each movie
- Removes spaces from names so `"Tom Hanks"` → `"TomHanks"` (treated as one unique token)
- Converts all text features into a numeric vector using `CountVectorizer` (5,000 features)
- Computes cosine similarity between every pair of movies
- Saves `movie_dict.pkl` and `similarity.pkl` into the `models/` folder

You will see:

```
[✓] Movies  : ./tmdb_5000_movies.csv
[✓] Credits : ./tmdb_5000_credits.csv
[✓] Rows after merge & dropna: 4803
[…] Vectorising tags (this may take ~30 s for 4800 movies)…
[✓] Similarity matrix shape: (4803, 4803)
[✓] Saved  → models/movie_dict.pkl
[✓] Saved  → models/similarity.pkl

✅  Done! You can now run:  streamlit run app.py
```

You only need to run this step again if you change the CSV data.

### Step 2 — Start the web app

```bash
streamlit run app.py
```

Streamlit will open the app in your browser automatically at `http://localhost:8501`.

---

## How It Works — The ML Pipeline

### 1. Data Loading & Merging

The two CSV files are loaded with Pandas and merged on the `title` column (with `id` as fallback) so that each movie row contains its genres, keywords, cast, crew, overview, and rating in one place. Only `movie_id`, `title`, `overview`, `genres`, `keywords`, `cast`, `crew`, and `vote_average` are kept. Rows with any missing values are dropped — leaving **4,803 clean records**.

### 2. Feature Engineering — Building "Tags"

For each movie, a single text string called `tags` is built by combining:

| Source | Example (Avatar) |
| :--- | :--- |
| Overview | `"in the 22nd century a paraplegic marine dispatched to moon pandora..."` |
| Genres | `"Action Adventure Fantasy ScienceFiction"` |
| Keywords | `"cultureclash future war biopunk..."` |
| Top 3 Cast | `"SamWorthington ZoeSaldana SigourneyWeaver"` |
| Director | `"JamesCameron"` |

**Why remove spaces from names?** `"Tom Hanks"` becomes `"TomHanks"` so the vectorizer treats it as one unique token, not two generic words (`"Tom"`, `"Hanks"`).

### 3. Text Vectorization — CountVectorizer

`CountVectorizer` from Scikit-learn converts the `tags` text into a numeric matrix where:
- Each **row** = one movie
- Each **column** = one word/token (top 5,000 most common)
- Each **cell** = how many times that word appears in that movie's tags
- English stop words (`the`, `a`, `is`, …) are removed automatically

```
Avatar:        [3, 1, 0, 2, 0, ...]   → result shape: (4803, 5000)
Interstellar:  [1, 0, 2, 1, 1, ...]
```

### 4. Cosine Similarity

For every pair of movies, cosine similarity is computed. It measures the angle between two vectors — preferred over Euclidean distance because it is length-invariant (a short-overview film is compared fairly with a long-overview film).

```
similarity[Avatar][Interstellar] = 0.72   ← very similar
similarity[Avatar][Titanic]      = 0.18   ← not similar
```

Score of `1.0` = identical; `0.0` = completely different. Final matrix shape: **(4,803 × 4,803)**.

### 5. Recommendation

When a user selects a movie:
1. Find its row index in the dataframe
2. Look up that row in the similarity matrix — one score per movie
3. Sort all movies by score (highest first)
4. Skip index `[0]` (the movie itself, score = 1.0)
5. Return the next **10 movies** as recommendations

```python
idx    = movies[movies["title"] == selected].index[0]
scores = list(enumerate(similarity[idx]))
top10  = sorted(scores, key=lambda x: x[1], reverse=True)[1:11]
```

---

## File Descriptions

### `app.py`

The main Streamlit page. Responsibilities:
- Loads the ML model from pickle files (`movie_dict.pkl`, `similarity.pkl`) at startup using `@st.cache_resource`
- Builds a **local metadata lookup** (`build_lookup()`) by re-reading and merging the raw CSVs — provides rating, cast, director, genres, overview, tagline, runtime, and vote_count for any movie without any API call
- Fetches movie **poster URLs** from the TMDB API and caches them locally in `poster_cache.pkl`; validates cache entries and re-fetches stale dict-format entries automatically
- Renders a persistent **navbar** with live movie count, ML-Powered badge, and TMDB badge
- Manages **two tabs**: `🎬 Recommendations` and `📊 Analytics & Charts`
- Renders the search dropdown, animated hero panel, genre feature strip, and two 5-column rows of movie cards
- Each **movie card** shows a TMDB poster and genre badge; hovering reveals a dark overlay with cast, runtime, rating, and overview snippet
- Each card has a **Details** button that saves full metadata to `st.session_state` and navigates to `pages/movie_detail.py`

### `model_builder.py`

One-time training script. Responsibilities:
- Searches for CSVs automatically in `BASE_DIR/data/` then `BASE_DIR/` (project root)
- Loads and merges `tmdb_5000_movies.csv` and `tmdb_5000_credits.csv`
- Parses JSON-formatted columns (`genres`, `keywords`, `cast`, `crew`) using `ast.literal_eval()`
- Limits cast to **top 3**; extracts director from crew by matching `job == "Director"`
- Collapses spaces in all name tokens and builds the lowercase `tags` string per movie
- Trains `CountVectorizer(max_features=5000, stop_words='english')` and computes `cosine_similarity`
- Creates the `models/` directory automatically if it does not exist, then saves both pickle files

### `pages/movie_detail.py`

Streamlit detail page opened when "Details" is clicked on any recommendation card. Responsibilities:
- Reads the selected movie's full metadata dict from `st.session_state.detail_movie`
- Displays: real poster image via `st.image`, large title heading, tagline in italic below
- Three metric cards: **IMDb Rating · Runtime · Release Year**
- Full overview paragraph, comma-separated genres, director name, and top 5 cast members
- **Back button** returns to the home page with previous recommendation results still visible in session state

---

## Analytics Dashboard

The `📊 Analytics & Charts` tab provides a full data dashboard built with Matplotlib using a dark cinema theme (`#07070f` / `#14142a` backgrounds) that matches the overall app UI. All data functions are cached with `@st.cache_data`.

### KPI Row (5 metric cards across the top)

| Metric | How It's Computed |
| :--- | :--- |
| Total Movies | `len(df_raw)` |
| Avg Rating | `df_raw["vote_average"].mean()` |
| Median Runtime | `df_raw["runtime"].median()` |
| Latest Year | `df_raw["year"].max()` |
| Total Votes (M) | `df_raw["vote_count"].sum() // 1_000_000` |

### Charts

| Chart | Type | Key Insight |
| :--- | :--- | :--- |
| 🎭 Top 10 Genres | Horizontal bar — Matplotlib | Drama leads with 2,297 films |
| ⭐ Rating Distribution | Histogram with plasma colourmap + mean line | Most films rate between 5–8; mean ≈ 6.1 |
| 📅 Movies per Year (1990–2017) | Dual-axis area + line (count) / dashed line (avg rating) | Volume peaks around 2014; average rating is stable |
| 🍕 Top 8 Genre Share | Donut pie chart with centre label | Drama + Comedy + Thriller dominate |
| 🔢 Interactive Genre Bar | Native `st.bar_chart` | Hover to explore exact counts per genre |
| ⏱ Runtime vs Rating | Scatter plot, plasma colourmap | Films 90–150 min cluster at higher ratings |
| 💰 Budget vs Revenue | Log-scale scatter + break-even diagonal line | Financial outliers clearly visible |
| 🏆 Top 15 Highest-Rated | HTML table with inline gradient rating bar | Filtered to movies with ≥ 500 votes |

---

## API Reference — TMDB

The app uses the TMDb (The Movie Database) API **only to fetch movie poster images**.

| Parameter | Value |
| :--- | :--- |
| Base URL | `https://api.themoviedb.org/3/movie/{id}` |
| API Key | `cdf3a58aa720377a583f33c3e879377c` |
| Image Base URL | `https://image.tmdb.org/t/p/w500` |
| Timeout | 8 seconds per request |
| Cache file | `models/poster_cache.pkl` |
| Cache validation | Only string URLs starting with `https://...tmdb...` are served; stale dict-format entries are re-fetched automatically |
| Fallback | Gradient placeholder div rendered in-browser if API fails or no poster exists |

Poster URLs are cached after the first fetch, so the API is only ever called **once per movie**.

All other data — rating, cast, director, genres, overview, tagline, runtime — comes directly from the local CSV files via `build_lookup()`. **No API call required for metadata.**

---

## Troubleshooting

| Problem | Likely Cause | Resolution |
| :--- | :--- | :--- |
| `Model files missing` error | `model_builder.py` not run yet | Run `python model_builder.py` |
| Posters show as broken images | TMDB API key invalid or no internet | Check internet connection; verify API key in `app.py` |
| Detail page shows `N/A` | Old `poster_cache.pkl` from earlier version | Delete `models/poster_cache.pkl` and restart the app |
| `ModuleNotFoundError` | Library not installed | Run `pip install streamlit pandas scikit-learn requests matplotlib` |
| `FileNotFoundError` for CSVs | CSVs not in root or `data/` folder | Place CSV files in project root or inside `data/` |
| Detail page shows `🎬` emoji | Using old `movie_detail.py` | Replace with latest version (uses `st.image(poster)` in `col1`) |
| Charts not rendering | `matplotlib` not installed | Run `pip install matplotlib` |
| Stale or corrupted poster cache | Old dict-format entries in cache | App auto-detects and re-fetches; or delete `models/poster_cache.pkl` |

---

## Tech Stack

| Tool | Version | Purpose |
| :--- | :--- | :--- |
| Python | 3.10+ | Programming language |
| Streamlit | Latest | Multi-page web UI framework |
| Pandas | Latest | Data loading, merging, and manipulation |
| Scikit-learn | Latest | CountVectorizer + cosine similarity |
| Matplotlib | Latest | Analytics charts with dark cinema theme |
| Requests | Latest | TMDB API calls for poster images |
| Pickle | Built-in | Saving/loading model and cache files |

---

## Dataset

**TMDB 5,000 Movie Dataset** — contains metadata for 4,803 movies including:
- Title, overview, genres, keywords
- Cast (actor names), crew (director name)
- Vote average (IMDb-style rating, 0–10), vote count
- Release date, runtime, budget, revenue, tagline
