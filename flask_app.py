import os
import sqlite3
import urllib.request
import json
import urllib.parse
import xml.etree.ElementTree as ET
from flask import Flask, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "the_list_secret_key_98765_change_me"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "movie_tracker.db")

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS movies (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL, genre TEXT DEFAULT '', status TEXT NOT NULL, score INTEGER DEFAULT 0, poster_url TEXT DEFAULT '', comments TEXT DEFAULT '', FOREIGN KEY (user_id) REFERENCES users (id))")
        cursor.execute("PRAGMA table_info(movies)")
        cols = [col[1] for col in cursor.fetchall()]
        if "poster_url" not in cols:
            cursor.execute("ALTER TABLE movies ADD COLUMN poster_url TEXT DEFAULT ''")
        if "comments" not in cols:
            cursor.execute("ALTER TABLE movies ADD COLUMN comments TEXT DEFAULT ''")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

init_db()

def fetch_movie_news():
    try:
        url = "https://news.google.com/rss/search?q=movies+cinema+casting+box+office&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = []
        for item in root.findall('.//channel/item')[:9]:
            title = item.find('title').text if item.find('title') is not None else 'Cinema News'
            link = item.find('link').text if item.find('link') is not None else '#'
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
            source = "Entertainment Press"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title, source = parts[0], parts[1]
            if pub_date:
                pub_date = pub_date[:16]
            items.append({"title": title, "link": link, "date": pub_date, "source": source})
        return items
    except Exception:
        return []

def fetch_itunes_movies(term):
    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(term)}&entity=movie&country=US&limit=12"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
        results = []
        for movie in data.get('results', []):
            artwork = movie.get('artworkUrl100', '')
            poster_url = artwork.replace('100x100bb', '600x600bb') if artwork else "https://via.placeholder.com/300x450"
            results.append({
                "title": movie.get('trackName', 'Untitled'),
                "release": movie.get('releaseDate', '2026')[:10],
                "genre": movie.get('primaryGenreName', 'Cinema'),
                "score": 8.5,
                "poster": poster_url,
                "overview": movie.get('longDescription', '')
            })
        return results
    except Exception:
        return []

def fetch_upcoming_movies():
    return fetch_itunes_movies("blockbuster 2026")

def fetch_recommended_movies():
    return fetch_itunes_movies("award winning movie")

