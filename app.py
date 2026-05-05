import os, subprocess, sys, streamlit as st

if not os.path.exists("models/similarity.pkl") or \
   not os.path.exists("models/movie_dict.pkl"):
    with st.spinner("⏳ Building model — first time only, ~60 seconds..."):
        subprocess.run([sys.executable, "model_builder.py"], check=True)
    st.rerun()
  
import os, pickle, ast, requests, urllib.parse
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── Google OAuth ─────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"

def make_google_auth_url() -> str:
    # FIXED: Use a fixed state string instead of a random one stored in
    # session_state. When Google redirects back to localhost:8501, Streamlit
    # creates a BRAND NEW session — the old session_state["oauth_state"] is
    # completely gone. A fixed known string survives this redirect perfectly.
    state = "cinematrix_oauth_ok"
    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "prompt":        "select_account",
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)

def exchange_code_for_user(code: str):
    """Exchange auth code → access token → user-info dict."""
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
        info = requests.get(GOOGLE_USERINFO,
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=8).json()
        return info   # keys: sub, email, name, picture
    except Exception:
        return None
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CineMatrix",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap');

/* ── PALETTE ── */
:root {
  --bg:        #07070f;
  --surface:   #0f0f1c;
  --card:      #14142a;
  --border:    #1e1e38;
  --border2:   #2a2a50;
  --purple:    #7c3aed;
  --purple2:   #6d28d9;
  --blue:      #2563eb;
  --cyan:      #06b6d4;
  --pink:      #ec4899;
  --gold:      #f59e0b;
  --green:     #10b981;
  --text:      #f1f0ff;
  --muted:     #6b7194;
  --radius:    14px;
}

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Poppins', sans-serif !important; }
.stApp              { background: var(--bg) !important; color: var(--text); }
.block-container    { padding: 0 2.5rem 4rem !important; max-width: 1380px; }
#MainMenu, footer, header { visibility: hidden; }
section[data-testid="stSidebar"] { display: none !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 0 1rem;
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--border);
}
.nav-brand {
  display: flex; align-items: center; gap: 10px;
  font-size: 1.5rem; font-weight: 900; letter-spacing: -0.02em;
}
.nav-brand-icon {
  width: 38px; height: 38px;
  background: linear-gradient(135deg, var(--purple) 0%, var(--blue) 100%);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem;
  box-shadow: 0 4px 15px rgba(124,58,237,0.45);
}
.nav-brand-text {
  background: linear-gradient(135deg, #a78bfa 0%, #60a5fa 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.nav-subtitle { font-size: 0.72rem; color: var(--muted); letter-spacing: 0.1em; text-transform: uppercase; }
.nav-stats {
  display: flex; gap: 2rem; align-items: center;
}
.nav-stat { text-align: center; }
.nav-stat-num { font-size: 1.1rem; font-weight: 800; color: var(--purple); line-height: 1; }
.nav-stat-lbl { font-size: 0.65rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }

.hero-panel {
  background: linear-gradient(135deg,
    rgba(124,58,237,0.18) 0%,
    rgba(37,99,235,0.14) 50%,
    rgba(6,182,212,0.10) 100%);
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: 20px;
  padding: 2.4rem 2.8rem;
  margin-bottom: 2.5rem;
  position: relative;
  overflow: hidden;
}
.hero-panel::before {
  content: '';
  position: absolute; top: -60px; right: -60px;
  width: 250px; height: 250px;
  background: radial-gradient(circle, rgba(124,58,237,.12) 0%, transparent 70%);
  border-radius: 50%;
}
.hero-panel::after {
  content: '';
  position: absolute; bottom: -40px; left: 30%;
  width: 180px; height: 180px;
  background: radial-gradient(circle, rgba(6,182,212,.08) 0%, transparent 70%);
  border-radius: 50%;
}
.hero-label {
  font-size: 0.72rem; font-weight: 600; color: var(--cyan);
  text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.55rem;
}
.hero-heading {
  font-size: 1.8rem; font-weight: 800; line-height: 1.2; margin-bottom: 0.4rem;
  color: var(--text);
}
.hero-heading span {
  background: linear-gradient(135deg, #a78bfa 0%, #60a5fa 70%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-sub { font-size: 0.88rem; color: var(--muted); margin-bottom: 0; }

/* Selectbox */
.stSelectbox > div > div {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
  color: var(--text) !important;
  font-size: 1rem !important;
  font-family: 'Poppins', sans-serif !important;
}
.stSelectbox label { color: var(--muted) !important; font-size: 0.75rem !important;
  text-transform: uppercase; letter-spacing: 0.1em; }

/* ALL BUTTONS → gold  (overridden per-button with unique containers below) */
div.stButton > button, div.stFormSubmitButton > button {
  background: linear-gradient(135deg, var(--purple) 0%, var(--blue) 100%) !important;
  color: #fff !important; font-weight: 700 !important; font-size: 0.9rem !important;
  border: none !important; border-radius: 10px !important;
  padding: 0.65rem 1.6rem !important; letter-spacing: 0.04em;
  font-family: 'Poppins', sans-serif !important;
  transition: transform 0.15s, box-shadow 0.15s !important;
  width: 100%;
  box-shadow: 0 4px 15px rgba(124,58,237,0.35) !important;
}
div.stButton > button:hover, div.stFormSubmitButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 25px rgba(124,58,237,0.55) !important;
}

/* Tabs */
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
  font-size: 0.85rem !important; font-weight: 500 !important;
  border-radius: 9px !important; padding: 0.45rem 1.3rem !important;
  border: none !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, var(--purple) 0%, var(--blue) 100%) !important;
  color: #fff !important; font-weight: 700 !important;
  box-shadow: 0 3px 12px rgba(124,58,237,0.45) !important;
}

/* Spinner */
.stSpinner > div { border-top-color: var(--purple) !important; }

/* HR */
hr { border-color: var(--border) !important; }

.sec-head {
  display: flex; align-items: center; gap: 12px;
  margin: 2.2rem 0 1.2rem;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid var(--border);
}
.sec-head-bar {
  width: 4px; height: 1.3rem; border-radius: 2px;
  background: linear-gradient(to bottom, var(--purple), var(--cyan));
}
.sec-head-title {
  font-size: 1.1rem; font-weight: 700; color: var(--text);
}
.sec-head-count {
  margin-left: auto;
  font-size: 0.72rem; color: var(--muted);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 20px; padding: 2px 10px;
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
.mc:hover {
  transform: translateY(-7px) scale(1.025);
  border-color: var(--purple);
  box-shadow: 0 18px 45px rgba(0,0,0,0.65), 0 0 0 1px rgba(124,58,237,0.5);
}
.mc img {
  width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block;
  background: var(--surface);
}
/* Default title bar */
.mc-title-bar {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: linear-gradient(to top, rgba(7,7,15,0.95) 0%, rgba(7,7,15,0.6) 60%, transparent 100%);
  padding: 2rem 0.75rem 0.75rem;
  transition: opacity 0.3s ease;
}
/* Expanded snippet on hover */
.mc-overlay {
  position: absolute; top: 0; bottom: 0; left: 0; right: 0;
  background: rgba(7, 7, 15, 0.92);
  backdrop-filter: blur(4px);
  padding: 1.2rem 1rem;
  display: flex; flex-direction: column; justify-content: center;
  opacity: 0; transition: opacity 0.3s ease;
}
.mc:hover .mc-title-bar { opacity: 0; }
.mc:hover .mc-overlay { opacity: 1; }

.mc-title-truncate {
  font-size: 0.78rem; font-weight: 600; color: #fff;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: 3px; line-height: 1.3;
}
.mc-title {
  font-size: 0.9rem; font-weight: 700; color: #fff;
  margin-bottom: 4px; line-height: 1.2;
}
.mc-rating { font-size: 0.7rem; color: var(--gold); font-weight: 700; }
.mc-cast { font-size: 0.65rem; color: var(--cyan); margin-bottom: 8px; line-height: 1.3; }
.mc-overview {
  font-size: 0.65rem; color: #d1d1e0; line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 5; -webkit-box-orient: vertical;
  overflow: hidden;
}
.mc-genre-tag {
  position: absolute; top: 8px; right: 8px;
  background: rgba(124,58,237,0.8); backdrop-filter: blur(4px);
  border-radius: 6px; padding: 2px 7px;
  font-size: 0.6rem; font-weight: 600; color: #fff; letter-spacing: 0.05em;
}

.feature-strip {
  background: linear-gradient(135deg, var(--card) 0%, rgba(124,58,237,0.08) 100%);
  border: 1px solid var(--border2);
  border-radius: 16px;
  padding: 1.2rem 1.5rem;
  margin-bottom: 1.8rem;
  display: flex; align-items: center; gap: 1rem;
}
.feature-strip-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: linear-gradient(135deg, var(--purple), var(--cyan));
  flex-shrink: 0;
  box-shadow: 0 0 8px rgba(124,58,237,0.7);
  animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
  0%,100%{ box-shadow: 0 0 8px rgba(124,58,237,0.7); }
  50%    { box-shadow: 0 0 18px rgba(124,58,237,1); }
}
.feature-strip-text { font-size: 0.9rem; color: var(--muted); }
.feature-strip-text b { color: var(--text); }

.site-footer {
  text-align: center; color: var(--muted); font-size: 0.72rem;
  padding: 2rem 0 1rem; border-top: 1px solid var(--border);
  margin-top: 3rem; letter-spacing: 0.05em;
}
.site-footer span { color: var(--purple); }

.analytics-link-card {
  background: linear-gradient(135deg, rgba(124,58,237,0.12) 0%, rgba(37,99,235,0.10) 100%);
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: 14px;
  padding: 1.1rem 1.5rem;
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 2rem;
  cursor: pointer;
}
.analytics-link-text { font-size: 0.88rem; color: #a78bfa; font-weight: 600; }
.analytics-link-sub  { font-size: 0.75rem; color: var(--muted); margin-top: 1px; }
</style>
""", unsafe_allow_html=True)

BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR        = os.path.join(BASE_DIR, 'models')
MOVIE_DICT_PATH   = os.path.join(MODELS_DIR, 'movie_dict.pkl')
SIMILARITY_PATH   = os.path.join(MODELS_DIR, 'similarity.pkl')
POSTER_CACHE_PATH = os.path.join(MODELS_DIR, 'poster_cache.pkl')

def get_csv_path(name):
    p = os.path.join(BASE_DIR, 'data', name)
    return p if os.path.exists(p) else os.path.join(BASE_DIR, name)

MOVIES_CSV  = get_csv_path('tmdb_5000_movies.csv')
CREDITS_CSV = get_csv_path('tmdb_5000_credits.csv')

TMDB_KEY        = os.environ.get('TMDB_API_KEY', 'cdf3a58aa720377a583f33c3e879377c')
TMDB_BASE       = 'https://api.themoviedb.org/3'
POSTER_BASE     = 'https://image.tmdb.org/t/p/w500'
NO_POSTER       = 'https://via.placeholder.com/300x450/14142a/7c3aed?text=No+Image'

if not os.path.exists(MOVIE_DICT_PATH) or not os.path.exists(SIMILARITY_PATH):
    st.error("⚠️  Run `python model_builder.py` first.")
    st.stop()

@st.cache_resource
def load_model(): # type: ignore
    m   = pd.DataFrame(pickle.load(open(MOVIE_DICT_PATH, 'rb')))
    sim = pickle.load(open(SIMILARITY_PATH, 'rb'))
    return m, sim

movies, similarity = load_model()

_pc: dict = {}
if os.path.exists(POSTER_CACHE_PATH):
    try:  _pc = pickle.load(open(POSTER_CACHE_PATH, 'rb'))
    except: pass

def get_poster(movie_id: int) -> str: # type: ignore
    cached = _pc.get(movie_id)
    # Valid string URL → use it immediately (fast path)
    if isinstance(cached, str) and cached.startswith('http') and 'tmdb' in cached:
        return cached
    # Stale old-format dict → ignore, re-fetch
    try:
        r    = requests.get(f"{POSTER_BASE.replace('/t/p/w500','/3')}/movie/{movie_id}?api_key={TMDB_KEY}", timeout=8).json()
        path = r.get('poster_path')
        url  = (POSTER_BASE + path) if path else NO_POSTER
    except:
        url = NO_POSTER
    _pc[movie_id] = url
    try: pickle.dump(_pc, open(POSTER_CACHE_PATH, 'wb'))
    except: pass
    return url

@st.cache_resource
def build_lookup(): # type: ignore
    rm = pd.read_csv(MOVIES_CSV)
    rc = pd.read_csv(CREDITS_CSV)
    mg = rm.merge(rc, left_on='id', right_on='movie_id', how='left')

    def sp(t):
        try:   return ast.literal_eval(str(t))
        except: return []
    def si(v):
        try:   return int(float(v)) if pd.notna(v) else 0
        except: return 0
    def sf(v):
        try:   return round(float(v),1) if pd.notna(v) else 0.0
        except: return 0.0

    lk = {}
    for _, row in mg.iterrows():
        mid = si(row.get('id') or 0)
        if not mid: continue
        lk[mid] = {
            "title"       : str(row.get('title_x') or row.get('title') or '').strip() or "Unknown",
            "rating"      : sf(row.get('vote_average')),
            "release_date": str(row.get('release_date') or '').strip() or "Unknown",
            "overview"    : str(row.get('overview') or '').strip() or "No description.",
            "genres"      : [g['name'] for g in sp(row.get('genres','[]'))],
            "directors"   : [c['name'] for c in sp(row.get('crew','[]')) if c.get('job')=='Director'],
            "cast"        : [c['name'] for c in sp(row.get('cast','[]'))[:5]],
            "runtime"     : si(row.get('runtime')),
            "tagline"     : str(row.get('tagline') or '').strip(),
            "vote_count"  : si(row.get('vote_count')),
        }
    return lk

local_lookup = build_lookup() # type: ignore

def get_details(movie_id, fallback=""): # type: ignore
    d = local_lookup.get(int(movie_id))
    if d: return d
    return {"title": fallback or "Unknown", "rating": 0, "release_date": "Unknown",
            "overview": "No description.", "genres": [], "directors": [], "cast": [],
            "runtime": 0, "tagline": "", "vote_count": 0}

def recommend(movie, n=10): # type: ignore
    idx    = movies[movies['title'] == movie].index[0]
    pos    = movies.index.get_loc(idx)
    scores = list(enumerate(similarity[pos]))
    top    = sorted(scores, key=lambda x: x[1], reverse=True)[1:n+1]
    return [{"title": movies.iloc[i]["title"], "movie_id": int(movies.iloc[i]["movie_id"])}
            for i, _ in top]

for k, v in [("recs",[]),("searched_for",None), ("logged_in", False), ("users_db", {"admin@cinematrix.com": "password"}), ("search_history", []), ("user_profile", {"name": "", "genres": []}), ("show_account", False)]:
    if k not in st.session_state: st.session_state[k] = v

if not st.session_state.logged_in:
    # ── Handle Google OAuth callback ─────────────────────────────────────────
    qp = st.query_params
    oauth_code  = qp.get("code")
    oauth_state = qp.get("state")
    if oauth_code:
        # FIXED: was checking oauth_state == st.session_state.get("oauth_state")
        # That ALWAYS fails because Google's redirect creates a brand new
        # Streamlit session — session_state is empty on return.
        # Now we check against the fixed string set in make_google_auth_url().
        if oauth_state == "cinematrix_oauth_ok":
            with st.spinner("🔐 Signing you in with Google…"):
                user_info = exchange_code_for_user(oauth_code)
            if user_info and user_info.get("email"):
                st.session_state.logged_in = True
                if not st.session_state.user_profile.get("name"):
                    st.session_state.user_profile["name"] = user_info.get("name", "")
                email_key = user_info["email"]
                if email_key not in st.session_state.users_db:
                    st.session_state.users_db[email_key] = "__google_oauth__"
                st.query_params.clear()
                st.rerun()
            else:
                st.error("❌ Google sign-in failed. Check your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
                st.query_params.clear()
        else:
            # Unknown state — clear params and reload cleanly
            st.query_params.clear()
            st.rerun()
    # ─────────────────────────────────────────────────────────────────────────

    st.markdown("""
    <div style="text-align:center; padding: 4rem 0;">
      <div style="font-size:3.5rem; margin-bottom:1rem">🎬</div>
      <div style="font-size:2rem; font-weight:800; color:#a78bfa; margin-bottom:0.5rem">Welcome to CineMatrix</div>
      <div style="font-size:1rem; color:#6b7194; margin-bottom:2rem">Please log in to continue</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        # ── Google Sign-In button ─────────────────────────────────────────────
        google_configured = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
        if google_configured:
            google_url = make_google_auth_url()
            st.markdown(f"""
            <a href="{google_url}" style="text-decoration:none; display:block; margin-bottom:0.75rem">
              <div style="
                display:flex; align-items:center; justify-content:center; gap:12px;
                background:#fff; color:#3c4043;
                border:1px solid #dadce0; border-radius:10px;
                padding:0.65rem 1.4rem; font-family:'Poppins',sans-serif;
                font-size:0.92rem; font-weight:600; cursor:pointer;
                box-shadow:0 1px 4px rgba(0,0,0,0.18);">
                <svg width="20" height="20" viewBox="0 0 48 48">
                  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                  <path fill="none" d="M0 0h48v48H0z"/>
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
            st.info("💡 Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in your `.env` to enable Google Sign-In.", icon="ℹ️")
        # ─────────────────────────────────────────────────────────────────────

        tab_login, tab_signup = st.tabs(["Log In", "Create Account"])

        with tab_login:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Log In", use_container_width=True):
                if email in st.session_state.users_db and st.session_state.users_db[email] == password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

        with tab_signup:
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_pass")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
            if st.button("Create Account", use_container_width=True):
                if not new_email or not new_password:
                    st.warning("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif new_email in st.session_state.users_db:
                    st.error("An account with this email already exists.")
                else:
                    st.session_state.users_db[new_email] = new_password
                    st.success("Account created successfully! You can now log in.")

    st.stop()


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
    <div class="nav-stat">
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

col_space, col_account, col_logout = st.columns([7.2, 1.6, 1.2])
with col_account:
    acc_label = f"👋 Hi, {st.session_state.user_profile['name']}" if st.session_state.user_profile.get("name") else "👤 Account"
    if st.button(acc_label, use_container_width=True):
        st.session_state.show_account = not st.session_state.show_account
        st.rerun()

with col_logout:
    if st.button("Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.connected = False
        st.rerun()

if st.session_state.show_account:
    with st.container(border=True):
        st.markdown("### 👤 Account Details & Preferences")
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Display Name", value=st.session_state.user_profile.get("name", ""))
            all_g = sorted(['Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Family', 'Fantasy', 'History', 'Horror', 'Music', 'Mystery', 'Romance', 'Science Fiction', 'TV Movie', 'Thriller', 'War', 'Western'])
            new_genres = st.multiselect("Favorite Genres", all_g, default=st.session_state.user_profile.get("genres", []))
            if st.button("Save Profile"):
                st.session_state.user_profile["name"] = new_name
                st.session_state.user_profile["genres"] = new_genres
                st.session_state.show_account = False
                st.toast("Profile saved successfully!", icon="✅")
                st.rerun()
        with c2:
            st.markdown("**📜 Recent Search History**")
            if st.session_state.search_history:
                for s in reversed(st.session_state.search_history[-8:]):
                    st.markdown(f"- 🎬 {s}")
            else:
                st.info("No searches yet. Find some movies to build your history!")
    st.markdown("<br>", unsafe_allow_html=True)

tab_home, tab_analytics = st.tabs(["Recommended", "📊  Analytics & Charts"])

with tab_home:

    st.markdown("""
    <div class="hero-panel">
      <div class="hero-label">The New AI-Powered</div>
      <div class="hero-heading">Find Movies You'll <span>Love</span></div>
      <div class="hero-sub">Pick a film of your choice, and we'll find you the match</div>
    </div>
    """, unsafe_allow_html=True)

    col_sel, col_btn = st.columns([5, 1])
    with col_sel:
        selected = st.selectbox("", movies["title"].values,
                                label_visibility="collapsed",
                                placeholder="🔍  Type or pick a movie…")
    with col_btn:
        go = st.button("✦  Recommend", use_container_width=True)

    if go:
        with st.spinner("Analysing patterns & fetching posters…"):
            recs = recommend(selected, n=10)
            
            for r in recs:
                get_poster(r["movie_id"])
                
            st.session_state.recs         = recs
            st.session_state.searched_for = selected
            if selected in st.session_state.search_history:
                st.session_state.search_history.remove(selected)
            st.session_state.search_history.append(selected)

    if st.session_state.recs:
        base = st.session_state.searched_for

        base_details = get_details(
            movies[movies['title']==base]['movie_id'].values[0]
            if base in movies['title'].values else 0,
            fallback=base
        )
        genres_preview = ", ".join(base_details.get("genres",[])[:3]) or "Mixed"
        st.markdown(f"""
        <div class="feature-strip">
          <div class="feature-strip-dot"></div>
          <div class="feature-strip-text">
            CineMatrix Intelligence <b>10 Similar Picks for...
            <b>{base}</b> &nbsp;·&nbsp; Genres: {genres_preview}
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">Because you liked <em style="color:#a78bfa">{base}</em></div>
          <div class="sec-head-count">1–5 of 10</div>
        </div>
        """, unsafe_allow_html=True)

        row1 = st.session_state.recs[:5]
        cols1 = st.columns(5, gap="small")
        for idx, (col, rec) in enumerate(zip(cols1, row1)):
            with col:
                d          = get_details(rec["movie_id"], fallback=rec["title"])
                poster_url = get_poster(rec["movie_id"])           
                genre_tag  = d["genres"][0] if d["genres"] else ""

                if poster_url == NO_POSTER:
                    img_html = f"""<div style="aspect-ratio: 2/3; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #12121a 0%, #1a1a26 100%); width: 100%;">
                      <div style="font-size: 1.5rem; font-weight: 700; color: #f5c518; text-align: center; line-height: 1.2;">Movie<br>🎬</div>
                    </div>"""
                else:
                    img_html = f'<img src="{poster_url}" alt="{d["title"]}" loading="lazy">'

                cast_str = ", ".join(d["cast"][:3]) if d.get("cast") else "Unknown"
                st.markdown(f"""
                <div class="mc">
                  {img_html}
                  {'<div class="mc-genre-tag">' + genre_tag + '</div>' if genre_tag else ''}
                  <div class="mc-title-bar">
                    <div class="mc-title-truncate">{d['title']}</div>
                    <div class="mc-rating">⭐ {d['rating']}</div>
                  </div>
                  <div class="mc-overlay">
                    <div class="mc-title">{d['title']}</div>
                    <div class="mc-rating" style="margin-bottom: 8px;">⭐ {d['rating']} &nbsp;•&nbsp; ⏳ {d['runtime']}m</div>
                    <div class="mc-cast"><b>Cast:</b> {cast_str}</div>
                    <div class="mc-overview">{d['overview']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Details", key=f"r1_{idx}_{rec['movie_id']}", use_container_width=True):
                    d["poster"] = poster_url
                    st.session_state.detail_movie = d
                    st.switch_page("pages/movie_detail.py")

        st.markdown(f"""
        <div class="sec-head" style="margin-top:2rem">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">More You Might Like</div>
          <div class="sec-head-count">6–10 of 10</div>
        </div>
        """, unsafe_allow_html=True)

        row2 = st.session_state.recs[5:]
        cols2 = st.columns(5, gap="small")
        for idx, (col, rec) in enumerate(zip(cols2, row2)):
            with col:
                d          = get_details(rec["movie_id"], fallback=rec["title"])
                poster_url = get_poster(rec["movie_id"])        
                genre_tag  = d["genres"][0] if d["genres"] else ""

                if poster_url == NO_POSTER:
                    img_html = f"""<div style="aspect-ratio: 2/3; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #12121a 0%, #1a1a26 100%); width: 100%;">
                      <div style="font-size: 1.5rem; font-weight: 700; color: #f5c518; text-align: center; line-height: 1.2;">Movie<br>🎬</div>
                    </div>"""
                else:
                    img_html = f'<img src="{poster_url}" alt="{d["title"]}" loading="lazy">'

                cast_str = ", ".join(d["cast"][:3]) if d.get("cast") else "Unknown"
                st.markdown(f"""
                <div class="mc">
                  {img_html}
                  {'<div class="mc-genre-tag">' + genre_tag + '</div>' if genre_tag else ''}
                  <div class="mc-title-bar">
                    <div class="mc-title-truncate">{d['title']}</div>
                    <div class="mc-rating">⭐ {d['rating']}</div>
                  </div>
                  <div class="mc-overlay">
                    <div class="mc-title">{d['title']}</div>
                    <div class="mc-rating" style="margin-bottom: 8px;">⭐ {d['rating']} &nbsp;•&nbsp; ⏳ {d['runtime']}m</div>
                    <div class="mc-cast"><b>Cast:</b> {cast_str}</div>
                    <div class="mc-overview">{d['overview']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Details", key=f"r2_{idx}_{rec['movie_id']}", use_container_width=True):
                    d["poster"] = poster_url
                    st.session_state.detail_movie = d
                    st.switch_page("pages/movie_detail.py")

with tab_analytics:

    st.markdown("""
    <div class="sec-head" style="margin-top:1.5rem">
      <div class="sec-head-bar"></div>
      <div class="sec-head-title">Dataset Analytics — TMDB 5,000 Movies</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load raw CSV once ──
    @st.cache_data
    def load_raw_for_charts_v2():
        df = pd.read_csv(MOVIES_CSV)
        df['year'] = pd.to_datetime(df['release_date'], errors='coerce').dt.year
        for col in ['budget', 'revenue', 'runtime', 'vote_average', 'vote_count']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    df_raw_full = load_raw_for_charts_v2()

    st.markdown("""
    <div class="sec-head" style="margin-top:0;">
      <div class="sec-head-bar"></div>
      <div class="sec-head-title">🎛️ Interactive Dashboard Filters</div>
    </div>
    """, unsafe_allow_html=True)
    
    fc1, fc2 = st.columns(2)
    with fc1:
        rating_range = st.slider("⭐ Select IMDb Rating Range", 
                                 min_value=0.0, max_value=10.0, value=(0.0, 10.0), step=0.5)
    with fc2:
        min_year = int(df_raw_full['year'].min(skipna=True))
        max_year = int(df_raw_full['year'].max(skipna=True))
        year_range = st.slider("📅 Select Release Year Range", 
                               min_value=min_year, max_value=max_year, value=(min_year, max_year))

    # Dynamically filter the entire dashboard data
    df_raw = df_raw_full[
        (df_raw_full['vote_average'] >= rating_range[0]) & 
        (df_raw_full['vote_average'] <= rating_range[1]) &
        (df_raw_full['year'] >= year_range[0]) &
        (df_raw_full['year'] <= year_range[1])
    ]

    k1, k2, k3, k4, k5 = st.columns(5)
    kpi_style = "background:var(--card);border:1px solid var(--border2);border-radius:12px;padding:.9rem 1rem;text-align:center"
    kpi_val   = "font-size:1.6rem;font-weight:800;color:var(--purple);font-family:'Poppins',sans-serif"
    kpi_lbl   = "font-size:0.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-top:2px"

    k1.markdown(f'<div style="{kpi_style}"><div style="{kpi_val}">{len(df_raw):,}</div><div style="{kpi_lbl}">Total Movies</div></div>', unsafe_allow_html=True)
    avg_rating = df_raw["vote_average"].mean() if not df_raw.empty else 0
    k2.markdown(f'<div style="{kpi_style}"><div style="{kpi_val}">{avg_rating:.1f}</div><div style="{kpi_lbl}">Avg Rating</div></div>', unsafe_allow_html=True)
    med_runtime = df_raw["runtime"].median() if not df_raw.empty else 0
    k3.markdown(f'<div style="{kpi_style}"><div style="{kpi_val}">{int(med_runtime)}m</div><div style="{kpi_lbl}">Median Runtime</div></div>', unsafe_allow_html=True)
    lat_year = df_raw["year"].max() if not df_raw.empty else 0
    k4.markdown(f'<div style="{kpi_style}"><div style="{kpi_val}">{int(lat_year)}</div><div style="{kpi_lbl}">Latest Year</div></div>', unsafe_allow_html=True)
    tot_votes = df_raw["vote_count"].sum() // 1_000_000 if not df_raw.empty else 0
    k5.markdown(f'<div style="{kpi_style}"><div style="{kpi_val}">{tot_votes:.0f}M</div><div style="{kpi_lbl}">Total Votes</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    def get_genre_counts_from_df(df):
        gc = {}
        for raw in df['genres'].dropna():
            try:
                for g in ast.literal_eval(raw):
                    gc[g['name']] = gc.get(g['name'], 0) + 1
            except: pass
        return pd.DataFrame(sorted(gc.items(), key=lambda x: x[1], reverse=True),
                            columns=['Genre','Count'])

    genre_df = get_genre_counts_from_df(df_raw)
    top10_df = genre_df.head(10) if not genre_df.empty else pd.DataFrame(columns=['Genre','Count'])

    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">🎭 Top 10 Genres — Movie Count</div>
        </div>
        """, unsafe_allow_html=True)

        import plotly.express as px
        
        if not top10_df.empty:
            fig1 = px.bar(
                top10_df.sort_values('Count', ascending=True), 
                x='Count', y='Genre', orientation='h',
                text='Count',
                color_discrete_sequence=['#7c3aed']
            )
            fig1.update_traces(textposition='outside')
            fig1.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_title="Number of Movies",
                yaxis_title=""
            )
            st.plotly_chart(fig1, use_container_width=True)
            st.caption(f"📊 {top10_df.iloc[0]['Genre']} leads with {top10_df.iloc[0]['Count']:,} films")
        else:
            st.info("No data available for this filter.")

    with col_b:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">⭐ Rating Distribution</div>
        </div>
        """, unsafe_allow_html=True)

        if not df_raw.empty:
            fig2 = px.histogram(
                df_raw.dropna(subset=['vote_average']), x='vote_average', nbins=20,
                color_discrete_sequence=['#7c3aed']
            )
            mean_val = df_raw['vote_average'].mean()
            fig2.add_vline(
                x=mean_val, 
                line_dash="dash", line_color="#f59e0b",
                annotation_text=f"Mean: {mean_val:.1f}"
            )
            fig2.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_title="IMDb Rating",
                yaxis_title="Movie Count"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No data available for this filter.")

    col_c, col_d = st.columns([3, 2])

    with col_c:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">📅 Movies Released per Year (1990–2017)</div>
        </div>
        """, unsafe_allow_html=True)

        year_df = (df_raw[df_raw['year'].between(1990, 2017)]
                   .groupby('year')
                   .agg(count=('title','count'), avg_rating=('vote_average','mean'))
                   .reset_index())

        if not year_df.empty:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            fig3 = make_subplots(specs=[[{"secondary_y": True}]])
            fig3.add_trace(
                go.Scatter(x=year_df['year'], y=year_df['count'], fill='tozeroy', 
                           name='Movies Released', line=dict(color='#7c3aed')),
                secondary_y=False
            )
            fig3.add_trace(
                go.Scatter(x=year_df['year'], y=year_df['avg_rating'], 
                           name='Avg Rating', line=dict(color='#f59e0b', dash='dash')),
                secondary_y=True
            )
            fig3.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=30, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig3.update_yaxes(title_text="# of Movies", secondary_y=False)
            fig3.update_yaxes(title_text="Avg Rating", secondary_y=True)
            
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No data available for this filter.")

    with col_d:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">🍕 Top 8 Genre Share</div>
        </div>
        """, unsafe_allow_html=True)

        pie8 = genre_df.head(8)
        if not pie8.empty:
            fig4 = px.pie(
                pie8, values='Count', names='Genre', hole=0.52,
                color_discrete_sequence=['#7c3aed','#2563eb','#06b6d4','#10b981',
                                         '#f59e0b','#ec4899','#6d28d9','#1d4ed8']
            )
            fig4.update_traces(textposition='inside', textinfo='percent+label')
            fig4.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=30, b=0),
                showlegend=False,
                annotations=[dict(text=f'{pie8["Count"].sum():,}<br>films', x=0.5, y=0.5, font_size=14, showarrow=False, font_color='#a78bfa')]
            )
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No data available for this filter.")

    st.markdown("""
    <div class="sec-head" style="margin-top:1rem">
      <div class="sec-head-bar"></div>
      <div class="sec-head-title">🔢 Top 10 Genres — Interactive Bar (Hover to explore)</div>
    </div>
    """, unsafe_allow_html=True)

    chart_data = top10_df.set_index('Genre')['Count']
    if not chart_data.empty:
        st.bar_chart(chart_data, use_container_width=True, height=320, color="#7c3aed")
    else:
        st.info("No data available for this filter.")

    col_e, col_f = st.columns(2)

    with col_e:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">⏱ Runtime vs IMDb Rating</div>
        </div>
        """, unsafe_allow_html=True)

        scatter_df = df_raw[['runtime','vote_average','title']].dropna()
        scatter_df = scatter_df[(scatter_df['runtime'] > 40) & (scatter_df['runtime'] < 240)]

        if not scatter_df.empty:
            fig5 = px.scatter(
                scatter_df, x='runtime', y='vote_average', color='vote_average',
                hover_name='title', color_continuous_scale='plasma',
                opacity=0.7
            )
            fig5.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_title="Runtime (min)",
                yaxis_title="Rating",
                coloraxis_showscale=True
            )
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("No data available for this filter.")

    with col_f:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">💰 Budget vs Revenue (log scale)</div>
        </div>
        """, unsafe_allow_html=True)

        bvr = df_raw[(df_raw['budget']>1e6)&(df_raw['revenue']>1e6)].copy()

        if not bvr.empty:
            fig6 = px.scatter(
                bvr, x='budget', y='revenue', color='vote_average',
                hover_name='title', color_continuous_scale='plasma',
                log_x=True, log_y=True, opacity=0.7
            )
            mn = min(bvr['budget'].min(), bvr['revenue'].min())
            mx = max(bvr['budget'].max(), bvr['revenue'].max())
            
            fig6.add_shape(
                type="line", x0=mn, y0=mn, x1=mx, y1=mx,
                line=dict(color="#f59e0b", dash="dash", width=1)
            )
            fig6.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_title="Budget ($)",
                yaxis_title="Revenue ($)"
            )
            st.plotly_chart(fig6, use_container_width=True)
        else:
            st.info("No data available for this filter.")

    st.markdown("""
    <div class="sec-head" style="margin-top:1rem">
      <div class="sec-head-bar"></div>
      <div class="sec-head-title">🏆 Top 10 Movies (Based on Filters)</div>
    </div>
    """, unsafe_allow_html=True)

    # Allow smaller vote counts if the user heavily filtered the data
    min_votes_required = 500 if len(df_raw) > 500 else 10
    top10_filtered = (df_raw[df_raw['vote_count'] >= min_votes_required]
             .nlargest(10, 'vote_average')[['title','vote_average','vote_count','year']]
             .reset_index(drop=True))
    top10_filtered.index = top10_filtered.index + 1
    top10_filtered.columns = ['Title','Rating','Votes','Year']
    top10_filtered['Year'] = top10_filtered['Year'].astype('Int64')

    rows_html = ""
    if top10_filtered.empty:
        rows_html = '<tr><td colspan="5" style="padding:1rem;text-align:center;color:#6b7194;">No movies match the current filters.</td></tr>'
    else:
        for i, row in top10_filtered.iterrows():
            bar_w = int(row['Rating'] / 10 * 100)
            rows_html += f"""
            <tr style="border-bottom:1px solid #1e1e38;">
              <td style="padding:.55rem .7rem;color:#a78bfa;font-weight:700">{i}</td>
              <td style="padding:.55rem .7rem;color:#f1f0ff;font-weight:500">{row['Title']}</td>
              <td style="padding:.55rem .7rem">
                <div style="display:flex;align-items:center;gap:8px">
                  <div style="width:80px;background:#1e1e38;border-radius:4px;height:6px;overflow:hidden">
                    <div style="width:{bar_w}%;background:linear-gradient(90deg,#7c3aed,#06b6d4);height:100%;border-radius:4px"></div>
                  </div>
                  <span style="color:#f59e0b;font-weight:700;font-size:.82rem">{row['Rating']}</span>
                </div>
              </td>
              <td style="padding:.55rem .7rem;color:#6b7194;font-size:.82rem">{row['Votes']:,}</td>
              <td style="padding:.55rem .7rem;color:#6b7194;font-size:.82rem">{row['Year']}</td>
            </tr>"""

    st.markdown(f"""
    <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden">
      <table style="width:100%;border-collapse:collapse;font-family:'Poppins',sans-serif;font-size:.85rem">
        <thead>
          <tr style="background:#0f0f1c;border-bottom:2px solid #2a2a50">
            <th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">#</th>
            <th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Title</th>
            <th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Rating</th>
            <th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Votes</th>
            <th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Year</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="site-footer">
  <span>CineMatrix</span> &nbsp;·&nbsp; Powered by TMDB &nbsp;·&nbsp;
  Built with Streamlit &amp; Python &nbsp;·&nbsp; © 2025
</div>
""", unsafe_allow_html=True)

