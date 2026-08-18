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

LOGO_SVG = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19.82 2H4.18C2.98 2 2 2.98 2 4.18v15.64C2 21.02 2.98 22 4.18 22h15.64c1.2 0 2.18-.98 2.18-2.18V4.18C22 2.98 21.02 2 19.82 2zM7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5"/></svg>'

BASE_CSS = """
<style>
:root { --bg-primary: #ffffff; --bg-secondary: #f4f4f5; --bg-card: #ffffff; --text-primary: #09090b; --text-muted: #71717a; --accent: #000000; --border: #e4e4e7; }
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
body { background-color: var(--bg-primary); color: var(--text-primary); min-height: 100vh; display: flex; flex-direction: column; }
.app-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 32px; border-bottom: 1px solid var(--border); background: var(--bg-secondary); }
.brand-logo { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1.1rem; letter-spacing: 2px; text-decoration: none; color: var(--text-primary); }
.app-user-actions { display: flex; align-items: center; gap: 16px; }
.container { max-width: 1200px; margin: 0 auto; padding: 32px 20px; width: 100%; flex: 1; }
.nav-tabs { display: flex; gap: 8px; border-bottom: 1px solid var(--border); margin-bottom: 32px; overflow-x: auto; padding-bottom: 8px; }
.nav-tab { background: none; border: none; color: var(--text-muted); padding: 8px 16px; font-weight: 600; font-size: 0.85rem; cursor: pointer; border-radius: 6px; white-space: nowrap; transition: 0.2s; }
.nav-tab.active { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border); }
.app-title-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.app-title-bar h2 { font-weight: 400; font-size: 1.6rem; letter-spacing: -0.5px; }
.view-icons { display: flex; gap: 8px; background: var(--bg-card); padding: 4px; border-radius: 8px; border: 1px solid var(--border); }
.view-icon { cursor: pointer; padding: 4px 10px; font-size: 0.9rem; color: var(--text-muted); border-radius: 6px; }
.view-icon.active { background: var(--bg-secondary); color: var(--text-primary); }
.app-select-container { margin-bottom: 24px; }
.app-select { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border); padding: 10px 16px; border-radius: 8px; font-size: 0.85rem; outline: none; }
.app-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }
.app-card { background: var(--bg-card); border-radius: 10px; overflow: hidden; border: 1px solid var(--border); position: relative; display: flex; flex-direction: column; height: 280px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.app-card img { width: 100%; height: 100%; object-fit: cover; }
.card-overlay { position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(to top, rgba(255,255,255,0.95), transparent); padding: 16px 12px 12px 12px; display: flex; flex-direction: column; justify-content: flex-end; height: 50%; }
.card-title { font-weight: 600; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px; color: #000; }
.card-meta { display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--text-muted); }
.score-star { color: #ca8a04; }
.edit-badge { position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.9); border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; cursor: pointer; z-index: 2; border: 1px solid var(--border); }
.btn-app { background: var(--text-primary); color: var(--bg-primary); border: none; padding: 10px 20px; border-radius: 8px; font-weight: 600; font-size: 0.8rem; cursor: pointer; text-decoration: none; display: inline-block; transition: opacity 0.2s; }
.btn-app:hover { opacity: 0.8; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: none; align-items: center; justify-content: center; z-index: 100; padding: 20px; }
.modal-card { background: var(--bg-primary); border: 1px solid var(--border); border-radius: 12px; width: 100%; max-width: 440px; padding: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }
.modal-card input, .modal-card select, .modal-card textarea { width: 100%; background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-primary); padding: 12px; border-radius: 8px; font-size: 0.85rem; margin-bottom: 12px; outline: none; }
.auth-wrapper { max-width: 380px; margin: auto; padding: 40px 20px; display: flex; flex-direction: column; justify-content: center; flex: 1; }
.news-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
.news-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; height: 180px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
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
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>The List - Authentication</title>
    {{ css|safe }}
</head>
<body>
    <header class="app-header">
        <a href="/" class="brand-logo">{{ logo|safe }} THE LIST</a>
    </header>
    <div class="auth-wrapper">
        <h2 style="margin-bottom: 24px; font-weight: 500; font-size: 1.5rem;">{{ title }}</h2>
        {% if error %}<p style="color: #ef4444; font-size: 0.85rem; margin-bottom: 16px;">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required style="width:100%; background:var(--bg-secondary); border:1px solid var(--border); color:var(--text-primary); padding:12px; border-radius:8px; font-size:0.85rem; margin-bottom:12px; outline:none;">
            <input type="password" name="password" placeholder="Password" required style="width:100%; background:var(--bg-secondary); border:1px solid var(--border); color:var(--text-primary); padding:12px; border-radius:8px; font-size:0.85rem; margin-bottom:20px; outline:none;">
            <button type="submit" class="btn-app" style="width: 100%;">{{ title }}</button>
        </form>
        <p style="margin-top: 20px; font-size: 0.85rem; color: var(--text-muted); text-align: center;">
            {% if is_register %}Already have an account? <a href="/login" style="color: var(--text-primary); font-weight: 600;">Log in</a>{% else %}Don't have an account? <a href="/register" style="color: var(--text-primary); font-weight: 600;">Register</a>{% endif %}
        </p>
    </div>
</body>
</html>
"""

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>The List</title>
    {{ css|safe }}