LOGO_SVG = """<svg width="26" height="16" viewBox="0 0 120 60" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle;"><circle cx="25" cy="30" r="18" stroke="currentColor" stroke-width="10"/><circle cx="60" cy="30" r="22" stroke="currentColor" stroke-width="11"/><circle cx="95" cy="30" r="18" stroke="currentColor" stroke-width="10"/></svg>"""

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600;700&display=swap');
:root { --bg: #f1f1f1; --card-bg: #ffffff; --border: #e2e2e2; --text-primary: #111111; --text-muted: #777777; --accent: #181818; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', sans-serif; background-color: var(--bg); color: var(--text-primary); min-height: 100vh; padding-bottom: 60px; }
.container { max-width: 950px; margin: 0 auto; padding: 0 20px; }
.app-header { background: var(--bg); padding: 24px 8%; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }
.brand-logo { display: flex; align-items: center; gap: 12px; text-decoration: none; color: var(--text-primary); font-weight: 600; letter-spacing: 3px; font-size: 0.85rem; text-transform: uppercase; }
.app-user-actions { display: flex; align-items: center; gap: 18px; }
.nav-tabs { display: flex; gap: 20px; margin: 24px 0; border-bottom: 1px solid var(--border); padding-bottom: 12px; overflow-x: auto; }
.nav-tab { background: transparent; color: var(--text-muted); border: none; font-size: 0.75rem; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; cursor: pointer; padding-bottom: 8px; position: relative; white-space: nowrap; }
.nav-tab.active { color: var(--text-primary); }
.nav-tab.active::after { content: ''; position: absolute; bottom: -13px; left: 0; right: 0; height: 2px; background-color: var(--text-primary); }
.app-title-bar { display: flex; justify-content: space-between; align-items: center; padding: 10px 0 16px 0; }
.app-title-bar h2 { font-size: 1.8rem; font-weight: 200; letter-spacing: -1px; }
.view-icons { display: flex; gap: 12px; font-size: 1.1rem; cursor: pointer; }
.view-icon { color: #aaaaaa; }
.view-icon.active { color: var(--text-primary); }
.app-select-container { margin-bottom: 20px; }
.app-select { width: 100%; padding: 14px 16px; background: var(--card-bg); color: var(--text-primary); border: 1px solid var(--border); font-size: 0.82rem; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; outline: none; cursor: pointer; }
.app-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
@media (min-width: 600px) { .app-grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; } }
.app-card { position: relative; aspect-ratio: 2 / 3; background: var(--card-bg); border: 1px solid var(--border); overflow: hidden; }
.app-card img { width: 100%; height: 100%; object-fit: cover; display: block; }
.edit-badge { position: absolute; top: 8px; left: 8px; background: rgba(255,255,255,0.92); border: 1px solid var(--border); width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; cursor: pointer; z-index: 5; }
.card-overlay { position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(0deg, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.5) 75%, rgba(0,0,0,0) 100%); padding: 24px 10px 10px 10px; color: #fff; display: flex; flex-direction: column; gap: 3px; }
.card-title { font-size: 0.82rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-meta { display: flex; justify-content: space-between; align-items: center; font-size: 0.72rem; color: #ddd; }
.score-star { color: #f59e0b; font-weight: 700; }
.news-grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
@media (min-width: 650px) { .news-grid { grid-template-columns: repeat(3, 1fr); gap: 20px; } }
.news-card { background: var(--card-bg); border: 1px solid var(--border); padding: 20px; display: flex; flex-direction: column; justify-content: space-between; }
.news-source { font-size: 0.68rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
.news-title { font-size: 0.95rem; font-weight: 500; line-height: 1.35; margin-bottom: 16px; }
.news-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border); padding-top: 12px; font-size: 0.72rem; }
.news-link { color: var(--text-primary); text-decoration: none; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
.app-list-table { width: 100%; border-collapse: collapse; background: var(--card-bg); border: 1px solid var(--border); }
.app-list-table th { background: #fdfdfd; text-align: left; padding: 14px; font-size: 0.72rem; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-muted); border-bottom: 1px solid var(--border); }
.app-list-table td { padding: 14px; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
.btn-app { background: var(--accent); color: #fff; border: none; padding: 10px 18px; font-weight: 700; font-size: 0.75rem; letter-spacing: 1.5px; text-transform: uppercase; cursor: pointer; text-decoration: none; display: inline-block; }
.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); z-index: 1000; align-items: center; justify-content: center; padding: 16px; }
.modal-card { background: var(--card-bg); border: 1px solid var(--border); padding: 28px; width: 100%; max-width: 460px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
input, select, textarea { width: 100%; padding: 12px; margin-top: 6px; margin-bottom: 14px; border: 1px solid var(--border); background: #fdfdfd; color: var(--text-primary); font-family: inherit; font-size: 0.88rem; outline: none; }
</style>
"""

LANDING_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>The List</title>{BASE_CSS}</head>
<body style="display:flex;flex-direction:column;justify-content:space-between;">
<header style="display:flex;justify-content:space-between;align-items:center;padding:28px 8%;">
<a href="/" class="brand-logo">{LOGO_SVG} <span>THE LIST</span></a>
<a href="/login" style="text-decoration:none;color:#111;font-size:0.78rem;font-weight:600;letter-spacing:2px;text-transform:uppercase;">LOG IN</a>
</header>
<main style="padding:10px 8%;max-width:1100px;margin:0 auto;width:100%;">
<h1 style="font-size:clamp(3.2rem,7.5vw,5.8rem);font-weight:200;line-height:1.05;letter-spacing:-2px;margin-bottom:28px;">Track the action.<br>Track the list.</h1>
<a href="/register" style="background:#181818;color:#fff;text-decoration:none;padding:18px 36px;font-size:0.78rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;display:inline-block;">GET STARTED</a>
</main>
</body>
</html>
"""

AUTH_TEMPLATE = f"""
<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{{ title }}</title>{BASE_CSS}</head>
<body style="display:flex;align-items:center;justify-content:center;min-height:100vh;">
<div class="modal-card" style="max-width:380px;">
<div style="text-align:center;margin-bottom:24px;"><a href="/" class="brand-logo" style="justify-content:center;font-size:1.1rem;">{LOGO_SVG} <span>THE LIST</span></a></div>
{{% if error %}}<div style="color:#dc2626;font-size:0.82rem;text-align:center;margin-bottom:12px;">{{{{ error }}}}</div>{{% endif %}}
<form method="POST">
<input type="text" name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<button type="submit" class="btn-app" style="width:100%;padding:14px;margin-top:6px;">{{{{ title }}}}</button>
</form>
</div>
</body>
</html>
"""
MAIN_TEMPLATE = f"""
<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>The List</title>{BASE_CSS}</head>
<body>
<div class="app-header">
<a href="/" class="brand-logo">{LOGO_SVG} <span>THE LIST</span></a>
<div class="app-user-actions">
<button onclick="openModal()" class="btn-app">+ Add Title</button>
<span style="font-weight:600;font-size:0.8rem;letter-spacing:1px;text-transform:uppercase;color:var(--text-muted);">{{{{ username }}}}</span>
<a href="/logout" style="color:var(--text-primary);font-size:0.75rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;text-decoration:none;">Exit</a>
</div>
</div>

<div class="container">
<div class="nav-tabs">
<button id="tab-library" onclick="switchNavTab('library')" class="nav-tab active">My List</button>
<button id="tab-search" onclick="switchNavTab('search')" class="nav-tab">Search & Track</button>
<button id="tab-news" onclick="switchNavTab('news')" class="nav-tab">Cinema News</button>
<button id="tab-upcoming" onclick="switchNavTab('upcoming')" class="nav-tab">Upcoming</button>
<button id="tab-recommended" onclick="switchNavTab('recommended')" class="nav-tab">Top Rated</button>
</div>

<!-- My List Section -->
<div id="section-library">
<div class="app-title-bar">
<h2>My List</h2>
<div class="view-icons">
<span id="btn-grid-view" onclick="setView('grid')" class="view-icon active">⊞</span>
<span id="btn-list-view" onclick="setView('list')" class="view-icon">≡</span>
</div>
</div>
<div class="app-select-container">
<select onchange="location = this.value;" class="app-select">
<option value="/?filter=All" {{% if current_filter == 'All' %}}selected{{% endif %}}>All Movies</option>
<option value="/?filter=Watching" {{% if current_filter == 'Watching' %}}selected{{% endif %}}>Watching</option>
<option value="/?filter=Completed" {{% if current_filter == 'Completed' %}}selected{{% endif %}}>Completed</option>
<option value="/?filter=On Hold" {{% if current_filter == 'On Hold' %}}selected{{% endif %}}>On Hold</option>
<option value="/?filter=Dropped" {{% if current_filter == 'Dropped' %}}selected{{% endif %}}>Dropped</option>
<option value="/?filter=Plan to Watch" {{% if current_filter == 'Plan to Watch' %}}selected{{% endif %}}>Plan to Watch</option>
</select>
</div>
<div id="view-grid" class="app-grid">
{{% for m in movies %}}
<div class="app-card">
<div class="edit-badge" onclick='editMovie({{{{ m.id }}}}, {{{{ m.title|tojson }}}}, {{{{ m.genre|tojson }}}}, {{{{ m.status|tojson }}}}, {{{{ m.score }}}}, {{{{ m.poster_url|tojson }}}}, {{{{ m.comments|tojson }}}})'>✏️</div>
{{% if m.poster_url %}}
<img src="{{{{ m.poster_url }}}}" alt="{{{{ m.title }}}}" referrerpolicy="no-referrer">
{{% else %}}
<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:2rem;color:#888;">🎬</div>
{{% endif %}}
<div class="card-overlay">
<div class="card-title">{{{{ m.title }}}}</div>
<div class="card-meta"><span>{{{{ m.status }}}}</span><span class="score-star">⭐ {{{{ m.score }}}}</span></div>
</div>
</div>
{{% endfor %}}
</div>
<div id="view-list" style="display:none;">
<table class="app-list-table">
<thead><tr><th>Title</th><th>Status</th><th>Score</th><th>Notes</th><th>Action</th></tr></thead>
<tbody>
{{% for m in movies %}}
<tr>
<td style="font-weight:600;">{{{{ m.title }}}}</td>
<td>{{{{ m.status }}}}</td>
<td><span class="score-star">⭐ {{{{ m.score }}}}</span></td>
<td>{{{{ m.comments or "—" }}}}</td>
<td><a href="/delete/{{{{ m.id }}}}" style="color:#dc2626;text-decoration:none;font-weight:600;font-size:0.75rem;">Remove</a></td>
</tr>
{{% endfor %}}
</tbody>
</table>
</div>
</div>

<!-- Search Section -->
<div id="section-search" style="display:none;">
<div class="app-title-bar"><h2>Search & Track</h2></div>
<div style="display:flex;gap:10px;margin-bottom:24px;">
<input type="text" id="liveSearchInput" placeholder="Search movies..." style="margin:0;padding:14px;">
<button type="button" onclick="performLiveSearch()" class="btn-app" style="padding:0 24px;">Search</button>
</div>
<div id="liveSearchResults" class="app-grid"></div>
</div>

<!-- News Section -->
<div id="section-news" style="display:none;">
<div class="app-title-bar"><h2>Cinema News</h2></div>
<div class="news-grid">
{{% for article in news_items %}}
<div class="news-card">
<div>
<div class="news-source">{{{{ article.source }}}}</div>
<h3 class="news-title">{{{{ article.title }}}}</h3>
</div>
<div class="news-footer"><span style="color:var(--text-muted);">{{{{ article.date }}}}</span><a href="{{{{ article.link }}}}" target="_blank" class="news-link">Read ↗</a></div>
</div>
{{% endfor %}}
</div>
</div>

<!-- Upcoming Section -->
<div id="section-upcoming" style="display:none;">
<div class="app-title-bar"><h2>Upcoming Releases</h2></div>
<div class="app-grid">
{{% for up in upcoming %}}
<div class="app-card">
<img src="{{{{ up.poster }}}}" referrerpolicy="no-referrer">
<div class="card-overlay">
<div class="card-title">{{{{ up.title }}}}</div>
<button onclick='quickAdd({{{{ up.title|tojson }}}}, "Upcoming", {{{{ up.poster|tojson }}}})' class="btn-app" style="margin-top:6px;padding:6px;font-size:0.68rem;">+ Add</button>
</div>
</div>
{{% endfor %}}
</div>
</div>

<!-- Top Rated Section -->
<div id="section-recommended" style="display:none;">
<div class="app-title-bar"><h2>Top Rated</h2></div>
<div class="app-grid">
{{% for rec in recommendations %}}
<div class="app-card">
<img src="{{{{ rec.poster }}}}" referrerpolicy="no-referrer">
<div class="card-overlay">
<div class="card-title">{{{{ rec.title }}}}</div>
<button onclick='quickAdd({{{{ rec.title|tojson }}}}, {{{{ rec.genre|tojson }}}}, {{{{ rec.poster|tojson }}}})' class="btn-app" style="margin-top:6px;padding:6px;font-size:0.68rem;">+ Add</button>
</div>
</div>
{{% endfor %}}
</div>
</div>
</div>

<!-- Modal -->
<div id="movieModal" class="modal-overlay">
<div class="modal-card">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
<h3 id="modalHeaderTitle" style="font-weight:300;font-size:1.4rem;">Add Movie</h3>
<button onclick="closeModal()" style="background:none;border:none;cursor:pointer;font-size:1.2rem;">✕</button>
</div>
<form action="/add" method="POST">
<input type="hidden" name="movie_id" id="movieId">
<input type="text" name="title" id="movieTitle" placeholder="Title" required>
<input type="text" name="genre" id="movieGenre" placeholder="Genre">
<input type="url" name="poster_url" id="moviePoster" placeholder="Poster URL">
<select name="status" id="movieStatus">
<option value="Watching">Watching</option>
<option value="Completed">Completed</option>
<option value="On Hold">On Hold</option>
<option value="Plan to Watch" selected>Plan to Watch</option>
<option value="Dropped">Dropped</option>
</select>
<select name="score" id="movieScore">
<option value="0">Unrated</option>
<option value="10">10 / 10</option>
<option value="9">9 / 10</option>
<option value="8">8 / 10</option>
<option value="7">7 / 10</option>
<option value="6">6 / 10</option>
<option value="5">5 / 10</option>
</select>
<textarea name="comments" id="movieComments" rows="3" placeholder="Notes..."></textarea>
<button type="submit" class="btn-app" style="width:100%;margin-top:6px;padding:14px;">Save</button>
</form>
</div>
</div>
MAIN_TEMPLATE = """
<script>
function switchNavTab(tab) {
['library', 'search', 'news', 'upcoming', 'recommended'].forEach(t => {
  const el = document.getElementById('section-' + t);
  const tabEl = document.getElementById('tab-' + t);
  if(el) el.style.display = (t === tab) ? 'block' : 'none';
  if(tabEl) tabEl.classList.toggle('active', t === tab);
});
}

function setView(view) {
document.getElementById('view-grid').style.display = (view === 'grid') ? 'grid' : 'none';
document.getElementById('view-list').style.display = (view === 'grid') ? 'none' : 'block';
document.getElementById('btn-grid-view').classList.toggle('active', view === 'grid');
document.getElementById('btn-list-view').classList.toggle('active', view === 'list');
}

function openModal() {
document.getElementById('modalHeaderTitle').innerText = "Add Movie";
['movieId', 'movieTitle', 'movieGenre', 'moviePoster', 'movieComments'].forEach(id => document.getElementById(id).value = '');
document.getElementById('movieModal').style.display = 'flex';
}

function closeModal() { document.getElementById('movieModal').style.display = 'none'; }

function editMovie(id, title, genre, status, score, poster, comments) {
document.getElementById('modalHeaderTitle').innerText = "Edit Movie";
document.getElementById('movieId').value = id;
document.getElementById('movieTitle').value = title;
document.getElementById('movieGenre').value = genre || '';
document.getElementById('movieStatus').value = status;
document.getElementById('movieScore').value = score;
document.getElementById('moviePoster').value = poster || '';
document.getElementById('movieComments').value = comments || '';
document.getElementById('movieModal').style.display = 'flex';
}

function quickAdd(title, genre, poster) {
openModal();
document.getElementById('movieTitle').value = title;
document.getElementById('movieGenre').value = genre;
document.getElementById('moviePoster').value = poster;
}

async function performLiveSearch() {
const query = document.getElementById('liveSearchInput').value.trim();
const resultsContainer = document.getElementById('liveSearchResults');
if (!query) return;
resultsContainer.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;">Searching...</div>';
try {
const res = await fetch('https://itunes.apple.com/search?term=' + encodeURIComponent(query) + '&entity=movie&country=US&limit=12');
const data = await res.json();
resultsContainer.innerHTML = '';
(data.results || []).forEach(item => {
const posterUrl = item.artworkUrl100 ? item.artworkUrl100.replace('100x100bb', '600x600bb') : '';
const title = item.trackName || 'Untitled';
const genre = item.primaryGenreName || 'Cinema';
const card = document.createElement('div');
card.className = 'app-card';
card.innerHTML = `<img src="${posterUrl}" referrerpolicy="no-referrer"><div class="card-overlay"><div class="card-title">${title}</div><button onclick='quickAdd(${JSON.stringify(title)}, ${JSON.stringify(genre)}, ${JSON.stringify(posterUrl)})' class="btn-app" style="margin-top:6px;padding:6px;font-size:0.68rem;">+ Track</button></div>`;
resultsContainer.appendChild(card);
});
} catch(e) { resultsContainer.innerHTML = 'Error loading results.'; }
}
</script>
</body>
</html>
"""
@app.route("/")
def index():
    if "user_id" not in session: return render_template_string(LANDING_TEMPLATE)
    filter_status = request.args.get("filter", "All")
    conn = get_db_connection()
    cursor = conn.cursor()
    if filter_status == "All":
        cursor.execute("SELECT * FROM movies WHERE user_id = ?", (session["user_id"],))
    else:
        cursor.execute("SELECT * FROM movies WHERE user_id = ? AND status = ?", (session["user_id"], filter_status))
    movies = cursor.fetchall()
    conn.close()
    
    page_html = MAIN_TEMPLATE.replace("{BASE_CSS}", BASE_CSS).replace("{LOGO_SVG}", LOGO_SVG)
    return render_template_string(page_html, movies=movies, username=session["username"], current_filter=filter_status, recommendations=fetch_recommended_movies(), upcoming=fetch_upcoming_movies(), news_items=fetch_movie_news())

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username, password = request.form.get("username", "").strip(), request.form.get("password", "").strip()
        if username and password:
            try:
                conn = get_db_connection()
                conn.cursor().execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, generate_password_hash(password)))
                conn.commit(); conn.close()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Username already exists."
    return render_template_string(AUTH_TEMPLATE, title="Register", error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username, password = request.form.get("username", "").strip(), request.form.get("password", "").strip()
        conn = get_db_connection()
        user = conn.cursor().execute("SELECT id, password FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"], session["username"] = user["id"], username
            return redirect(url_for("index"))
        error = "Invalid credentials."
    return render_template_string(AUTH_TEMPLATE, title="Login", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/add", methods=["POST"])
def add():
    if "user_id" not in session: return redirect(url_for("login"))
    movie_id, title = request.form.get("movie_id"), request.form.get("title")
    genre, status = request.form.get("genre", ""), request.form.get("status")
    score = int(request.form.get("score", 0))
    poster_url, comments = request.form.get("poster_url", "").strip(), request.form.get("comments", "").strip()
    if title:
        conn = get_db_connection()
        cursor = conn.cursor()
        if movie_id:
            cursor.execute("UPDATE movies SET title = ?, genre = ?, status = ?, score = ?, poster_url = ?, comments = ? WHERE id = ? AND user_id = ?", (title, genre, status, score, poster_url, comments, movie_id, session["user_id"]))
        else:
            cursor.execute("INSERT INTO movies (user_id, title, genre, status, score, poster_url, comments) VALUES (?, ?, ?, ?, ?, ?, ?)", (session["user_id"], title, genre, status, score, poster_url, comments))
        conn.commit(); conn.close()
    return redirect(url_for("index"))

@app.route("/delete/<int:movie_id>")
def delete(movie_id):
    if "user_id" not in session: return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM movies WHERE id = ? AND user_id = ?", (movie_id, session["user_id"]))
    conn.commit(); conn.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run()