st.stop()


load_dotenv()

st.set_page_config(
    page_title="CineMatrix",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap');

/* ── PALETTE ── */
:root {
  --bg:        #07070f;
  --surface:   #0f0f1c;
  --card:      #14142a;
  --border:    #1e1e38;
  --border2:   #2a2a50;
  --purple:    #7c3aed;
  --purple2:   #6d28d9;
  --blue:      #2563eb;
  --cyan:      #06b6d4;
  --pink:      #ec4899;
  --gold:      #f59e0b;
  --green:     #10b981;
  --text:      #f1f0ff;
  --muted:     #6b7194;
  --radius:    14px;
}

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Poppins', sans-serif !important; }
.stApp              { background: var(--bg) !important; color: var(--text); }
.block-container    { padding: 0 2.5rem 4rem !important; max-width: 1380px; }
#MainMenu, footer, header { visibility: hidden; }
section[data-testid="stSidebar"] { display: none !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 0 1rem;
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--border);
}
.nav-brand {
  display: flex; align-items: center; gap: 10px;
  font-size: 1.5rem; font-weight: 900; letter-spacing: -0.02em;
}
.nav-brand-icon {
  width: 38px; height: 38px;
  background: linear-gradient(135deg, var(--purple) 0%, var(--blue) 100%);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem;
  box-shadow: 0 4px 15px rgba(124,58,237,0.45);
}
.nav-brand-text {
  background: linear-gradient(135deg, #a78bfa 0%, #60a5fa 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.nav-subtitle { font-size: 0.72rem; color: var(--muted); letter-spacing: 0.1em; text-transform: uppercase; }
.nav-stats {
  display: flex; gap: 2rem; align-items: center;
}
.nav-stat { text-align: center; }
.nav-stat-num { font-size: 1.1rem; font-weight: 800; color: var(--purple); line-height: 1; }
.nav-stat-lbl { font-size: 0.65rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }

.hero-panel {
  background: linear-gradient(135deg,
    rgba(124,58,237,0.18) 0%,
    rgba(37,99,235,0.14) 50%,
    rgba(6,182,212,0.10) 100%);
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: 20px;
  padding: 2.4rem 2.8rem;
  margin-bottom: 2.5rem;
  position: relative;
  overflow: hidden;
}
.hero-panel::before {
  content: '';
  position: absolute; top: -60px; right: -60px;
  width: 250px; height: 250px;
  background: radial-gradient(circle, rgba(124,58,237,.12) 0%, transparent 70%);
  border-radius: 50%;
}
.hero-panel::after {
  content: '';
  position: absolute; bottom: -40px; left: 30%;
  width: 180px; height: 180px;
  background: radial-gradient(circle, rgba(6,182,212,.08) 0%, transparent 70%);
  border-radius: 50%;
}
.hero-label {
  font-size: 0.72rem; font-weight: 600; color: var(--cyan);
  text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.55rem;
}
.hero-heading {
  font-size: 1.8rem; font-weight: 800; line-height: 1.2; margin-bottom: 0.4rem;
  color: var(--text);
}
.hero-heading span {
  background: linear-gradient(135deg, #a78bfa 0%, #60a5fa 70%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-sub { font-size: 0.88rem; color: var(--muted); margin-bottom: 0; }

/* Selectbox */
.stSelectbox > div > div {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
  color: var(--text) !important;
  font-size: 1rem !important;
  font-family: 'Poppins', sans-serif !important;
}
.stSelectbox label { color: var(--muted) !important; font-size: 0.75rem !important;
  text-transform: uppercase; letter-spacing: 0.1em; }

/* ALL BUTTONS → gold  (overridden per-button with unique containers below) */
div.stButton > button, div.stFormSubmitButton > button {
  background: linear-gradient(135deg, var(--purple) 0%, var(--blue) 100%) !important;
  color: #fff !important; font-weight: 700 !important; font-size: 0.9rem !important;
  border: none !important; border-radius: 10px !important;
  padding: 0.65rem 1.6rem !important; letter-spacing: 0.04em;
  font-family: 'Poppins', sans-serif !important;
  transition: transform 0.15s, box-shadow 0.15s !important;
  width: 100%;
  box-shadow: 0 4px 15px rgba(124,58,237,0.35) !important;
}
div.stButton > button:hover, div.stFormSubmitButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 25px rgba(124,58,237,0.55) !important;
}

/* Tabs */
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
  font-size: 0.85rem !important; font-weight: 500 !important;
  border-radius: 9px !important; padding: 0.45rem 1.3rem !important;
  border: none !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, var(--purple) 0%, var(--blue) 100%) !important;
  color: #fff !important; font-weight: 700 !important;
  box-shadow: 0 3px 12px rgba(124,58,237,0.45) !important;
}

/* Spinner */
.stSpinner > div { border-top-color: var(--purple) !important; }

/* HR */
hr { border-color: var(--border) !important; }

.sec-head {
  display: flex; align-items: center; gap: 12px;
  margin: 2.2rem 0 1.2rem;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid var(--border);
}
.sec-head-bar {
  width: 4px; height: 1.3rem; border-radius: 2px;
  background: linear-gradient(to bottom, var(--purple), var(--cyan));
}
.sec-head-title {
  font-size: 1.1rem; font-weight: 700; color: var(--text);
}
.sec-head-count {
  margin-left: auto;
  font-size: 0.72rem; color: var(--muted);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 20px; padding: 2px 10px;
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
.mc:hover {
  transform: translateY(-7px) scale(1.025);
  border-color: var(--purple);
  box-shadow: 0 18px 45px rgba(0,0,0,0.65), 0 0 0 1px rgba(124,58,237,0.5);
}
.mc img {
  width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block;
  background: var(--surface);
}
/* Default title bar */
.mc-title-bar {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: linear-gradient(to top, rgba(7,7,15,0.95) 0%, rgba(7,7,15,0.6) 60%, transparent 100%);
  padding: 2rem 0.75rem 0.75rem;
  transition: opacity 0.3s ease;
}
/* Expanded snippet on hover */
.mc-overlay {
  position: absolute; top: 0; bottom: 0; left: 0; right: 0;
  background: rgba(7, 7, 15, 0.92);
  backdrop-filter: blur(4px);
  padding: 1.2rem 1rem;
  display: flex; flex-direction: column; justify-content: center;
  opacity: 0; transition: opacity 0.3s ease;
}
.mc:hover .mc-title-bar { opacity: 0; }
.mc:hover .mc-overlay { opacity: 1; }

.mc-title-truncate {
  font-size: 0.78rem; font-weight: 600; color: #fff;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: 3px; line-height: 1.3;
}
.mc-title {
  font-size: 0.9rem; font-weight: 700; color: #fff;
  margin-bottom: 4px; line-height: 1.2;
}
.mc-rating { font-size: 0.7rem; color: var(--gold); font-weight: 700; }
.mc-cast { font-size: 0.65rem; color: var(--cyan); margin-bottom: 8px; line-height: 1.3; }
.mc-overview {
  font-size: 0.65rem; color: #d1d1e0; line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 5; -webkit-box-orient: vertical;
  overflow: hidden;
}
.mc-genre-tag {
  position: absolute; top: 8px; right: 8px;
  background: rgba(124,58,237,0.8); backdrop-filter: blur(4px);
  border-radius: 6px; padding: 2px 7px;
  font-size: 0.6rem; font-weight: 600; color: #fff; letter-spacing: 0.05em;
}

.feature-strip {
  background: linear-gradient(135deg, var(--card) 0%, rgba(124,58,237,0.08) 100%);
  border: 1px solid var(--border2);
  border-radius: 16px;
  padding: 1.2rem 1.5rem;
  margin-bottom: 1.8rem;
  display: flex; align-items: center; gap: 1rem;
}
.feature-strip-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: linear-gradient(135deg, var(--purple), var(--cyan));
  flex-shrink: 0;
  box-shadow: 0 0 8px rgba(124,58,237,0.7);
  animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
  0%,100%{ box-shadow: 0 0 8px rgba(124,58,237,0.7); }
  50%    { box-shadow: 0 0 18px rgba(124,58,237,1); }
}
.feature-strip-text { font-size: 0.9rem; color: var(--muted); }
.feature-strip-text b { color: var(--text); }

.site-footer {
  text-align: center; color: var(--muted); font-size: 0.72rem;
  padding: 2rem 0 1rem; border-top: 1px solid var(--border);
  margin-top: 3rem; letter-spacing: 0.05em;
}
.site-footer span { color: var(--purple); }

.analytics-link-card {
  background: linear-gradient(135deg, rgba(124,58,237,0.12) 0%, rgba(37,99,235,0.10) 100%);
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: 14px;
  padding: 1.1rem 1.5rem;
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 2rem;
  cursor: pointer;
}
.analytics-link-text { font-size: 0.88rem; color: #a78bfa; font-weight: 600; }
.analytics-link-sub  { font-size: 0.75rem; color: var(--muted); margin-top: 1px; }
</style>
""", unsafe_allow_html=True)

BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR        = os.path.join(BASE_DIR, 'models')
MOVIE_DICT_PATH   = os.path.join(MODELS_DIR, 'movie_dict.pkl')
SIMILARITY_PATH   = os.path.join(MODELS_DIR, 'similarity.pkl')
POSTER_CACHE_PATH = os.path.join(MODELS_DIR, 'poster_cache.pkl')

def _csv(name):
    p = os.path.join(BASE_DIR, 'data', name)
    return p if os.path.exists(p) else os.path.join(BASE_DIR, name)

MOVIES_CSV  = _csv('tmdb_5000_movies.csv')
CREDITS_CSV = _csv('tmdb_5000_credits.csv')

TMDB_KEY        = os.environ.get('TMDB_API_KEY', 'cdf3a58aa720377a583f33c3e879377c')
TMDB_BASE       = 'https://api.themoviedb.org/3'
POSTER_BASE     = 'https://image.tmdb.org/t/p/w500'
NO_POSTER       = 'https://via.placeholder.com/300x450/14142a/7c3aed?text=No+Image'

if not os.path.exists(MOVIE_DICT_PATH) or not os.path.exists(SIMILARITY_PATH):
    st.error("⚠️  Run `python model_builder.py` first.")
    st.stop()

@st.cache_resource
def load_model():
    m   = pd.DataFrame(pickle.load(open(MOVIE_DICT_PATH, 'rb')))
    sim = pickle.load(open(SIMILARITY_PATH, 'rb'))
    return m, sim

movies, similarity = load_model()

_pc: dict = {}
if os.path.exists(POSTER_CACHE_PATH):
    try:  _pc = pickle.load(open(POSTER_CACHE_PATH, 'rb'))
    except: pass

def get_poster(movie_id: int) -> str:
    cached = _pc.get(movie_id)
    # Valid string URL → use it immediately (fast path)
    if isinstance(cached, str) and cached.startswith('http') and 'tmdb' in cached:
        return cached
    # Stale old-format dict → ignore, re-fetch
    try:
        r    = requests.get(f"{POSTER_BASE.replace('/t/p/w500','/3')}/movie/{movie_id}?api_key={TMDB_KEY}", timeout=8).json()
        path = r.get('poster_path')
        url  = (POSTER_BASE + path) if path else NO_POSTER
    except:
        url = NO_POSTER
    _pc[movie_id] = url
    try: pickle.dump(_pc, open(POSTER_CACHE_PATH, 'wb'))
    except: pass
    return url

@st.cache_resource
def build_lookup():
    rm = pd.read_csv(MOVIES_CSV)
    rc = pd.read_csv(CREDITS_CSV)
    mg = rm.merge(rc, left_on='id', right_on='movie_id', how='left')

    def sp(t):
        try:   return ast.literal_eval(str(t))
        except: return []
    def si(v):
        try:   return int(float(v)) if pd.notna(v) else 0
        except: return 0
    def sf(v):
        try:   return round(float(v),1) if pd.notna(v) else 0.0
        except: return 0.0

    lk = {}
    for _, row in mg.iterrows():
        mid = si(row.get('id') or 0)
        if not mid: continue
        lk[mid] = {
            "title"       : str(row.get('title_x') or row.get('title') or '').strip() or "Unknown",
            "rating"      : sf(row.get('vote_average')),
            "release_date": str(row.get('release_date') or '').strip() or "Unknown",
            "overview"    : str(row.get('overview') or '').strip() or "No description.",
            "genres"      : [g['name'] for g in sp(row.get('genres','[]'))],
            "directors"   : [c['name'] for c in sp(row.get('crew','[]')) if c.get('job')=='Director'],
            "cast"        : [c['name'] for c in sp(row.get('cast','[]'))[:5]],
            "runtime"     : si(row.get('runtime')),
            "tagline"     : str(row.get('tagline') or '').strip(),
            "vote_count"  : si(row.get('vote_count')),
        }
    return lk

local_lookup = build_lookup()

def get_details(movie_id, fallback=""):
    d = local_lookup.get(int(movie_id))
    if d: return d
    return {"title": fallback or "Unknown", "rating": 0, "release_date": "Unknown",
            "overview": "No description.", "genres": [], "directors": [], "cast": [],
            "runtime": 0, "tagline": "", "vote_count": 0}

def recommend(movie, n=10):
    idx    = movies[movies['title'] == movie].index[0]
    pos    = movies.index.get_loc(idx)
    scores = list(enumerate(similarity[pos]))
    top    = sorted(scores, key=lambda x: x[1], reverse=True)[1:n+1]
    return [{"title": movies.iloc[i]["title"], "movie_id": int(movies.iloc[i]["movie_id"])}
            for i, _ in top]

for k, v in [("recs",[]),("searched_for",None), ("logged_in", False), ("users_db", {"admin@cinematrix.com": "password"}), ("search_history", []), ("user_profile", {"name": "", "genres": []}), ("show_account", False)]:
    if k not in st.session_state: st.session_state[k] = v

if not st.session_state.logged_in:
    st.markdown("""
    <div style="text-align:center; padding: 4rem 0;">
      <div style="font-size:3.5rem; margin-bottom:1rem">🎬</div>
      <div style="font-size:2rem; font-weight:800; color:#a78bfa; margin-bottom:0.5rem">Welcome to CineMatrix</div>
      <div style="font-size:1rem; color:#6b7194; margin-bottom:2rem">Please log in to continue</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["Log In", "Create Account"])
        
        with tab_login:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Log In", use_container_width=True):
                if email in st.session_state.users_db and st.session_state.users_db[email] == password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
                
        with tab_signup:
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_pass")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
            if st.button("Create Account", use_container_width=True):
                if not new_email or not new_password:
                    st.warning("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif new_email in st.session_state.users_db:
                    st.error("An account with this email already exists.")
                else:
                    st.session_state.users_db[new_email] = new_password
                    st.success("Account created successfully! You can now log in.")
                    
    st.stop()

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
    <div class="nav-stat">
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

col_space, col_account, col_logout = st.columns([7.2, 1.6, 1.2])
with col_account:
    acc_label = f"👋 Hi, {st.session_state.user_profile['name']}" if st.session_state.user_profile.get("name") else "👤 Account"
    if st.button(acc_label, use_container_width=True):
        st.session_state.show_account = not st.session_state.show_account
        st.rerun()

with col_logout:
    if st.button("Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.connected = False
        st.rerun()

if st.session_state.show_account:
    with st.container(border=True):
        st.markdown("### 👤 Account Details & Preferences")
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Display Name", value=st.session_state.user_profile.get("name", ""))
            all_g = sorted(['Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Family', 'Fantasy', 'History', 'Horror', 'Music', 'Mystery', 'Romance', 'Science Fiction', 'TV Movie', 'Thriller', 'War', 'Western'])
            new_genres = st.multiselect("Favorite Genres", all_g, default=st.session_state.user_profile.get("genres", []))
            if st.button("Save Profile"):
                st.session_state.user_profile["name"] = new_name
                st.session_state.user_profile["genres"] = new_genres
                st.session_state.show_account = False
                st.toast("Profile saved successfully!", icon="✅")
                st.rerun()
        with c2:
            st.markdown("**📜 Recent Search History**")
            if st.session_state.search_history:
                for s in reversed(st.session_state.search_history[-8:]):
                    st.markdown(f"- 🎬 {s}")
            else:
                st.info("No searches yet. Find some movies to build your history!")
    st.markdown("<br>", unsafe_allow_html=True)

tab_home, tab_analytics = st.tabs(["Recommended", "📊  Analytics & Charts"])

with tab_home:

    st.markdown("""
    <div class="hero-panel">
      <div class="hero-label">The New AI-Powered</div>
      <div class="hero-heading">Find Movies You'll <span>Love</span></div>
      <div class="hero-sub">Pick a film of your choice, and we'll find you the match</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form(key="search_form"):
        col_sel, col_btn = st.columns([5, 1])
        with col_sel:
            selected = st.selectbox("", movies["title"].values,
                                    label_visibility="collapsed",
                                    placeholder="🔍  Type or pick a movie…")
        with col_btn:
            go = st.form_submit_button("✦  Recommend", use_container_width=True)

    if go:
        with st.spinner("Analysing patterns & fetching posters…"):
            recs = recommend(selected, n=10)
            
            for r in recs:
                get_poster(r["movie_id"])
                
            st.session_state.recs         = recs
            st.session_state.searched_for = selected
            if selected in st.session_state.search_history:
                st.session_state.search_history.remove(selected)
            st.session_state.search_history.append(selected)

    if st.session_state.recs:
        base = st.session_state.searched_for

        base_details = get_details(
            movies[movies['title']==base]['movie_id'].values[0]
            if base in movies['title'].values else 0,
            fallback=base
        )
        genres_preview = ", ".join(base_details.get("genres",[])[:3]) or "Mixed"
        st.markdown(f"""
        <div class="feature-strip">
          <div class="feature-strip-dot"></div>
          <div class="feature-strip-text">
            CineMatrix Intelligence <b>10 Similar Picks for...
            <b>{base}</b> &nbsp;·&nbsp; Genres: {genres_preview}
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">Because you liked <em style="color:#a78bfa">{base}</em></div>
          <div class="sec-head-count">1–5 of 10</div>
        </div>
        """, unsafe_allow_html=True)

        row1 = st.session_state.recs[:5]
        cols1 = st.columns(5, gap="small")
        for idx, (col, rec) in enumerate(zip(cols1, row1)):
            with col:
                d          = get_details(rec["movie_id"], fallback=rec["title"])
                poster_url = get_poster(rec["movie_id"])           
                genre_tag  = d["genres"][0] if d["genres"] else ""

                if poster_url == NO_POSTER:
                    img_html = f"""<div style="aspect-ratio: 2/3; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #12121a 0%, #1a1a26 100%); width: 100%;">
                      <div style="font-size: 1.5rem; font-weight: 700; color: #f5c518; text-align: center; line-height: 1.2;">Movie<br>🎬</div>
                    </div>"""
                else:
                    img_html = f'<img src="{poster_url}" alt="{d["title"]}" loading="lazy">'

                cast_str = ", ".join(d["cast"][:3]) if d.get("cast") else "Unknown"
                st.markdown(f"""
                <div class="mc">
                  {img_html}
                  {'<div class="mc-genre-tag">' + genre_tag + '</div>' if genre_tag else ''}
                  <div class="mc-title-bar">
                    <div class="mc-title-truncate">{d['title']}</div>
                    <div class="mc-rating">⭐ {d['rating']}</div>
                  </div>
                  <div class="mc-overlay">
                    <div class="mc-title">{d['title']}</div>
                    <div class="mc-rating" style="margin-bottom: 8px;">⭐ {d['rating']} &nbsp;•&nbsp; ⏳ {d['runtime']}m</div>
                    <div class="mc-cast"><b>Cast:</b> {cast_str}</div>
                    <div class="mc-overview">{d['overview']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Details", key=f"r1_{idx}_{rec['movie_id']}", use_container_width=True):
                    d["poster"] = poster_url
                    st.session_state.detail_movie = d
                    st.switch_page("pages/movie_detail.py")

        st.markdown(f"""
        <div class="sec-head" style="margin-top:2rem">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">More You Might Like</div>
          <div class="sec-head-count">6–10 of 10</div>
        </div>
        """, unsafe_allow_html=True)

        row2 = st.session_state.recs[5:]
        cols2 = st.columns(5, gap="small")
        for idx, (col, rec) in enumerate(zip(cols2, row2)):
            with col:
                d          = get_details(rec["movie_id"], fallback=rec["title"])
                poster_url = get_poster(rec["movie_id"])        
                genre_tag  = d["genres"][0] if d["genres"] else ""

                if poster_url == NO_POSTER:
                    img_html = f"""<div style="aspect-ratio: 2/3; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #12121a 0%, #1a1a26 100%); width: 100%;">
                      <div style="font-size: 1.5rem; font-weight: 700; color: #f5c518; text-align: center; line-height: 1.2;">Movie<br>🎬</div>
                    </div>"""
                else:
                    img_html = f'<img src="{poster_url}" alt="{d["title"]}" loading="lazy">'

                cast_str = ", ".join(d["cast"][:3]) if d.get("cast") else "Unknown"
                st.markdown(f"""
                <div class="mc">
                  {img_html}
                  {'<div class="mc-genre-tag">' + genre_tag + '</div>' if genre_tag else ''}
                  <div class="mc-title-bar">
                    <div class="mc-title-truncate">{d['title']}</div>
                    <div class="mc-rating">⭐ {d['rating']}</div>
                  </div>
                  <div class="mc-overlay">
                    <div class="mc-title">{d['title']}</div>
                    <div class="mc-rating" style="margin-bottom: 8px;">⭐ {d['rating']} &nbsp;•&nbsp; ⏳ {d['runtime']}m</div>
                    <div class="mc-cast"><b>Cast:</b> {cast_str}</div>
                    <div class="mc-overview">{d['overview']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Details", key=f"r2_{idx}_{rec['movie_id']}", use_container_width=True):
                    d["poster"] = poster_url
                    st.session_state.detail_movie = d
                    st.switch_page("pages/movie_detail.py")

with tab_analytics:

    st.markdown("""
    <div class="sec-head" style="margin-top:1.5rem">
      <div class="sec-head-bar"></div>
      <div class="sec-head-title">Dataset Analytics — TMDB 5,000 Movies</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load raw CSV once ──
    @st.cache_data
    def load_raw_for_charts_v2():
        df = pd.read_csv(MOVIES_CSV)
        df['year'] = pd.to_datetime(df['release_date'], errors='coerce').dt.year
        for col in ['budget', 'revenue', 'runtime', 'vote_average', 'vote_count']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    df_raw = load_raw_for_charts_v2()

    k1, k2, k3, k4, k5 = st.columns(5)
    kpi_style = "background:var(--card);border:1px solid var(--border2);border-radius:12px;padding:.9rem 1rem;text-align:center"
    kpi_val   = "font-size:1.6rem;font-weight:800;color:var(--purple);font-family:'Poppins',sans-serif"
    kpi_lbl   = "font-size:0.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-top:2px"

    k1.markdown(f'<div style="{kpi_style}"><div style="{kpi_val}">{len(df_raw):,}</div><div style="{kpi_lbl}">Total Movies</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div style="{kpi_style}"><div style="{kpi_val}">{df_raw["vote_average"].mean():.1f}</div><div style="{kpi_lbl}">Avg Rating</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div style="{kpi_style}"><div style="{kpi_val}">{int(df_raw["runtime"].median())}m</div><div style="{kpi_lbl}">Median Runtime</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div style="{kpi_style}"><div style="{kpi_val}">{int(df_raw["year"].max())}</div><div style="{kpi_lbl}">Latest Year</div></div>', unsafe_allow_html=True)
    k5.markdown(f'<div style="{kpi_style}"><div style="{kpi_val}">{df_raw["vote_count"].sum()//1_000_000:.0f}M</div><div style="{kpi_lbl}">Total Votes</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    @st.cache_data
    def get_genre_counts(csv_path):
        df = pd.read_csv(csv_path)
        gc = {}
        for raw in df['genres'].dropna():
            try:
                for g in ast.literal_eval(raw):
                    gc[g['name']] = gc.get(g['name'], 0) + 1
            except: pass
        return pd.DataFrame(sorted(gc.items(), key=lambda x: x[1], reverse=True),
                            columns=['Genre','Count'])

    genre_df = get_genre_counts(MOVIES_CSV)
    top10_df = genre_df.head(10)

    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">🎭 Top 10 Genres — Movie Count</div>
        </div>
        """, unsafe_allow_html=True)

        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(8, 4.5))
        fig.patch.set_facecolor('#14142a')
        ax.set_facecolor('#0f0f1c')

        bars = ax.barh(top10_df['Genre'][::-1], top10_df['Count'][::-1],
                       color=['#7c3aed','#6d28d9','#5b21b6','#4c1d95',
                              '#2563eb','#1d4ed8','#1e40af','#06b6d4',
                              '#0891b2','#0e7490'],
                       height=0.65, edgecolor='none')

        for bar in bars:
            w = bar.get_width()
            ax.text(w + 8, bar.get_y() + bar.get_height()/2,
                    f'{int(w):,}', va='center', ha='left',
                    fontsize=9, color='#a78bfa', fontweight='bold')

        ax.set_xlabel('Number of Movies', color='#6b7194', fontsize=9)
        ax.tick_params(colors='#9090b8', labelsize=9)
        ax.spines[:].set_visible(False)
        ax.xaxis.grid(True, color='#1e1e38', linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xlim(0, top10_df['Count'].max() * 1.15)
        fig.tight_layout(pad=1.5)

        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

        st.caption("📊 Drama leads with 2,297 films — hover the chart in the interactive version on the Analytics tab")

    with col_b:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">⭐ Rating Distribution</div>
        </div>
        """, unsafe_allow_html=True)

        fig2, ax2 = plt.subplots(figsize=(5, 4.5))
        fig2.patch.set_facecolor('#14142a')
        ax2.set_facecolor('#0f0f1c')

        n, bins, patches = ax2.hist(df_raw['vote_average'].dropna(), bins=20,
                                     edgecolor='none', color='#7c3aed')
        cmap = plt.cm.get_cmap('plasma')
        for i, patch in enumerate(patches): # type: ignore
            patch.set_facecolor(cmap(i / len(patches))) # type: ignore

        ax2.axvline(df_raw['vote_average'].mean(), color='#f59e0b', linewidth=1.5,
                    linestyle='--', label=f"Mean {df_raw['vote_average'].mean():.1f}")
        ax2.legend(fontsize=8, facecolor='#14142a', edgecolor='#2a2a50', labelcolor='#a78bfa')
        ax2.set_xlabel('IMDb Rating', color='#6b7194', fontsize=9)
        ax2.set_ylabel('Movie Count', color='#6b7194', fontsize=9)
        ax2.tick_params(colors='#9090b8', labelsize=9)
        ax2.spines[:].set_visible(False)
        ax2.yaxis.grid(True, color='#1e1e38', linewidth=0.8)
        ax2.set_axisbelow(True)
        fig2.tight_layout(pad=1.5)

        st.pyplot(fig2, use_container_width=True)
        plt.close(fig2)

    col_c, col_d = st.columns([3, 2])

    with col_c:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">📅 Movies Released per Year (1990–2017)</div>
        </div>
        """, unsafe_allow_html=True)

        year_df = (df_raw[df_raw['year'].between(1990, 2017)]
                   .groupby('year')
                   .agg(count=('title','count'), avg_rating=('vote_average','mean'))
                   .reset_index())

        fig3, ax3 = plt.subplots(figsize=(8, 4))
        ax3b = ax3.twinx()
        fig3.patch.set_facecolor('#14142a')
        ax3.set_facecolor('#0f0f1c')
        ax3b.set_facecolor('#0f0f1c')

        ax3.fill_between(year_df['year'], year_df['count'],
                         alpha=0.35, color='#7c3aed')
        ax3.plot(year_df['year'], year_df['count'],
                 color='#a78bfa', linewidth=2)
        ax3b.plot(year_df['year'], year_df['avg_rating'],
                  color='#f59e0b', linewidth=1.8, linestyle='--', marker='o', markersize=3)

        ax3.set_ylabel('# of Movies', color='#a78bfa', fontsize=8)
        ax3b.set_ylabel('Avg Rating', color='#f59e0b', fontsize=8)
        ax3.tick_params(colors='#9090b8', labelsize=8)
        ax3b.tick_params(colors='#9090b8', labelsize=8)
        ax3.spines[:].set_visible(False)
        ax3b.spines[:].set_visible(False)
        ax3.xaxis.grid(True, color='#1e1e38', linewidth=0.6)
        ax3.yaxis.grid(True, color='#1e1e38', linewidth=0.6)
        ax3.set_axisbelow(True)

        # Legend
        p1 = mpatches.Patch(color='#a78bfa', label='Movies Released')
        p2 = mpatches.Patch(color='#f59e0b', label='Avg Rating')
        ax3.legend(handles=[p1,p2], fontsize=8, facecolor='#14142a',
                   edgecolor='#2a2a50', labelcolor='#e0e0f0', loc='upper left')
        fig3.tight_layout(pad=1.5)
        st.pyplot(fig3, use_container_width=True)
        plt.close(fig3)

    with col_d:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">🍕 Top 8 Genre Share</div>
        </div>
        """, unsafe_allow_html=True)

        fig4, ax4 = plt.subplots(figsize=(5, 4))
        fig4.patch.set_facecolor('#14142a')
        ax4.set_facecolor('#14142a')

        pie8 = genre_df.head(8)
        colors_pie = ['#7c3aed','#2563eb','#06b6d4','#10b981',
                      '#f59e0b','#ec4899','#6d28d9','#1d4ed8']
        pie_results = ax4.pie( 
            pie8['Count'], labels=pie8['Genre'].tolist(), autopct='%1.0f%%',
            colors=colors_pie, startangle=90,
            wedgeprops=dict(edgecolor='#07070f', linewidth=1.5),
            pctdistance=0.78, labeldistance=1.1
        )
        wedges, texts, autotexts = pie_results # type: ignore
        for t in texts:     t.set_color('#9090b8');  t.set_fontsize(8)
        for t in autotexts: t.set_color('#fff');     t.set_fontsize(7.5); t.set_fontweight('bold')

        centre = plt.Circle((0,0), 0.52, fc='#14142a')  # type: ignore
        ax4.add_patch(centre)
        ax4.text(0, 0, f'{pie8["Count"].sum():,}\nfilms',
                 ha='center', va='center', fontsize=9, color='#a78bfa', fontweight='bold')

        fig4.tight_layout()
        st.pyplot(fig4, use_container_width=True)
        plt.close(fig4)

    st.markdown("""
    <div class="sec-head" style="margin-top:1rem">
      <div class="sec-head-bar"></div>
      <div class="sec-head-title">🔢 Top 10 Genres — Interactive Bar (Hover to explore)</div>
    </div>
    """, unsafe_allow_html=True)

    chart_data = top10_df.set_index('Genre')['Count']
    st.bar_chart(chart_data, use_container_width=True, height=320, color="#7c3aed")

    col_e, col_f = st.columns(2)

    with col_e:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">⏱ Runtime vs IMDb Rating</div>
        </div>
        """, unsafe_allow_html=True)

        scatter_df = df_raw[['runtime','vote_average','title']].dropna()
        scatter_df = scatter_df[(scatter_df['runtime'] > 40) & (scatter_df['runtime'] < 240)]

        fig5, ax5 = plt.subplots(figsize=(5.5, 4))
        fig5.patch.set_facecolor('#14142a')
        ax5.set_facecolor('#0f0f1c')
        sc = ax5.scatter(scatter_df['runtime'], scatter_df['vote_average'],
                         c=scatter_df['vote_average'], cmap='plasma',
                         alpha=0.5, s=12, linewidths=0)
        ax5.set_xlabel('Runtime (min)', color='#6b7194', fontsize=9)
        ax5.set_ylabel('Rating', color='#6b7194', fontsize=9)
        ax5.tick_params(colors='#9090b8', labelsize=8)
        ax5.spines[:].set_visible(False)
        ax5.xaxis.grid(True, color='#1e1e38', linewidth=0.6)
        ax5.yaxis.grid(True, color='#1e1e38', linewidth=0.6)
        ax5.set_axisbelow(True)
        cb = fig5.colorbar(sc, ax=ax5, shrink=0.8)
        cb.ax.tick_params(colors='#9090b8', labelsize=7)
        fig5.tight_layout(pad=1.5)
        st.pyplot(fig5, use_container_width=True)
        plt.close(fig5)

    with col_f:
        st.markdown("""
        <div class="sec-head">
          <div class="sec-head-bar"></div>
          <div class="sec-head-title">💰 Budget vs Revenue (log scale)</div>
        </div>
        """, unsafe_allow_html=True)

        bvr = df_raw[(df_raw['budget']>1e6)&(df_raw['revenue']>1e6)].copy()

        fig6, ax6 = plt.subplots(figsize=(5.5, 4))
        fig6.patch.set_facecolor('#14142a')
        ax6.set_facecolor('#0f0f1c')
        sc2 = ax6.scatter(bvr['budget'], bvr['revenue'],
                          c=bvr['vote_average'], cmap='plasma',
                          alpha=0.5, s=12, linewidths=0)
        ax6.set_xscale('log'); ax6.set_yscale('log')
        mn = min(bvr['budget'].min(), bvr['revenue'].min())
        mx = max(bvr['budget'].max(), bvr['revenue'].max())
        ax6.plot([mn,mx],[mn,mx], color='#f59e0b', linewidth=1, linestyle='--', alpha=0.5, label='Break-even')
        ax6.legend(fontsize=7.5, facecolor='#14142a', edgecolor='#2a2a50', labelcolor='#e0e0f0')
        ax6.set_xlabel('Budget ($)', color='#6b7194', fontsize=9)
        ax6.set_ylabel('Revenue ($)', color='#6b7194', fontsize=9)
        ax6.tick_params(colors='#9090b8', labelsize=8)
        ax6.spines[:].set_visible(False)
        ax6.xaxis.grid(True, color='#1e1e38', linewidth=0.6)
        ax6.yaxis.grid(True, color='#1e1e38', linewidth=0.6)
        ax6.set_axisbelow(True)
        cb2 = fig6.colorbar(sc2, ax=ax6, shrink=0.8, label='Rating')
        cb2.ax.tick_params(colors='#9090b8', labelsize=7)
        fig6.tight_layout(pad=1.5)
        st.pyplot(fig6, use_container_width=True)
        plt.close(fig6)

    st.markdown("""
    <div class="sec-head" style="margin-top:1rem">
      <div class="sec-head-bar"></div>
      <div class="sec-head-title">🏆 Top 15 Highest-Rated Movies (min 500 votes)</div>
    </div>
    """, unsafe_allow_html=True)

    top15 = (df_raw[df_raw['vote_count'] >= 500]
             .nlargest(15, 'vote_average')[['title','vote_average','vote_count','year']]
             .reset_index(drop=True))
    top15.index = top15.index + 1
    top15.columns = ['Title','Rating','Votes','Year']
    top15['Year'] = top15['Year'].astype('Int64')

    rows_html = ""
    for i, row in top15.iterrows():
        bar_w = int(row['Rating'] / 10 * 100)
        rows_html += f"""
        <tr style="border-bottom:1px solid #1e1e38;">
          <td style="padding:.55rem .7rem;color:#a78bfa;font-weight:700">{i}</td>
          <td style="padding:.55rem .7rem;color:#f1f0ff;font-weight:500">{row['Title']}</td>
          <td style="padding:.55rem .7rem">
            <div style="display:flex;align-items:center;gap:8px">
              <div style="width:80px;background:#1e1e38;border-radius:4px;height:6px;overflow:hidden">
                <div style="width:{bar_w}%;background:linear-gradient(90deg,#7c3aed,#06b6d4);height:100%;border-radius:4px"></div>
              </div>
              <span style="color:#f59e0b;font-weight:700;font-size:.82rem">{row['Rating']}</span>
            </div>
          </td>
          <td style="padding:.55rem .7rem;color:#6b7194;font-size:.82rem">{row['Votes']:,}</td>
          <td style="padding:.55rem .7rem;color:#6b7194;font-size:.82rem">{row['Year']}</td>
        </tr>"""

    st.markdown(f"""
    <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden">
      <table style="width:100%;border-collapse:collapse;font-family:'Poppins',sans-serif;font-size:.85rem">
        <thead>
          <tr style="background:#0f0f1c;border-bottom:2px solid #2a2a50">
            <th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">#</th>
            <th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Title</th>
            <th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Rating</th>
            <th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Votes</th>
            <th style="padding:.65rem .7rem;color:#6b7194;font-weight:600;text-align:left">Year</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="site-footer">
  <span>CineMatrix</span> &nbsp;·&nbsp; Powered by TMDB &nbsp;·&nbsp;
  Built with Streamlit &amp; Python &nbsp;·&nbsp; © 2025
</div>
""", unsafe_allow_html=True)