</head>
<body>
    <header class="app-header">
        <a href="/" class="brand-logo">{{ logo|safe }} THE LIST</a>
        <div class="app-user-actions">
            {% if username %}
                <button onclick="openModal()" class="btn-app">+ Add Title</button>
                <span style="font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">{{ username }}</span>
                <a href="/logout" style="font-size: 0.85rem; color: var(--text-muted); text-decoration: none;">Exit</a>
            {% else %}
                <a href="/login" class="btn-app">Log In</a>
            {% endif %}
        </div>
    </header>

    <div class="container">
        {% if username %}
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="switchTab('list')">My List</button>
            <button class="nav-tab" onclick="switchTab('search')">Search & Track</button>
            <button class="nav-tab" onclick="switchTab('news')">Cinema News</button>
        </div>

        <!-- TAB 1: MY LIST -->
        <div id="tab-list" class="tab-content">
            <div class="app-title-bar">
                <h2>My List</h2>
                <div class="view-icons">
                    <span class="view-icon active" onclick="setView('grid')">&#8862;</span>
                    <span class="view-icon" onclick="setView('table')">&#9776;</span>
                </div>
            </div>
            <div class="app-select-container">
                <select class="app-select" onchange="filterGenre(this.value)">
                    <option value="All">All Movies</option>
                    <option value="Action">Action</option>
                    <option value="Sci-Fi">Sci-Fi</option>
                    <option value="Drama">Drama</option>
                </select>
            </div>

            <div id="movie-grid-view" class="app-grid">
                {% for m in movies %}
                <div class="app-card" data-genre="{{ m.genre }}">
                    <div class="edit-badge" onclick="openEditModal('{{ m.id }}', '{{ m.title }}', '{{ m.genre }}', '{{ m.status }}', '{{ m.score }}', '{{ m.poster_url }}', '{{ m.comments }}')">&#9998;</div>
                    <img src="{{ m.poster_url or 'https://via.placeholder.com/300x450?text=No+Poster' }}" alt="{{ m.title }}">
                    <div class="card-overlay">
                        <div class="card-title">{{ m.title }}</div>
                        <div class="card-meta">
                            <span>{{ m.genre }}</span>
                            <span class="score-star">&#9733; {{ m.score }}/10</span>
                        </div>
                    </div>
                </div>
                {% else %}
                <p style="color: var(--text-muted); font-size: 0.85rem;">Your list is empty. Click "+ Add Title" to begin.</p>
                {% endfor %}
            </div>

            <div id="movie-table-view" style="display: none;">
                <table class="app-list-table">
                    <thead>
                        <tr><th>Title</th><th>Genre</th><th>Status</th><th>Score</th></tr>
                    </thead>
                    <tbody>
                        {% for m in movies %}
                        <tr>
                            <td>{{ m.title }}</td>
                            <td>{{ m.genre }}</td>
                            <td>{{ m.status }}</td>
                            <td>&#9733; {{ m.score }}/10</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- TAB 2: SEARCH & TRACK -->
        <div id="tab-search" class="tab-content" style="display: none;">
            <div class="app-title-bar"><h2>Recommended & Search</h2></div>
            <h3 style="font-size: 1rem; margin-bottom: 16px; font-weight: 600;">Top Recommendations</h3>
            <div class="app-grid" style="margin-bottom: 40px;">
                {% for rec in recommended %}
                <div class="app-card" onclick="quickAdd('{{ rec.title }}', '{{ rec.poster }}', '{{ rec.genre }}')" style="cursor: pointer;">
                    <img src="{{ rec.poster }}" alt="{{ rec.title }}">
                    <div class="card-overlay">
                        <div class="card-title">{{ rec.title }}</div>
                        <div class="card-meta"><span>Click to Track</span></div>
                    </div>
                </div>
                {% endfor %}
            </div>

            <h3 style="font-size: 1rem; margin-bottom: 16px; font-weight: 600;">Coming Soon</h3>
            <div class="app-grid">
                {% for up in upcoming %}
                <div class="app-card" onclick="quickAdd('{{ up.title }}', '{{ up.poster }}', 'Upcoming')" style="cursor: pointer;">
                    <img src="{{ up.poster }}" alt="{{ up.title }}">
                    <div class="card-overlay">
                        <div class="card-title">{{ up.title }}</div>
                        <div class="card-meta"><span>Coming Soon</span></div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- TAB 3: NEWS -->
        <div id="tab-news" class="tab-content" style="display: none;">
            <div class="app-title-bar"><h2>Cinema News</h2></div>
            <div class="news-grid">
                {% for n in news %}
                <div class="news-card">
                    <div>
                        <div class="news-source">{{ n.source }}</div>
                        <div class="news-title">{{ n.title }}</div>
                    </div>
                    <div class="news-footer">
                        <span>{{ n.date }}</span>
                        <a href="{{ n.link }}" target="_blank" class="news-link">Read &rarr;</a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        {% else %}
        <!-- LANDING PAGE FOR LOGGED OUT -->
        <div style="padding: 60px 0; text-align: center;">
            <h1 style="font-size: 3rem; font-weight: 400; letter-spacing: -1px; margin-bottom: 16px;">Track the action.<br>Track the list.</h1>
            <p style="color: var(--text-muted); font-size: 1rem; margin-bottom: 32px;">Start organizing your cinema collection today.</p>
            <a href="/register" class="btn-app" style="padding: 14px 28px; font-size: 0.9rem;">Get Started</a>
        </div>
        {% endif %}
    </div>

    <!-- MODAL ADD/EDIT -->
    <div id="addModal" class="modal-overlay">
        <div class="modal-card">
            <h3 id="modalTitle" style="margin-bottom: 16px; font-weight: 600; font-size: 1.1rem;">Add Movie</h3>
            <form id="movieForm" method="POST" action="/add">
                <input type="hidden" name="id" id="movieId">
                <input type="text" name="title" id="movieTitleInput" placeholder="Movie Title" required>
                <select name="genre" id="movieGenreInput">
                    <option value="Action">Action</option>
                    <option value="Sci-Fi">Sci-Fi</option>
                    <option value="Drama">Drama</option>
                    <option value="Comedy">Comedy</option>
                </select>
                <select name="status" id="movieStatusInput">
                    <option value="Want to Watch">Want to Watch</option>
                    <option value="Watched">Watched</option>
                </select>
                <input type="number" name="score" id="movieScoreInput" min="1" max="10" placeholder="Score (1-10)">
                <input type="text" name="poster_url" id="moviePosterInput" placeholder="Poster Image URL">
                <textarea name="comments" id="movieCommentsInput" placeholder="Comments..." rows="3"></textarea>
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    <button type="submit" class="btn-app" style="flex: 1;">Save</button>
                    <button type="button" onclick="closeModal()" style="background:var(--bg-secondary); border:1px solid var(--border); color:var(--text-primary); padding:10px 20px; border-radius:8px; font-weight:600; font-size:0.8rem; cursor:pointer; flex: 1;">Cancel</button>
                </div>
            </form>
            <form id="deleteForm" method="POST" action="/delete" style="margin-top: 8px;">
                <input type="hidden" name="id" id="deleteMovieId">
                <button type="submit" id="deleteBtn" style="display:none; width:100%; background:#ef4444; color:#fff; border:none; padding:10px; border-radius:8px; font-weight:600; font-size:0.8rem; cursor:pointer;">Delete Movie</button>
            </form>
        </div>
    </div>

    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
            document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + tab).style.display = 'block';
            event.target.classList.add('active');
        }
        function setView(view) {
            document.querySelectorAll('.view-icon').forEach(el => el.classList.remove('active'));
            if(view === 'grid') {
                document.getElementById('movie-grid-view').style.display = 'grid';
                document.getElementById('movie-table-view').style.display = 'none';
                event.target.classList.add('active');
            } else {
                document.getElementById('movie-grid-view').style.display = 'none';
                document.getElementById('movie-table-view').style.display = 'block';
                event.target.classList.add('active');
            }
        }
        function filterGenre(genre) {
            document.querySelectorAll('.app-card').forEach(card => {
                if(genre === 'All' || card.dataset.genre === genre) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });
        }
        function openModal() {
            document.getElementById('modalTitle').innerText = 'Add Movie';
            document.getElementById('movieForm').action = '/add';
            document.getElementById('movieId').value = '';
            document.getElementById('movieTitleInput').value = '';
            document.getElementById('movieScoreInput').value = '';
            document.getElementById('moviePosterInput').value = '';
            document.getElementById('movieCommentsInput').value = '';
            document.getElementById('deleteBtn').style.display = 'none';
            document.getElementById('addModal').style.display = 'flex';
        }
        function openEditModal(id, title, genre, status, score, poster, comments) {
            document.getElementById('modalTitle').innerText = 'Edit Movie';
            document.getElementById('movieForm').action = '/add';
            document.getElementById('movieId').value = id;
            document.getElementById('movieTitleInput').value = title;
            document.getElementById('movieGenreInput').value = genre;
            document.getElementById('movieStatusInput').value = status;
            document.getElementById('movieScoreInput').value = score;
            document.getElementById('moviePosterInput').value = poster;
            document.getElementById('movieCommentsInput').value = comments;
            document.getElementById('deleteMovieId').value = id;
            document.getElementById('deleteBtn').style.display = 'block';
            document.getElementById('addModal').style.display = 'flex';
        }
        function closeModal() {
            document.getElementById('addModal').style.display = 'none';
        }
        function quickAdd(title, poster, genre) {
            document.getElementById('modalTitle').innerText = 'Add to List';
            document.getElementById('movieForm').action = '/add';
            document.getElementById('movieId').value = '';
            document.getElementById('movieTitleInput').value = title;
            document.getElementById('movieGenreInput').value = genre;
            document.getElementById('movieStatusInput').value = 'Want to Watch';
            document.getElementById('movieScoreInput').value = '8';
            document.getElementById('moviePosterInput').value = poster;
            document.getElementById('movieCommentsInput').value = 'Added from recommendations';
            document.getElementById('deleteBtn').style.display = 'none';
            document.getElementById('addModal').style.display = 'flex';
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    if "user_id" not in session:
        return render_template_string(INDEX_TEMPLATE, css=BASE_CSS, logo=LOGO_SVG, username=None)
    
    conn = get_db_connection()
    movies = conn.execute("SELECT * FROM movies WHERE user_id = ?", (session["user_id"],)).fetchall()
    conn.close()
    
    recommended = fetch_recommended_movies()
    upcoming = fetch_upcoming_movies()
    news = fetch_movie_news()
    
    return render_template_string(INDEX_TEMPLATE, css=BASE_CSS, logo=LOGO_SVG, username=session.get("username"), movies=movies, recommended=recommended, upcoming=upcoming, news=news)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        error = "Invalid username or password"
    return render_template_string(AUTH_TEMPLATE, css=BASE_CSS, logo=LOGO_SVG, title="Log In", is_register=False, error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            error = "Username already exists"
    return render_template_string(AUTH_TEMPLATE, css=BASE_CSS, logo=LOGO_SVG, title="Register", is_register=True, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/add", methods=["POST"])
def add_movie():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    movie_id = request.form.get("id")
    title = request.form["title"]
    genre = request.form.get("genre", "Drama")
    status = request.form.get("status", "Want to Watch")
    score = request.form.get("score") or 0
    poster_url = request.form.get("poster_url", "")
    comments = request.form.get("comments", "")
    
    conn = get_db_connection()
    if movie_id:
        conn.execute("UPDATE movies SET title=?, genre=?, status=?, score=?, poster_url=?, comments=? WHERE id=? AND user_id=?",
                     (title, genre, status, score, poster_url, comments, movie_id, session["user_id"]))
    else:
        conn.execute("INSERT INTO movies (user_id, title, genre, status, score, poster_url, comments) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (session["user_id"], title, genre, status, score, poster_url, comments))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/delete", methods=["POST"])
def delete_movie():
    if "user_id" not in session:
        return redirect(url_for("login"))
    movie_id = request.form.get("id")
    conn = get_db_connection()
    conn.execute("DELETE FROM movies WHERE id=? AND user_id=?", (movie_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
