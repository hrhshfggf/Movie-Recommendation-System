import os, subprocess, sys, streamlit as st

# STEP 1 ─ MODEL BOOTSTRAP

if not os.path.exists("models/similarity.pkl") or \
   not os.path.exists("models/movie_dict.pkl"):
    with st.spinner("⏳ Building model — first time only, ~60 seconds..."):
        subprocess.run([sys.executable, "model_builder.py"], check=True)
    st.rerun()

import pickle, ast, requests, urllib.parse, hmac, hashlib, time
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# STEP 2 ─ GOOGLE OAUTH CONFIGURATION

GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"

# STEP 3 ─ CSRF STATE TOKEN HELPERS

_SIGN_KEY = (GOOGLE_CLIENT_SECRET or "dev-secret").encode("utf-8")

def _make_state() -> str:
    ts  = str(int(time.time()))
    sig = hmac.new(_SIGN_KEY, ts.encode(), hashlib.sha256).hexdigest()[:24]
    return f"{ts}.{sig}"

def _verify_state(state: str) -> bool:
    """True if signature is valid and token is < 10 minutes old."""
    try:
        ts_str, sig = state.rsplit(".", 1)
        expected    = hmac.new(_SIGN_KEY, ts_str.encode(), hashlib.sha256).hexdigest()[:24]
        if not hmac.compare_digest(sig, expected):
            return False
        return 0 <= int(time.time()) - int(ts_str) <= 600
    except Exception:
        return False

# STEP 4 ─ GOOGLE OAUTH URL BUILDER & TOKEN EXCHANGE

def make_google_auth_url() -> str:
    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         _make_state(),
        "prompt":        "select_account",
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)

def exchange_code_for_user(code: str):
    try:
        r = requests.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri":  GOOGLE_REDIRECT_URI,
            "grant_type":    "authorization_code",
        }, timeout=10)
        r.raise_for_status()
        token = r.json().get("access_token")
        if not token:
            return None
        return requests.get(
            GOOGLE_USERINFO,
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        ).json()
    except Exception:
        return None

# STEP 5 ─ STREAMLIT PAGE CONFIG

