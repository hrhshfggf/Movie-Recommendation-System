import streamlit as st

st.set_page_config(page_title="Movie Details", layout="wide")

st.markdown("""
<style>
    .stApp { background: #0a0a0f !important; color: #e8e8f0; }
    .label { color: #f5c518; font-weight: bold; text-transform: uppercase; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

if "detail_movie" not in st.session_state or not st.session_state.detail_movie:
    
    if st.button("Go Home"):
        st.switch_page("app.py")
    st.stop()

m = st.session_state.detail_movie   

poster       = m.get("poster")
title        = m.get("title")        or "Unknown Title"
tagline      = m.get("tagline")      or ""
rating       = m.get("rating")       or "N/A"
runtime      = m.get("runtime")      or 0
release_date = m.get("release_date") or "N/A"
overview     = m.get("overview")     or "No description available."
genres       = m.get("genres")       or []
directors    = m.get("directors")    or []
cast         = m.get("cast")         or []
vote_count   = m.get("vote_count")   or 0

year         = release_date[:4] if release_date not in ("N/A", None, "") else "N/A"
runtime_str  = f"{runtime} min" if runtime else "N/A"
genres_str   = ", ".join(genres)    if genres    else "N/A"
director_str = ", ".join(directors) if directors else "N/A"
cast_str     = ", ".join(cast)      if cast      else "N/A"

if st.button("⬅ Back to Home"):
    st.switch_page("app.py")
    
st.divider()

col1, col2 = st.columns([1, 2], gap="large")

with col1:
    if not poster or "via.placeholder.com" in poster:
        st.markdown("""
        <div style="aspect-ratio: 2/3; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #12121a 0%, #1a1a26 100%); border-radius: 14px; border: 1px solid #2a2a3d;">
            <div style="font-size: 2.5rem; font-weight: 700; color: #f5c518; text-align: center; line-height: 1.2;">
                Movie<br>🎬
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.image(poster, use_container_width=True)

with col2:
    st.title(title)

    if tagline:
        st.markdown(f"*{tagline}*")

    st.write("---")

    c1, c2, c3 = st.columns(3)
    c1.metric("Rating",  f"⭐ {rating}")
    c2.metric("Runtime", runtime_str)
    c3.metric("Year",    year)

    st.write("### Overview")
    st.write(overview)

    st.write("### Genres")
    st.write(genres_str)

    st.write("### Director")
    st.write(director_str)

    st.write("### Top Cast")
    st.write(cast_str)