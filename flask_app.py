import os
import sqlite3
import urllib.request
import json
import urllib.parse
import xml.etree.ElementTree as ET
from flask import Flask, redirect, render_template_string, request, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "the_list_secret_key_987654321"

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
        cursor.execute("CREATE TABLE IF NOT EXISTS movies (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, title TEXT NOT NULL, genre TEXT, status TEXT, score INTEGER, poster_url TEXT, comments TEXT, FOREIGN KEY(user_id) REFERENCES users(id))")
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB Init Error:", e)

init_db()

def fetch_recommended_movies():
    try:
        url = "https://rss.applehot.com/api/v2/us/movies/top-movies/10/explicit.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            results = []
            for item in data.get('feed', {}).get('results', []):
                results.append({
                    'title': item.get('name'),
                    'poster': item.get('artworkUrl100', '').replace('100x100bb', '600x600bb'),
                    'genre': 'Top Rated'
                })
            return results
    except Exception:
        return [
            {'title': 'Inception', 'poster': 'https://is1-ssl.mzstatic.com/image/thumb/Video115/v4/71/84/6b/71846b76-a496-512c-98a9-46738927909b/pr_source.lsr/600x600bb.jpg', 'genre': 'Sci-Fi'},
            {'title': 'The Dark Knight', 'poster': 'https://is1-ssl.mzstatic.com/image/thumb/Video125/v4/7c/41/49/7c414966-238d-8a5b-6f8d-635b7190135d/pr_source.lsr/600x600bb.jpg', 'genre': 'Action'}
        ]

def fetch_upcoming_movies():
    try:
        url = "https://rss.applehot.com/api/v2/us/movies/coming-soon/10/explicit.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            results = []
            for item in data.get('feed', {}).get('results', []):
                results.append({
                    'title': item.get('name'),
                    'poster': item.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
                })
            return results
    except Exception:
        return []

def fetch_movie_news():
    try:
        url = "https://news.google.com/rss/search?q=movie+releases+hollywood&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            root = ET.fromstring(response.read())
            news = []
            for item in root.findall('./channel/item')[:6]:
                title = item.find('text') if item.find('text') is not None else item.find('title')
                link = item.find('link')
                pubDate = item.find('pubDate')
                source = item.find('source')
                news.append({
                    'title': title.text if title is not None else 'News Update',
                    'link': link.text if link is not None else '#',
                    'date': pubDate.text[:16] if pubDate is not None and pubDate.text else '',
                    'source': source.text if source is not None else 'Cinema Web'
                })
            return news
    except Exception:
        return [{'title': 'Hollywood Box Office Reaches New Milestones', 'link': '#', 'date': 'Today', 'source': 'Box Office Mojo'}]

LOGO_SVG = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect><line x1="7" y1="2" x2="7" y2="22"></line><line x1="17" y1="2" x2="17" y2="22"></line><line x1="2" y1="12" x2="22" y2="12"></line><line x1="2" y1="7" x2="7" y2="7"></line><line x1="2" y1="17" x2="7" y2="17"></line><line x1="17" y1="17" x2="22" y2="17"></line><line x1="17" y1="7" x2="22" y2="7"></line></svg>'