st.set_page_config(
    page_title="CineMatrix",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# STEP 6 ─ GLOBAL CSS / DESIGN SYSTEM

st.markdown("""
<style>

/* ── 6a. Google Font ─────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap');

/* ── 6b. Design Tokens (CSS custom properties) ───────────────────────────── */
:root {
  --bg:      #07070f;
  --surface: #0f0f1c;
  --card:    #14142a;
  --border:  #1e1e38;
  --border2: #2a2a50;
  --purple:  #7c3aed;
  --blue:    #2563eb;
  --cyan:    #06b6d4;
  --pink:    #ec4899;
  --gold:    #f59e0b;
  --green:   #10b981;
  --text:    #f1f0ff;
  --muted:   #6b7194;
  --radius:  14px;
}

/* ── 6c. Global Reset ────────────────────────────────────────────────────── */
*, *::before, *::after {
  box-sizing: border-box;
}

html, body, [class*="css"] {
  font-family: 'Poppins', sans-serif !important;
}

/* ── 6d. Streamlit App Shell Overrides ───────────────────────────────────── */
.stApp {
  background: var(--bg) !important;
  color: var(--text);
}

.block-container {
  padding: 0 2.5rem 4rem !important;
  max-width: 1380px;
}

/* Hide default Streamlit chrome (menu, footer, header) */
#MainMenu, footer, header {
  visibility: hidden;
}

/* Hide sidebar entirely — navigation is inline */
section[data-testid="stSidebar"] {
  display: none !important;
}

/* Custom thin scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }

/* ── 6e. Navbar ──────────────────────────────────────────────────────────── */
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 0;
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--border);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1.5rem;
  font-weight: 900;
  letter-spacing: -0.02em;
}

.nav-brand-icon {
  width: 38px;
  height: 38px;
  background: linear-gradient(135deg, var(--purple) 0%, var(--blue) 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  box-shadow: 0 4px 15px rgba(124, 58, 237, 0.45);
}

.nav-brand-text {
  background: linear-gradient(135deg, #a78bfa 0%, #60a5fa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nav-subtitle {
  font-size: 0.72rem;
  color: var(--muted);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.nav-stats { display: flex; gap: 2rem; align-items: center; }

.nav-stat { text-align: center; }

.nav-stat-num {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--purple);
  line-height: 1;
}

.nav-stat-lbl {
  font-size: 0.65rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.hero-panel {
  background: linear-gradient(
    135deg,
    rgba(124, 58, 237, 0.18) 0%,
    rgba(37, 99, 235, 0.14) 50%,
    rgba(6, 182, 212, 0.10) 100%
  );
  border: 1px solid rgba(124, 58, 237, 0.25);
  border-radius: 20px;
  padding: 2.4rem 2.8rem;
  margin-bottom: 2.5rem;
  position: relative;
  overflow: hidden;
}

/* Decorative radial blobs behind hero content */
.hero-panel::before {
  content: '';
  position: absolute;
  top: -60px; right: -60px;
  width: 250px; height: 250px;
  background: radial-gradient(circle, rgba(124, 58, 237, .12) 0%, transparent 70%);
  border-radius: 50%;
}

.hero-panel::after {
  content: '';
  position: absolute;
  bottom: -40px; left: 30%;
  width: 180px; height: 180px;
  background: radial-gradient(circle, rgba(6, 182, 212, .08) 0%, transparent 70%);
  border-radius: 50%;
}

.hero-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--cyan);
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin-bottom: 0.55rem;
}

.hero-heading {
  font-size: 1.8rem;
  font-weight: 800;
  line-height: 1.2;
  margin-bottom: 0.4rem;
  color: var(--text);
}

.hero-heading span {
  background: linear-gradient(135deg, #a78bfa 0%, #60a5fa 70%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-sub {
  font-size: 0.88rem;
  color: var(--muted);
  margin-bottom: 0;
}


.stSelectbox > div > div {
  background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
  color: var(--text) !important;
  font-size: 1rem !important;
  font-family: 'Poppins', sans-serif !important;
}

.stSelectbox label {
  color: var(--muted) !important;
  font-size: 0.75rem !important;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

div.stButton > button,
div.stFormSubmitButton > button {
  background: linear-gradient(135deg, var(--purple) 0%, var(--blue) 100%) !important;
  color: #fff !important;
  font-weight: 700 !important;
  font-size: 0.9rem !important;
  border: none !important;
  border-radius: 10px !important;
  padding: 0.65rem 1.6rem !important;
  letter-spacing: 0.04em;
  font-family: 'Poppins', sans-serif !important;
  transition: transform 0.15s, box-shadow 0.15s !important;
  width: 100%;
  box-shadow: 0 4px 15px rgba(124, 58, 237, 0.35) !important;
}

div.stButton > button:hover,
div.stFormSubmitButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 25px rgba(124, 58, 237, 0.55) !important;
}

.stTabs [data-baseweb="tab-list"] {
  background: var(--surface) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  gap: 3px !important;
  border: 1px solid var(--border) !important;
}

.stTabs [data-baseweb="tab"] {
  color: var(--muted) !important;
  font-family: 'Poppins', sans-serif !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  border-radius: 9px !important;
  padding: 0.45rem 1.3rem !important;
  border: none !important;
}

.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, var(--purple) 0%, var(--blue) 100%) !important;
  color: #fff !important;
  font-weight: 700 !important;
  box-shadow: 0 3px 12px rgba(124, 58, 237, 0.45) !important;
}

/* Spinner accent colour */
.stSpinner > div { border-top-color: var(--purple) !important; }

/* Horizontal rule */
hr { border-color: var(--border) !important; }

.sec-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 2.2rem 0 1.2rem;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid var(--border);
}

.sec-head-bar {
  width: 4px;
  height: 1.3rem;
  border-radius: 2px;
  background: linear-gradient(to bottom, var(--purple), var(--cyan));
}

.sec-head-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text);
}

.sec-head-count {
  margin-left: auto;
  font-size: 0.72rem;
  color: var(--muted);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 2px 10px;
}

.mc {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  position: relative;
  margin-bottom: 0.5rem;
  transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
  cursor: pointer;
}

/* Hover lift + glow effect */
.mc:hover {
  transform: translateY(-7px) scale(1.025);
  border-color: var(--purple);
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(124, 58, 237, 0.5);
}

/* Poster image */
.mc img {
  width: 100%;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  display: block;
  background: var(--surface);
}

/* Bottom gradient title bar (visible at rest) */
.mc-title-bar {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  background: linear-gradient(to top, rgba(7,7,15,0.95) 0%, rgba(7,7,15,0.6) 60%, transparent 100%);
  padding: 2rem 0.75rem 0.75rem;
  transition: opacity 0.3s ease;
}

/* Full overlay (visible on hover) */
.mc-overlay {
  position: absolute;
  top: 0; bottom: 0; left: 0; right: 0;
  background: rgba(7, 7, 15, 0.92);
  backdrop-filter: blur(4px);
  padding: 1.2rem 1rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

/* On hover: hide title bar, show overlay */
.mc:hover .mc-title-bar { opacity: 0; }
.mc:hover .mc-overlay   { opacity: 1; }

/* Card text styles */
.mc-title-truncate {
  font-size: 0.78rem;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 3px;
  line-height: 1.3;
}

.mc-title    { font-size: 0.9rem; font-weight: 700; color: #fff; margin-bottom: 4px; line-height: 1.2; }
.mc-rating   { font-size: 0.7rem; color: var(--gold); font-weight: 700; }
.mc-cast     { font-size: 0.65rem; color: var(--cyan); margin-bottom: 8px; line-height: 1.3; }

.mc-overview {
  font-size: 0.65rem;
  color: #d1d1e0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Genre badge (top-right corner of card) */
.mc-genre-tag {
  position: absolute;
  top: 8px; right: 8px;
  background: rgba(124, 58, 237, 0.8);
  backdrop-filter: blur(4px);
  border-radius: 6px;
  padding: 2px 7px;
  font-size: 0.6rem;
  font-weight: 600;
  color: #fff;
  letter-spacing: 0.05em;
}

.feature-strip {
  background: linear-gradient(135deg, var(--card) 0%, rgba(124, 58, 237, 0.08) 100%);
  border: 1px solid var(--border2);
  border-radius: 16px;
  padding: 1.2rem 1.5rem;
  margin-bottom: 1.8rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* Pulsing dot indicator */
.feature-strip-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--purple), var(--cyan));
  flex-shrink: 0;
  box-shadow: 0 0 8px rgba(124, 58, 237, 0.7);
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%,  100% { box-shadow: 0 0  8px rgba(124, 58, 237, 0.7); }
  50%        { box-shadow: 0 0 18px rgba(124, 58, 237, 1.0); }
}

.feature-strip-text   { font-size: 0.9rem; color: var(--muted); }
.feature-strip-text b { color: var(--text); }

.site-footer {
  text-align: center;
  color: var(--muted);
  font-size: 0.72rem;
  padding: 2rem 0 1rem;
  border-top: 1px solid var(--border);
  margin-top: 3rem;
  letter-spacing: 0.05em;
}

.site-footer span { color: var(--purple); }

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 ─ FILE PATH CONSTANTS
# Resolve all data / model paths relative to this script's directory so the
# app works regardless of the working directory when launched.
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR        = os.path.join(BASE_DIR, "models")
MOVIE_DICT_PATH   = os.path.join(MODELS_DIR, "movie_dict.pkl")
SIMILARITY_PATH   = os.path.join(MODELS_DIR, "similarity.pkl")
POSTER_CACHE_PATH = os.path.join(MODELS_DIR, "poster_cache.pkl")

def get_csv_path(name):
    p = os.path.join(BASE_DIR, "data", name)
    return p if os.path.exists(p) else os.path.join(BASE_DIR, name)

MOVIES_CSV  = get_csv_path("tmdb_5000_movies.csv")
CREDITS_CSV = get_csv_path("tmdb_5000_credits.csv")
TMDB_KEY    = os.environ.get("TMDB_API_KEY", "")
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
NO_POSTER   = "https://via.placeholder.com/300x450/14142a/7c3aed?text=No+Image"

# STEP 8 ─ SAFETY GUARD


if not os.path.exists(MOVIE_DICT_PATH) or not os.path.exists(SIMILARITY_PATH):
    st.error("⚠️  Run `python model_builder.py` first.")
    st.stop()

# STEP 9 ─ LOAD ML MODEL (cached)


@st.cache_resource
def load_model():  # type: ignore
    m   = pd.DataFrame(pickle.load(open(MOVIE_DICT_PATH, "rb")))
    sim = pickle.load(open(SIMILARITY_PATH, "rb"))
    return m, sim

movies, similarity = load_model()

# STEP 10 ─ POSTER CACHE


_pc: dict = {}
if os.path.exists(POSTER_CACHE_PATH):
    try:    _pc = pickle.load(open(POSTER_CACHE_PATH, "rb"))
    except: pass

# STEP 11 ─ POSTER FETCHER


def get_poster(movie_id: int) -> str:  # type: ignore
    cached = _pc.get(movie_id)
    if isinstance(cached, str) and cached.startswith("http") and "tmdb" in cached:
        return cached
    try:
        r    = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_KEY}", timeout=8).json()
        path = r.get("poster_path")
        url  = (POSTER_BASE + path) if path else NO_POSTER
    except:
        url = NO_POSTER
    _pc[movie_id] = url
    try: pickle.dump(_pc, open(POSTER_CACHE_PATH, "wb"))
    except: pass
    return url

@st.cache_resource
def build_lookup():  # type: ignore
    rm = pd.read_csv(MOVIES_CSV)
    rc = pd.read_csv(CREDITS_CSV)
    mg = rm.merge(rc, left_on="id", right_on="movie_id", how="left")
    def sp(t):
        try:   return ast.literal_eval(str(t))
        except: return []
    def si(v):
        try:   return int(float(v)) if pd.notna(v) else 0
        except: return 0
    def sf(v):
        try:   return round(float(v), 1) if pd.notna(v) else 0.0
        except: return 0.0
    lk = {}
    for _, row in mg.iterrows():
        mid = si(row.get("id") or 0)
        if not mid: continue
        lk[mid] = {
            "title"       : str(row.get("title_x") or row.get("title") or "").strip() or "Unknown",
            "rating"      : sf(row.get("vote_average")),
            "release_date": str(row.get("release_date") or "").strip() or "Unknown",
            "overview"    : str(row.get("overview") or "").strip() or "No description.",
            "genres"      : [g["name"] for g in sp(row.get("genres", "[]"))],
            "directors"   : [c["name"] for c in sp(row.get("crew", "[]")) if c.get("job") == "Director"],
            "cast"        : [c["name"] for c in sp(row.get("cast", "[]"))[:5]],
            "runtime"     : si(row.get("runtime")),
            "tagline"     : str(row.get("tagline") or "").strip(),
            "vote_count"  : si(row.get("vote_count")),
        }
    return lk

local_lookup = build_lookup()  # type: ignore

# STEP 13 ─ HELPER: GET MOVIE DETAILS

def get_details(movie_id, fallback=""):  # type: ignore
    d = local_lookup.get(int(movie_id))
    if d: return d
    return {"title": fallback or "Unknown", "rating": 0, "release_date": "Unknown",
            "overview": "No description.", "genres": [], "directors": [], "cast": [],
            "runtime": 0, "tagline": "", "vote_count": 0}

# STEP 14 ─ RECOMMENDATION ENGINE

def recommend(movie, n=10):  # type: ignore
    idx    = movies[movies["title"] == movie].index[0]
    pos    = movies.index.get_loc(idx)
    scores = list(enumerate(similarity[pos]))
    top    = sorted(scores, key=lambda x: x[1], reverse=True)[1:n+1]
    return [{"title": movies.iloc[i]["title"], "movie_id": int(movies.iloc[i]["movie_id"])}
            for i, _ in top]

# STEP 15 ─ SESSION STATE INITIALISATION

for k, v in [
    ("recs", []),
    ("searched_for", None),
    ("logged_in", False),
    ("users_db", {"admin@cinematrix.com": "password"}),
    ("search_history", []),
    ("user_profile", {"name": "", "genres": []}),
    ("show_account", False),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# STEP 16 ─ GOOGLE OAUTH CALLBACK HANDLER

if not st.session_state.logged_in:
    _code  = st.query_params.get("code",  None)
    _state = st.query_params.get("state", None)

    if _code:
        st.query_params.clear()          # clean up URL immediately
        if _state and _verify_state(_state):
            with st.spinner("🔐 Signing you in with Google…"):
                user_info = exchange_code_for_user(_code)
            if user_info and user_info.get("email"):
                st.session_state.logged_in = True
                if not st.session_state.user_profile.get("name"):
                    st.session_state.user_profile["name"] = user_info.get("name", "")
                ek = user_info["email"]
                if ek not in st.session_state.users_db:
                    st.session_state.users_db[ek] = "__google_oauth__"
                st.rerun()
            else:
                st.error("Google sign-in failed — please try again.")
        else:
            st.error("Sign-in link expired. Please click 'Continue with Google' again.")

# STEP 17 ─ LOGIN / SIGN-UP PAGE

if not st.session_state.logged_in:
    st.markdown("""
    <div style="text-align:center;padding:4rem 0;">
      <div style="font-size:3.5rem;margin-bottom:1rem">🎬</div>
      <div style="font-size:2rem;font-weight:800;color:#a78bfa;margin-bottom:0.5rem">Welcome to CineMatrix</div>
      <div style="font-size:1rem;color:#6b7194;margin-bottom:2rem">Please log in to continue</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
            google_url = make_google_auth_url()
            st.markdown(f"""
            <a href="{google_url}" style="text-decoration:none;display:block;margin-bottom:0.75rem">
              <div style="display:flex;align-items:center;justify-content:center;gap:12px;
                background:#fff;color:#3c4043;border:1px solid #dadce0;border-radius:10px;
                padding:0.65rem 1.4rem;font-family:'Poppins',sans-serif;font-size:0.92rem;
                font-weight:600;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,0.18);">
                <svg width="20" height="20" viewBox="0 0 48 48">
                  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                </svg>
                Continue with Google
              </div>
            </a>
            <div style="display:flex;align-items:center;gap:8px;margin:0.5rem 0 0.75rem">
              <div style="flex:1;height:1px;background:#2a2a50"></div>
              <span style="color:#6b7194;font-size:0.75rem">or use email</span>
              <div style="flex:1;height:1px;background:#2a2a50"></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("💡 Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in your `.env`.", icon="ℹ️")

        # ── Email login / sign-up tabs ────────────────────────────────────────
        tab_login, tab_signup = st.tabs(["Log In", "Create Account"])

        # Login tab
        with tab_login:
            import re as _re
            email    = st.text_input("Email", key="login_email", placeholder="name@example.com")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Log In", use_container_width=True):
                _v = bool(_re.match(r"^[\w.%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}$", email.strip()))
                if not email or not password:     st.error("❌ Enter email and password.")
                elif not _v:                      st.error("❌ Enter a valid email e.g. name@gmail.com")
                elif st.session_state.users_db.get(email.strip().lower()) == password:
                    st.session_state.logged_in = True; st.rerun()
                else:                             st.error("❌ Incorrect email or password.")

        # Sign-up tab
        with tab_signup:
            import re as _re
            ne = st.text_input("Email",            key="signup_email",   placeholder="name@example.com")
            np = st.text_input("Password",         type="password", key="signup_pass",    placeholder="At least 6 characters")
            cp = st.text_input("Confirm Password", type="password", key="signup_confirm", placeholder="Re-enter password")
            if st.button("Create Account", use_container_width=True):
                _ep = r"^[\w.%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}$"
                if not ne or not np:                          st.warning("⚠️ Fill all fields.")
                elif not _re.match(_ep, ne.strip()):          st.error("❌ Invalid email.")
                elif len(np) < 6:                             st.error("❌ Password too short (min 6).")
                elif np != cp:                                st.error("❌ Passwords don't match.")
                elif ne.strip().lower() in st.session_state.users_db: st.error("❌ Email already registered.")
                else:
                    st.session_state.users_db[ne.strip().lower()] = np
                    st.success("✅ Account created! You can now log in.")
    st.stop()

# STEP 18 ─ TOP NAVIGATION BAR

st.markdown(f"""
<div class="navbar">
  <div class="nav-brand">
    <div class="nav-brand-icon">🎬</div>
    <div>
      <div class="nav-brand-text">CineMatrix</div>
      <div class="nav-subtitle">Movie Intelligence</div>
    </div>
  </div>
  <div class="nav-stats">
    <div class="nav-stat">
      <div class="nav-stat-num">{len(movies):,}</div>
      <div class="nav-stat-lbl">Movies</div>
    </div>
    <div class="nav-stat">
      <div class="nav-stat-num">ML</div>
      <div class="nav-stat-lbl">Powered</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 19 ─ ACCOUNT / LOGOUT BUTTONS (top-right area)
# ─────────────────────────────────────────────────────────────────────────────

col_space, col_account, col_logout = st.columns([7.2, 1.6, 1.2])
with col_account:
    lbl = f"👋 Hi, {st.session_state.user_profile['name']}" if st.session_state.user_profile.get("name") else "👤 Account"
    if st.button(lbl, use_container_width=True):
        st.session_state.show_account = not st.session_state.show_account; st.rerun()
with col_logout:
    if st.button("Log Out", use_container_width=True):
        st.session_state.logged_in = False; st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 20 ─ ACCOUNT PANEL (collapsible)
# Shows display name editor, favourite genre selector, and recent search
# history. Toggled by the Account button above.
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.show_account:
    with st.container(border=True):
        st.markdown("### 👤 Account Details & Preferences")
        c1, c2 = st.columns(2)
        with c1:
            nn = st.text_input("Display Name", value=st.session_state.user_profile.get("name",""))
            ag = sorted(["Action","Adventure","Animation","Comedy","Crime","Documentary","Drama",
                         "Family","Fantasy","History","Horror","Music","Mystery","Romance",
                         "Science Fiction","TV Movie","Thriller","War","Western"])
            ng = st.multiselect("Favorite Genres", ag, default=st.session_state.user_profile.get("genres",[]))
            if st.button("Save Profile"):
                st.session_state.user_profile.update({"name":nn,"genres":ng})
                st.session_state.show_account = False
                st.toast("Profile saved!", icon="✅"); st.rerun()
        with c2:
            st.markdown("**📜 Recent Search History**")
            if st.session_state.search_history:
                for s in reversed(st.session_state.search_history[-8:]):
                    st.markdown(f"- 🎬 {s}")
            else:
                st.info("No searches yet.")
    st.markdown("<br>", unsafe_allow_html=True)

# STEP 21 ─ MAIN TABS

tab_home, tab_analytics = st.tabs(["🎬 Recommended", "📊 Analytics & Charts"])

# TAB A ─ RECOMMENDATIONS

with tab_home:

    # ── Hero banner ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-panel">
      <div class="hero-label">AI-Powered</div>
      <div class="hero-heading">Find Movies You'll <span>Love</span></div>
      <div class="hero-sub">Pick a film and we'll find your perfect match</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Movie selector + Recommend button ─────────────────────────────────────
    col_sel, col_btn = st.columns([5, 1])
    with col_sel:
        selected = st.selectbox("", movies["title"].values, label_visibility="collapsed", placeholder="🔍 Type or pick a movie…")
    with col_btn:
        go = st.button("✦ Recommend", use_container_width=True)

    # ── Trigger recommendation on button click ────────────────────────────────
    if go:
        with st.spinner("Analysing patterns & fetching posters…"):
            recs = recommend(selected, n=10)
            for r in recs: get_poster(r["movie_id"])
            st.session_state.recs = recs
            st.session_state.searched_for = selected
            if selected in st.session_state.search_history:
                st.session_state.search_history.remove(selected)
            st.session_state.search_history.append(selected)

    # ── Render recommendation grid ────────────────────────────────────────────
    if st.session_state.recs:
        base         = st.session_state.searched_for
        base_details = get_details(
            movies[movies["title"]==base]["movie_id"].values[0] if base in movies["title"].values else 0,
            fallback=base)
        gp = ", ".join(base_details.get("genres",[])[:3]) or "Mixed"

        # Context strip showing which movie was used as the seed
        st.markdown(f"""
        <div class="feature-strip">
          <div class="feature-strip-dot"></div>
          <div class="feature-strip-text">
            CineMatrix Intelligence — <b>10 Similar Picks for {base}</b>
            &nbsp;·&nbsp; Genres: {gp}
          </div>
        </div>""", unsafe_allow_html=True)

        # ── Inner helper: render a row of 5 movie cards ───────────────────────
        def render_row(recs_slice, heading, count_label, key_prefix):
            st.markdown(f"""
            <div class="sec-head">
              <div class="sec-head-bar"></div>
              <div class="sec-head-title">{heading}</div>
              <div class="sec-head-count">{count_label}</div>
            </div>""", unsafe_allow_html=True)

            for idx, (col, rec) in enumerate(zip(st.columns(5, gap="small"), recs_slice)):
                with col:
                    d  = get_details(rec["movie_id"], fallback=rec["title"])
                    pu = get_poster(rec["movie_id"])
                    gt = d["genres"][0] if d["genres"] else ""

                    # Poster image or fallback placeholder
                    ih = (f'<img src="{pu}" alt="{d["title"]}" loading="lazy">'
                          if pu != NO_POSTER else
                          '<div style="aspect-ratio:2/3;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#12121a,#1a1a26)"><div style="font-size:1.5rem;font-weight:700;color:#f5c518;text-align:center">Movie<br>🎬</div></div>')

                    cs = ", ".join(d["cast"][:3]) if d.get("cast") else "Unknown"

                    # Movie card HTML (poster + title bar + hover overlay)
                    st.markdown(f"""<div class="mc">{ih}
                      {'<div class="mc-genre-tag">'+gt+'</div>' if gt else ''}
                      <div class="mc-title-bar">
                        <div class="mc-title-truncate">{d['title']}</div>
                        <div class="mc-rating">⭐ {d['rating']}</div>
                      </div>
                      <div class="mc-overlay">
                        <div class="mc-title">{d['title']}</div>
                        <div class="mc-rating" style="margin-bottom:8px">⭐ {d['rating']} &nbsp;•&nbsp; ⏳ {d['runtime']}m</div>
                        <div class="mc-cast"><b>Cast:</b> {cs}</div>
                        <div class="mc-overview">{d['overview']}</div>
                      </div>
                    </div>""", unsafe_allow_html=True)

                    # "Details" button → navigates to movie_detail page
                    if st.button("Details", key=f"{key_prefix}_{idx}_{rec['movie_id']}", use_container_width=True):
                        d["poster"] = pu; st.session_state.detail_movie = d
                        st.switch_page("pages/movie_detail.py")

        # Render two rows of 5 cards each (10 recommendations total)
        render_row(st.session_state.recs[:5], f"Because you liked <em style='color:#a78bfa'>{base}</em>", "1–5 of 10", "r1")
        st.markdown("<div style='margin-top:2rem'></div>", unsafe_allow_html=True)
        render_row(st.session_state.recs[5:], "More You Might Like", "6–10 of 10", "r2")

# TAB B ─ ANALYTICS & CHARTS

with tab_analytics:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    st.markdown(
        '<div class="sec-head" style="margin-top:1.5rem">'
        '<div class="sec-head-bar"></div>'
        '<div class="sec-head-title">Dataset Analytics — TMDB 5,000 Movies</div>'
        '</div>',
        unsafe_allow_html=True
    )

    @st.cache_data
    def load_raw():
        df = pd.read_csv(MOVIES_CSV)
        df["year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year
        for c in ["budget","revenue","runtime","vote_average","vote_count"]:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    df_full = load_raw()

    fc1, fc2 = st.columns(2)
    with fc1: rr = st.slider("⭐ IMDb Rating Range", 0.0, 10.0, (0.0, 10.0), 0.5)
    with fc2:
        ym, yx = int(df_full["year"].min(skipna=True)), int(df_full["year"].max(skipna=True))
        yr = st.slider("📅 Release Year", ym, yx, (ym, yx))

    df = df_full[
        (df_full["vote_average"] >= rr[0]) &
        (df_full["vote_average"] <= rr[1]) &
        (df_full["year"] >= yr[0]) &
        (df_full["year"] <= yr[1])
    ]

    k1, k2, k3, k4, k5 = st.columns(5)
    ks = "background:var(--card);border:1px solid var(--border2);border-radius:12px;padding:.9rem 1rem;text-align:center"
    kv = "font-size:1.6rem;font-weight:800;color:var(--purple);font-family:'Poppins',sans-serif"
    kl = "font-size:0.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-top:2px"

    k1.markdown(f'<div style="{ks}"><div style="{kv}">{len(df):,}</div><div style="{kl}">Total Movies</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div style="{ks}"><div style="{kv}">{df["vote_average"].mean():.1f}</div><div style="{kl}">Avg Rating</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div style="{ks}"><div style="{kv}">{int(df["runtime"].median())}m</div><div style="{kl}">Median Runtime</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div style="{ks}"><div style="{kv}">{int(df["year"].max())}</div><div style="{kl}">Latest Year</div></div>', unsafe_allow_html=True)
    k5.markdown(f'<div style="{ks}"><div style="{kv}">{df["vote_count"].sum()//1_000_000:.0f}M</div><div style="{kl}">Total Votes</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    def genre_counts(dataframe):
        gc = {}
        for raw in dataframe["genres"].dropna():
            try:
                for g in ast.literal_eval(raw): gc[g["name"]] = gc.get(g["name"], 0) + 1
            except: pass
        return pd.DataFrame(sorted(gc.items(), key=lambda x: x[1], reverse=True), columns=["Genre", "Count"])

    gdf   = genre_counts(df)
    top10 = gdf.head(10) if not gdf.empty else pd.DataFrame(columns=["Genre", "Count"])

    # Shared Plotly dark theme kwargs
    _pc_kw = dict(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=30, b=0)
    )

    # Chart 1: Top Genres | Rating Distribution
    ca, cb = st.columns([3, 2])

    with ca:
        st.markdown('<div class="sec-head"><div class="sec-head-bar"></div><div class="sec-head-title">🎭 Top 10 Genres</div></div>', unsafe_allow_html=True)
        if not top10.empty:
            fig = px.bar(top10.sort_values("Count", ascending=True), x="Count", y="Genre",
                         orientation="h", text="Count", color_discrete_sequence=["#7c3aed"])
            fig.update_traces(textposition="outside")
            fig.update_layout(**_pc_kw, xaxis_title="Number of Movies", yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

    with cb:
        st.markdown('<div class="sec-head"><div class="sec-head-bar"></div><div class="sec-head-title">⭐ Rating Distribution</div></div>', unsafe_allow_html=True)
        if not df.empty:
            fig = px.histogram(df.dropna(subset=["vote_average"]), x="vote_average", nbins=20, color_discrete_sequence=["#7c3aed"])
            mv  = df["vote_average"].mean()
            fig.add_vline(x=mv, line_dash="dash", line_color="#f59e0b", annotation_text=f"Mean:{mv:.1f}")
            fig.update_layout(**_pc_kw, xaxis_title="IMDb Rating", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

    # Chart 2: Movies per Year | Genre Pie
    cc, cd = st.columns([3, 2])

    with cc:
        st.markdown('<div class="sec-head"><div class="sec-head-bar"></div><div class="sec-head-title">📅 Movies per Year</div></div>', unsafe_allow_html=True)
        ydf = (df[df["year"].between(1990, 2017)]
               .groupby("year")
               .agg(count=("title", "count"), avg_rating=("vote_average", "mean"))
               .reset_index())
        if not ydf.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=ydf["year"], y=ydf["count"],   fill="tozeroy", name="Movies",     line=dict(color="#7c3aed")),         secondary_y=False)
            fig.add_trace(go.Scatter(x=ydf["year"], y=ydf["avg_rating"],              name="Avg Rating", line=dict(color="#f59e0b", dash="dash")), secondary_y=True)
            fig.update_layout(**_pc_kw, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig.update_yaxes(title_text="# Movies",   secondary_y=False)
            fig.update_yaxes(title_text="Avg Rating", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)

    with cd:
        st.markdown('<div class="sec-head"><div class="sec-head-bar"></div><div class="sec-head-title">🍕 Genre Share</div></div>', unsafe_allow_html=True)
        p8 = gdf.head(8)
        if not p8.empty:
            fig = px.pie(p8, values="Count", names="Genre", hole=0.52,
                         color_discrete_sequence=["#7c3aed","#2563eb","#06b6d4","#10b981","#f59e0b","#ec4899","#6d28d9","#1d4ed8"])
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(**_pc_kw, showlegend=False,
                              annotations=[dict(text=f'{p8["Count"].sum():,}<br>films', x=0.5, y=0.5,
                                                font_size=14, showarrow=False, font_color="#a78bfa")])
            st.plotly_chart(fig, use_container_width=True)

    # Chart 3: Runtime vs Rating | Budget vs Revenue
    ce, cf = st.columns(2)

    with ce:
        st.markdown('<div class="sec-head"><div class="sec-head-bar"></div><div class="sec-head-title">⏱ Runtime vs Rating</div></div>', unsafe_allow_html=True)
        sc = df[["runtime","vote_average","title"]].dropna()
        sc = sc[(sc["runtime"] > 40) & (sc["runtime"] < 240)]
        if not sc.empty:
            fig = px.scatter(sc, x="runtime", y="vote_average", color="vote_average",
                             hover_name="title", color_continuous_scale="plasma", opacity=0.7)
            fig.update_layout(**_pc_kw, xaxis_title="Runtime (min)", yaxis_title="Rating")
            st.plotly_chart(fig, use_container_width=True)

    with cf:
        st.markdown('<div class="sec-head"><div class="sec-head-bar"></div><div class="sec-head-title">💰 Budget vs Revenue</div></div>', unsafe_allow_html=True)
        bvr = df[(df["budget"] > 1e6) & (df["revenue"] > 1e6)].copy()
        if not bvr.empty:
            fig = px.scatter(bvr, x="budget", y="revenue", color="vote_average",
                             hover_name="title", color_continuous_scale="plasma",
                             log_x=True, log_y=True, opacity=0.7)
            mn, mx = min(bvr["budget"].min(), bvr["revenue"].min()), max(bvr["budget"].max(), bvr["revenue"].max())
            fig.add_shape(type="line", x0=mn, y0=mn, x1=mx, y1=mx,
                          line=dict(color="#f59e0b", dash="dash", width=1))
            fig.update_layout(**_pc_kw, xaxis_title="Budget ($)", yaxis_title="Revenue ($)")
            st.plotly_chart(fig, use_container_width=True)

    #  Top-10 leaderboard table 
    st.markdown(
        '<div class="sec-head" style="margin-top:1rem">'
        '<div class="sec-head-bar"></div>'
        '<div class="sec-head-title">🏆 Top 10 Movies (Filtered)</div>'
        '</div>',
        unsafe_allow_html=True
    )

    mv_req  = 500 if len(df) > 500 else 10
    top10f  = (df[df["vote_count"] >= mv_req]
               .nlargest(10, "vote_average")
               [["title","vote_average","vote_count","year"]]
               .reset_index(drop=True))
    top10f.index += 1
    top10f.columns = ["Title","Rating","Votes","Year"]
    top10f["Year"] = top10f["Year"].astype("Int64")

    rh = "" if not top10f.empty else '<tr><td colspan="5" style="padding:1rem;text-align:center;color:#6b7194">No movies match.</td></tr>'

    for i, row in top10f.iterrows():
        bw  = int(row["Rating"] / 10 * 100)
        rh += (
            f'<tr style="border-bottom:1px solid #1e1e38">'
            f'<td style="padding:.55rem .7rem;color:#a78bfa;font-weight:700">{i}</td>'
            f'<td style="padding:.55rem .7rem;color:#f1f0ff;font-weight:500">{row["Title"]}</td>'
            f'<td style="padding:.55rem .7rem">'
            f'  <div style="display:flex;align-items:center;gap:8px">'
            f'    <div style="width:80px;background:#1e1e38;border-radius:4px;height:6px;overflow:hidden">'
            f'      <div style="width:{bw}%;background:linear-gradient(90deg,#7c3aed,#06b6d4);height:100%;border-radius:4px"></div>'
            f'    </div>'
            f'    <span style="color:#f59e0b;font-weight:700;font-size:.82rem">{row["Rating"]}</span>'
            f'  </div>'
            f'</td>'
            f'<td style="padding:.55rem .7rem;color:#6b7194;font-size:.82rem">{row["Votes"]:,}</td>'
            f'<td style="padding:.55rem .7rem;color:#6b7194;font-size:.82rem">{row["Year"]}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<div style="background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden">'
        f'<table style="width:100%;border-collapse:collapse;font-family:\'Poppins\',sans-serif;font-size:.85rem">'
        f'<thead>'
        f'<tr style="background:#0f0f1c;border-bottom:2px solid #2a2a50">'
        f'<th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">#</th>'
        f'<th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Title</th>'
        f'<th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Rating</th>'
        f'<th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Votes</th>'
        f'<th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Year</th>'
        f'</tr></thead>'
        f'<tbody>{rh}</tbody>'
        f'</table></div>',
        unsafe_allow_html=True
    )

# SITE FOOTER

st.markdown(
    '<div class="site-footer">'
    '<span>CineMatrix</span> &nbsp;·&nbsp; Powered by TMDB &nbsp;
    '</div>',
    unsafe_allow_html=True
)