BASE_CSS = """
<style>
:root { --bg-primary: #09090b; --bg-secondary: #121215; --bg-card: #18181b; --text-primary: #f4f4f5; --text-muted: #a1a1aa; --accent: #ffffff; --border: #27272a; }
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
body { background-color: var(--bg-primary); color: var(--text-primary); min-height: 100vh; display: flex; flex-direction: column; }
.app-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 32px; border-bottom: 1px solid var(--border); background: var(--bg-secondary); }
.brand-logo { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1.1rem; letter-spacing: 2px; text-decoration: none; color: var(--text-primary); }
.app-user-actions { display: flex; align-items: center; gap: 16px; }
.container { max-width: 1200px; margin: 0 auto; padding: 32px 20px; width: 100%; flex: 1; }
.nav-tabs { display: flex; gap: 8px; border-bottom: 1px solid var(--border); margin-bottom: 32px; overflow-x: auto; padding-bottom: 8px; }
.nav-tab { background: none; border: none; color: var(--text-muted); padding: 8px 16px; font-weight: 600; font-size: 0.85rem; cursor: pointer; border-radius: 6px; white-space: nowrap; transition: 0.2s; }
.nav-tab.active { background: var(--bg-card); color: var(--text-primary); }
.app-title-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.app-title-bar h2 { font-weight: 400; font-size: 1.6rem; letter-spacing: -0.5px; }
.view-icons { display: flex; gap: 8px; background: var(--bg-card); padding: 4px; border-radius: 8px; border: 1px solid var(--border); }
.view-icon { cursor: pointer; padding: 4px 10px; font-size: 0.9rem; color: var(--text-muted); border-radius: 6px; }
.view-icon.active { background: var(--bg-secondary); color: var(--text-primary); }
.app-select-container { margin-bottom: 24px; }
.app-select { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border); padding: 10px 16px; border-radius: 8px; font-size: 0.85rem; outline: none; }
.app-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }
.app-card { background: var(--bg-card); border-radius: 10px; overflow: hidden; border: 1px solid var(--border); position: relative; display: flex; flex-direction: column; height: 280px; }
.app-card img { width: 100%; height: 100%; object-fit: cover; }
.card-overlay { position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(to top, rgba(9,9,11,0.95), transparent); padding: 16px 12px 12px 12px; display: flex; flex-direction: column; justify-content: flex-end; height: 50%; }
.card-title { font-weight: 600; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px; }
.card-meta { display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--text-muted); }
.score-star { color: #eab308; }
.edit-badge { position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.7); border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; cursor: pointer; z-index: 2; border: 1px solid var(--border); }
.btn-app { background: var(--text-primary); color: var(--bg-primary); border: none; padding: 10px 20px; border-radius: 8px; font-weight: 600; font-size: 0.8rem; cursor: pointer; text-decoration: none; display: inline-block; transition: opacity 0.2s; }
.btn-app:hover { opacity: 0.9; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.8); display: none; align-items: center; justify-content: center; z-index: 100; padding: 20px; }
.modal-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; width: 100%; max-width: 440px; padding: 24px; }
.modal-card input, .modal-card select, .modal-card textarea { width: 100%; background: var(--bg-card); border: 1px solid var(--border); color: var(--text-primary); padding: 12px; border-radius: 8px; font-size: 0.85rem; margin-bottom: 12px; outline: none; }
.auth-wrapper { max-width: 380px; margin: auto; padding: 40px 20px; display: flex; flex-direction: column; justify-content: center; flex: 1; }
.news-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
.news-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; height: 180px; }
.news-source { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 6px; }
.news-title { font-size: 0.9rem; font-weight: 600; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.news-footer { display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; border-top: 1px solid var(--border); padding-top: 12px; }
.news-link { color: var(--text-primary); text-decoration: none; font-weight: 600; }
.app-list-table { width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: 10px; overflow: hidden; border: 1px solid var(--border); }
.app-list-table th, .app-list-table td { padding: 14px 16px; text-align: left; font-size: 0.85rem; border-bottom: 1px solid var(--border); }
.app-list-table th { background: var(--bg-secondary); font-weight: 600; color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }
</style>
"""

AUTH_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{{ title }} — The List</title>{BASE_CSS}</head>
<body>
<div class="auth-wrapper">
<div style="text-align:center;margin-bottom:32px;">
<div style="display:inline-flex;padding:12px;background:var(--bg-card);border-radius:12px;border:1px solid var(--border);margin-bottom:16px;">{LOGO_SVG}</div>
<h1 style="font-weight:400;font-size:1.5rem;letter-spacing:-0.5px;">{{ title }} to The List</h1>
</div>
{% if error %}<div style="background:#dc262620;color:#ef4444;border:1px solid #dc262640;padding:12px;border-radius:8px;font-size:0.8rem;margin-bottom:16px;text-align:center;">{{ error }}</div>{% endif %}
<form method="POST">
<input type="text" name="username" placeholder="Username" required style="width:100%;background:var(--bg-card);border:1px solid var(--border);color:var(--text-primary);padding:14px;border-radius:8px;font-size:0.9rem;margin-bottom:12px;outline:none;">
<input type="password" name="password" placeholder="Password" required style="width:100%;background:var(--bg-card);border:1px solid var(--border);color:var(--text-primary);padding:14px;border-radius:8px;font-size:0.9rem;margin-bottom:16px;outline:none;">
<button type="submit" class="btn-app" style="width:100%;padding:14px;font-size:0.9rem;">Continue</button>
</form>
<div style="text-align:center;margin-top:24px;font-size:0.8rem;color:var(--text-muted);">
{% if title == 'Login' %}Don't have an account? <a href="/register" style="color:var(--text-primary);font-weight:600;text-decoration:none;">Register</a>{% else %}Already have an account? <a href="/login" style="color:var(--text-primary);font-weight:600;text-decoration:none;">Login</a>{% endif %}
</div>
</div>
</body>
</html>
"""

LANDING_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>The List — Cinema Tracker</title>{BASE_CSS}</head>
<body>
<div class="app-header">
<div class="brand-logo">{LOGO_SVG} <span>THE LIST</span></div>
<div class="app-user-actions">
<a href="/login" style="color:var(--text-primary);font-size:0.8rem;font-weight:600;letter-spacing:1px;text-transform:uppercase;text-decoration:none;margin-right:8px;">Login</a>
<a href="/register" class="btn-app">Get Started</a>
</div>
</div>
<div class="container" style="display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:80px 20px;">
<h1 style="font-size:3rem;font-weight:400;letter-spacing:-1.5px;max-width:600px;margin-bottom:20px;line-height:1.1;">Your personal cinematic universe, organized.</h1>
<p style="color:var(--text-muted);font-size:1.05rem;max-width:480px;margin-bottom:36px;line-height:1.5;">Track what you're watching, discover top-rated films, and manage your custom watchlist seamlessly.</p>
<a href="/register" class="btn-app" style="padding:16px 36px;font-size:0.9rem;">Create Your List Free</a>
</div>
</body>
</html>
"""
MAIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>The List</title>{BASE_CSS}</head>
<body>
<div class="app-header">
<a href="/" class="brand-logo">{LOGO_SVG} <span>THE LIST</span></a>
<div class="app-user-actions">
<button onclick="openModal()" class="btn-app">+ Add Title</button>
<span style="font-weight:600;font-size:0.8rem;letter-spacing:1px;text-transform:uppercase;color:var(--text-muted);">{{ username }}</span>
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
<option value="/?filter=All" {% if current_filter == 'All' %}selected{% endif %}>All Movies</option>
<option value="/?filter=Watching" {% if current_filter == 'Watching' %}selected{% endif %}>Watching</option>
<option value="/?filter=Completed" {% if current_filter == 'Completed' %}selected{% endif %}>Completed</option>
<option value="/?filter=On Hold" {% if current_filter == 'On Hold' %}selected{% endif %}>On Hold</option>
<option value="/?filter=Dropped" {% if current_filter == 'Dropped' %}selected{% endif %}>Dropped</option>
<option value="/?filter=Plan to Watch" {% if current_filter == 'Plan to Watch' %}selected{% endif %}>Plan to Watch</option>
</select>
</div>
<div id="view-grid" class="app-grid">
{% for m in movies %}
<div class="app-card">
<div class="edit-badge" onclick='editMovie({{ m.id }}, {{ m.title|tojson }}, {{ m.genre|tojson }}, {{ m.status|tojson }}, {{ m.score }}, {{ m.poster_url|tojson }}, {{ m.comments|tojson }})'>✏️</div>
{% if m.poster_url %}
<img src="{{ m.poster_url }}" alt="{{ m.title }}" referrerpolicy="no-referrer">
{% else %}
<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:2rem;color:#888;">🎬</div>
{% endif %}
<div class="card-overlay">
<div class="card-title">{{ m.title }}</div>
<div class="card-meta"><span>{{ m.status }}</span><span class="score-star">⭐ {{ m.score }}</span></div>
</div>
</div>
{% endfor %}
</div>
<div id="view-list" style="display:none;">
<table class="app-list-table">
<thead><tr><th>Title</th><th>Status</th><th>Score</th><th>Notes</th><th>Action</th></tr></thead>
<tbody>
{% for m in movies %}
<tr>
<td style="font-weight:600;">{{ m.title }}</td>
<td>{{ m.status }}</td>
<td><span class="score-star">⭐ {{ m.score }}</span></td>
<td>{{ m.comments or "—" }}</td>
<td><a href="/delete/{{ m.id }}" style="color:#dc2626;text-decoration:none;font-weight:600;font-size:0.75rem;">Remove</a></td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
</div>

<!-- Search Section -->
<div id="section-search" style="display:none;">
<div class="app-title-bar"><h2>Search & Track</h2></div>
<div style="display:flex;gap:10px;margin-bottom:24px;">
<input type="text" id="liveSearchInput" placeholder="Search movies..." style="margin:0;padding:14px;flex:1;background:var(--bg-card);border:1px solid var(--border);color:var(--text-primary);border-radius:8px;">
<button type="button" onclick="performLiveSearch()" class="btn-app" style="padding:0 24px;">Search</button>
</div>
<div id="liveSearchResults" class="app-grid"></div>
</div>

<!-- News Section -->
<div id="section-news" style="display:none;">
<div class="app-title-bar"><h2>Cinema News</h2></div>
<div class="news-grid">
{% for article in news_items %}
<div class="news-card">
<div>
<div class="news-source">{{ article.source }}</div>
<h3 class="news-title">{{ article.title }}</h3>
</div>
<div class="news-footer"><span style="color:var(--text-muted);">{{ article.date }}</span><a href="{{ article.link }}" target="_blank" class="news-link">Read ↗</a></div>
</div>
{% endfor %}
</div>
</div>

<!-- Upcoming Section -->
<div id="section-upcoming" style="display:none;">
<div class="app-title-bar"><h2>Upcoming Releases</h2></div>
<div class="app-grid">
{% for up in upcoming %}
<div class="app-card">
<img src="{{ up.poster }}" referrerpolicy="no-referrer">
<div class="card-overlay">
<div class="card-title">{{ up.title }}</div>
<button onclick='quickAdd({{ up.title|tojson }}, "Upcoming", {{ up.poster|tojson }})' class="btn-app" style="margin-top:6px;padding:6px;font-size:0.68rem;">+ Add</button>
</div>
</div>
{% endfor %}
</div>
</div>

<!-- Top Rated Section -->
<div id="section-recommended" style="display:none;">
<div class="app-title-bar"><h2>Top Rated</h2></div>
<div class="app-grid">
{% for rec in recommendations %}
<div class="app-card">
<img src="{{ rec.poster }}" referrerpolicy="no-referrer">
<div class="card-overlay">
<div class="card-title">{{ rec.title }}</div>
<button onclick='quickAdd({{ rec.title|tojson }}, {{ rec.genre|tojson }}, {{ rec.poster|tojson }})' class="btn-app" style="margin-top:6px;padding:6px;font-size:0.68rem;">+ Add</button>
</div>
</div>
{% endfor %}
</div>
</div>
</div>

<!-- Modal -->
<div id="movieModal" class="modal-overlay">
<div class="modal-card">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
<h3 id="modalHeaderTitle" style="font-weight:300;font-size:1.4rem;">Add Movie</h3>
<button onclick="closeModal()" style="background:none;border:none;cursor:pointer;font-size:1.2rem;color:var(--text-primary);">✕</button>
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
    return render_template_string(AUTH_TEMPLATE, title="Register", error=error, BASE_CSS=BASE_CSS, LOGO_SVG=LOGO_SVG)

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
    return render_template_string(AUTH_TEMPLATE, title="Login", error=error, BASE_CSS=BASE_CSS, LOGO_SVG=LOGO_SVG)

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
