import os
import sqlite3
import urllib.request
import json
import urllib.parse
import csv
import io
import xml.etree.ElementTree as ET
from flask import Flask, redirect, render_template_string, request, session, url_for, Response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "the_list_secret_key_98765_change_me"

# SQLite DB Setup
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                genre TEXT DEFAULT '',
                status TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                poster_url TEXT DEFAULT '',
                comments TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        cursor.execute("PRAGMA table_info(movies)")
        cols = [col[1] for col in cursor.fetchall()]
        if "poster_url" not in cols:
            cursor.execute("ALTER TABLE movies ADD COLUMN poster_url TEXT DEFAULT ''")
        if "comments" not in cols:
            cursor.execute("ALTER TABLE movies ADD COLUMN comments TEXT DEFAULT ''")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database initialization error: {e}")

init_db()

# Automated News Fetcher (Google News RSS)
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
                title = parts[0]
                source = parts[1]

            if pub_date:
                pub_date = pub_date[:16]

            items.append({
                "title": title,
                "link": link,
                "date": pub_date,
                "source": source
            })
        return items
    except Exception as e:
        print(f"Error fetching news feed: {e}")
        return []

TMDB_API_KEY = "712a9f047a4b914389fae85321120ec1"

def fetch_tmdb_movies(query):
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={encoded_query}&include_adult=false&language=en-US&page=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        results = []
        for movie in data.get('results', []):
            poster_path = movie.get('poster_path')
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/300x450?text=No+Poster"
            
            results.append({
                "id": movie.get('id'),
                "title": movie.get('title', 'Untitled'),
                "release": movie.get('release_date', 'N/A')[:4],
                "genre": "Cinema",
                "score": round(float(movie.get('vote_average', 0)), 1),
                "poster": poster_url,
                "overview": movie.get('overview', '')
            })
        return results
    except Exception as e:
        print(f"Error querying TMDb API: {e}")
        return []

def fetch_upcoming_movies():
    try:
        url = f"https://api.themoviedb.org/3/movie/upcoming?api_key={TMDB_API_KEY}&language=en-US&page=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        items = []
        for movie in data.get('results', [])[:12]:
            poster_path = movie.get('poster_path')
            items.append({
                "id": movie.get('id'),
                "title": movie.get('title', 'Untitled'),
                "release": movie.get('release_date', 'Coming Soon'),
                "poster": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/300x450"
            })
        return items
    except Exception:
        return []

def fetch_recommended_movies():
    try:
        url = f"https://api.themoviedb.org/3/movie/top_rated?api_key={TMDB_API_KEY}&language=en-US&page=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        items = []
        for movie in data.get('results', [])[:12]:
            poster_path = movie.get('poster_path')
            items.append({
                "id": movie.get('id'),
                "title": movie.get('title', 'Untitled'),
                "genre": "Top Rated",
                "score": round(float(movie.get('vote_average', 0)), 1),
                "poster": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/300x450"
            })
        return items
    except Exception:
        return []

LOGO_SVG = """<svg width="26" height="16" viewBox="0 0 120 60" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle;"><circle cx="25" cy="30" r="18" stroke="currentColor" stroke-width="10"/><circle cx="60" cy="30" r="22" stroke="currentColor" stroke-width="11"/><circle cx="95" cy="30" r="18" stroke="currentColor" stroke-width="10"/></svg>"""
BASE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600;700&display=swap');

    :root[data-theme="light"] {
        --bg: #f1f1f1;
        --card-bg: #ffffff;
        --border: #e2e2e2;
        --text-primary: #111111;
        --text-muted: #777777;
        --accent: #181818;
        --input-bg: #ffffff;
    }

    :root[data-theme="dim"] {
        --bg: #1e2530;
        --card-bg: #283141;
        --border: #3a4659;
        --text-primary: #e6edf3;
        --text-muted: #9ba7b6;
        --accent: #3b82f6;
        --input-bg: #1e2530;
    }

    :root[data-theme="dark"] {
        --bg: #0a0a0a;
        --card-bg: #141414;
        --border: #262626;
        --text-primary: #f5f5f5;
        --text-muted: #888888;
        --accent: #ffffff;
        --input-bg: #0a0a0a;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: var(--bg);
        color: var(--text-primary);
        min-height: 100vh;
        margin: 0;
        padding-bottom: 80px;
        transition: background-color 0.3s, color 0.3s;
    }

    .container { max-width: 950px; margin: 0 auto; padding: 0 20px; }

    .app-header {
        background: var(--bg);
        padding: 20px 8%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--border);
        position: sticky; top: 0; z-index: 100;
    }

    .brand-logo {
        display: flex;
        align-items: center;
        gap: 12px;
        text-decoration: none;
        color: var(--text-primary);
        font-weight: 600;
        letter-spacing: 3px;
        font-size: 0.85rem;
        text-transform: uppercase;
    }

    .tab-content { display: none !important; }
    .tab-content.active { display: block !important; }

    .bottom-nav-bar {
        position: fixed;
        bottom: 0; left: 0; width: 100%;
        height: 60px;
        background-color: var(--bg);
        border-top: 1px solid var(--border);
        display: flex;
        justify-content: space-around;
        align-items: center;
        z-index: 1000;
    }

    .nav-tab {
        background: transparent;
        color: var(--text-muted);
        border: none;
        font-size: 0.60rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        flex: 1; height: 100%;
        position: relative;
        transition: color 0.2s ease;
    }

    .nav-tab svg {
        width: 18px; height: 18px;
        margin-bottom: 3px;
        fill: none;
        stroke: var(--text-muted);
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
        transition: stroke 0.2s ease;
    }

    .nav-tab.active { color: var(--text-primary); }
    .nav-tab.active svg { stroke: var(--text-primary); }

    .nav-tab.active::after {
        content: ''; position: absolute;
        bottom: 0; left: 15%; right: 15%;
        height: 2px; background-color: var(--text-primary);
    }

    .app-title-bar {
        display: flex; justify-content: space-between;
        align-items: center; padding: 20px 0 16px 0;
    }

    .app-title-bar h2 { font-size: 1.8rem; font-weight: 200; letter-spacing: -1px; }

    .filter-bar {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px; margin-bottom: 20px;
    }

    .app-select, .app-input {
        width: 100%; padding: 12px 14px;
        background: var(--card-bg);
        color: var(--text-primary);
        border: 1px solid var(--border);
        font-size: 0.78rem; font-weight: 600;
        letter-spacing: 1px; text-transform: uppercase;
        outline: none;
    }

    .app-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
    @media (min-width: 600px) { .app-grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; } }

    .app-card {
        position: relative; aspect-ratio: 2 / 3;
        background: var(--card-bg); border: 1px solid var(--border);
        overflow: hidden;
    }

    .app-card img { width: 100%; height: 100%; object-fit: cover; display: block; }

    .card-overlay {
        position: absolute; bottom: 0; left: 0; right: 0;
        background: linear-gradient(0deg, rgba(0, 0, 0, 0.9) 0%, rgba(0, 0, 0, 0.4) 75%, rgba(0, 0, 0, 0) 100%);
        padding: 24px 10px 10px 10px; color: #ffffff;
        display: flex; flex-direction: column; gap: 3px;
    }

    .card-title { font-size: 0.82rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .card-meta { display: flex; justify-content: space-between; align-items: center; font-size: 0.72rem; color: #dddddd; }

    .btn-app {
        background: var(--accent); color: var(--bg);
        border: none; padding: 10px 18px; font-weight: 700;
        font-size: 0.75rem; letter-spacing: 1.5px;
        text-transform: uppercase; cursor: pointer;
        text-decoration: none; display: inline-block;
    }

    .btn-secondary-app {
        background: transparent; color: var(--text-primary);
        border: 1px solid var(--border); padding: 9px 14px;
        font-weight: 600; font-size: 0.72rem;
        letter-spacing: 1px; text-transform: uppercase; cursor: pointer;
    }

    .theme-selector {
        display: grid; grid-template-columns: repeat(3, 1fr);
        gap: 12px; margin-top: 10px; margin-bottom: 24px;
    }

    .theme-btn {
        padding: 14px; border: 1px solid var(--border);
        background: var(--card-bg); color: var(--text-primary);
        font-weight: 600; font-size: 0.75rem;
        letter-spacing: 1px; text-transform: uppercase;
        cursor: pointer; text-align: center;
    }

    .theme-btn.active { border-color: var(--text-primary); outline: 2px solid var(--text-primary); }

    .modal-backdrop {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0, 0, 0, 0.7); display: none;
        justify-content: center; align-items: center; z-index: 2000;
    }
    .modal-content {
        background: var(--card-bg); border: 1px solid var(--border);
        padding: 24px; width: 90%; max-width: 450px;
        color: var(--text-primary);
    }
</style>
"""
APP_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard — The List</title>
    """ + BASE_CSS + """
</head>
<body>

    <header class="app-header">
        <a href="/" class="brand-logo">
            """ + LOGO_SVG + """ <span>THE LIST</span>
        </a>
    </header>

    <div class="container">

        <!-- TAB 1: COLLECTION (VAULT) -->
        <div id="collection-view" class="tab-content active">
            <div class="app-title-bar">
                <h2>My Collection</h2>
                <button class="btn-app" onclick="openAddModal()">+ ADD</button>
            </div>

            <form method="GET" action="/dashboard" class="filter-bar">
                <select name="status" class="app-select" onchange="this.form.submit()">
                    <option value="ALL" {% if current_status == 'ALL' %}selected{% endif %}>STATUS: ALL</option>
                    <option value="WATCHED" {% if current_status == 'WATCHED' %}selected{% endif %}>WATCHED</option>
                    <option value="PLAN TO WATCH" {% if current_status == 'PLAN TO WATCH' %}selected{% endif %}>PLAN TO WATCH</option>
                </select>

                <select name="genre" class="app-select" onchange="this.form.submit()">
                    <option value="ALL" {% if current_genre == 'ALL' %}selected{% endif %}>GENRE: ALL</option>
                    {% for g in genres %}
                        <option value="{{ g }}" {% if current_genre == g %}selected{% endif %}>{{ g }}</option>
                    {% endfor %}
                </select>

                <select name="sort" class="app-select" onchange="this.form.submit()">
                    <option value="TITLE" {% if current_sort == 'TITLE' %}selected{% endif %}>SORT: TITLE</option>
                    <option value="SCORE" {% if current_sort == 'SCORE' %}selected{% endif %}>SORT: HIGHEST SCORE</option>
                </select>
            </form>

            {% if user_movies %}
                <div class="app-grid">
                    {% for movie in user_movies %}
                        <div class="app-card">
                            <img src="{{ movie.poster_url if movie.poster_url else 'https://via.placeholder.com/300x450?text=No+Poster' }}" alt="{{ movie.title }}">
                            <div class="card-overlay">
                                <div class="card-title">{{ movie.title }}</div>
                                <div class="card-meta">
                                    <span>{{ movie.genre if movie.genre else 'Cinema' }}</span>
                                    <span>★ {{ movie.score }}</span>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            {% else %}
                <div style="text-align: center; padding: 60px 20px; background: var(--card-bg); border: 1px solid var(--border);">
                    <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 16px;">Your movie vault is empty.</p>
                    <button class="btn-app" onclick="openAddModal()">Add Your First Movie</button>
                </div>
            {% endif %}
        </div>

        <!-- TAB 2: SEARCH -->
        <div id="search-view" class="tab-content">
            <div class="app-title-bar">
                <h2>Search TMDB</h2>
            </div>
            <div style="display: flex; gap: 10px; margin-bottom: 24px;">
                <input type="text" id="tmdb-search-input" class="app-input" placeholder="Search movies online...">
                <button class="btn-app" onclick="executeTmdbSearch()">SEARCH</button>
            </div>
            <div id="tmdb-search-results" class="app-grid"></div>
        </div>

        <!-- TAB 3: NEWS -->
        <div id="news-view" class="tab-content">
            <div class="app-title-bar">
                <h2>Cinema News</h2>
            </div>
            <div class="news-grid">
                {% for item in news_feed %}
                    <div class="news-card" style="background: var(--card-bg); border: 1px solid var(--border); padding: 16px; margin-bottom: 12px;">
                        <div class="news-source" style="font-size: 0.7rem; color: var(--text-muted);">{{ item.source }}</div>
                        <div class="news-title" style="font-weight: 600; margin: 8px 0;">{{ item.title }}</div>
                        <a href="{{ item.link }}" target="_blank" class="btn-secondary-app" style="text-decoration: none; display: inline-block;">READ ARTICLE →</a>
                    </div>
                {% endfor %}
            </div>
        </div>

        <!-- TAB 4: UPCOMING -->
        <div id="upcoming-view" class="tab-content">
            <div class="app-title-bar">
                <h2>Upcoming Releases</h2>
            </div>
            <div class="app-grid">
                {% for movie in upcoming_movies %}
                    <div class="app-card">
                        <img src="{{ movie.poster }}" alt="{{ movie.title }}">
                        <div class="card-overlay">
                            <div class="card-title">{{ movie.title }}</div>
                            <div class="card-meta">
                                <span>Release</span>
                                <span>{{ movie.release }}</span>
                            </div>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <!-- TAB 5: DATA -->
        <div id="data-view" class="tab-content">
            <div class="app-title-bar">
                <h2>Manage Data</h2>
            </div>
            <div style="background: var(--card-bg); border: 1px solid var(--border); padding: 24px; max-width: 500px;">
                <h3 style="font-size: 0.9rem; font-weight: 600; margin-bottom: 12px;">Export Backup</h3>
                <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 18px;">Download your collection backup in CSV format.</p>
                <a href="/export_csv" class="btn-app">DOWNLOAD CSV</a>
            </div>
        </div>

        <!-- TAB 6: SETTINGS -->
        <div id="settings-view" class="tab-content">
            <div class="app-title-bar">
                <h2>Account Settings</h2>
            </div>
            <div style="background: var(--card-bg); border: 1px solid var(--border); padding: 24px; max-width: 500px;">
                <label style="font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: var(--text-muted);">Theme Appearance</label>
                <div class="theme-selector">
                    <button type="button" class="theme-btn" id="theme-btn-light" onclick="setTheme('light')">Light</button>
                    <button type="button" class="theme-btn" id="theme-btn-dim" onclick="setTheme('dim')">Dim</button>
                    <button type="button" class="theme-btn" id="theme-btn-dark" onclick="setTheme('dark')">Dark</button>
                </div>

                <hr style="border: 0; border-top: 1px solid var(--border); margin: 20px 0;">

                <label style="font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: var(--text-muted);">Account Actions</label>
                <div style="margin-top: 12px;">
                    <a href="/logout" class="btn-secondary-app" style="color: #dc2626; border-color: #dc2626; text-decoration: none;">LOG OUT OF ACCOUNT</a>
                </div>
            </div>
        </div>

    </div>

    <!-- Add Movie Modal -->
    <div id="addModal" class="modal-backdrop">
        <div class="modal-content">
            <h3 style="font-size: 1.1rem; font-weight: 600; margin-bottom: 16px;">Add Movie to Vault</h3>
            <form method="POST" action="/add_movie">
                <input type="text" name="title" class="app-input" placeholder="Movie Title" required style="margin-bottom: 12px;">
                <input type="text" name="genre" class="app-input" placeholder="Genre (e.g. Sci-Fi)" style="margin-bottom: 12px;">
                <select name="status" class="app-select" style="margin-bottom: 12px;">
                    <option value="WATCHED">WATCHED</option>
                    <option value="PLAN TO WATCH">PLAN TO WATCH</option>
                </select>
                <input type="number" name="score" class="app-input" placeholder="Score (0 - 10)" min="0" max="10" style="margin-bottom: 12px;">
                <input type="text" name="poster_url" class="app-input" placeholder="Poster URL (Optional)" style="margin-bottom: 18px;">
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button type="button" class="btn-secondary-app" onclick="closeAddModal()">CANCEL</button>
                    <button type="submit" class="btn-app">SAVE MOVIE</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Bottom Navigation Bar -->
    <nav class="bottom-nav-bar">
        <button class="nav-tab active" id="tab-collection" onclick="switchTab('collection')">
            <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            <span>Vault</span>
        </button>
        <button class="nav-tab" id="tab-search" onclick="switchTab('search')">
            <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <span>Search</span>
        </button>
        <button class="nav-tab" id="tab-news" onclick="switchTab('news')">
            <svg viewBox="0 0 24 24"><path d="M19 20H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h10l5 5v11a2 2 0 0 1-2 2z"/></svg>
            <span>News</span>
        </button>
        <button class="nav-tab" id="tab-upcoming" onclick="switchTab('upcoming')">
            <svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/></svg>
            <span>Upcoming</span>
        </button>
        <button class="nav-tab" id="tab-data" onclick="switchTab('data')">
            <svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/></svg>
            <span>Data</span>
        </button>
        <button class="nav-tab" id="tab-settings" onclick="switchTab('settings')">
            <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            <span>Settings</span>
        </button>
    </nav>
"""
APP_TEMPLATE += """
    <script>
        function switchTab(tabId) {
            const allTabs = document.querySelectorAll('.tab-content');
            allTabs.forEach(tab => tab.classList.remove('active'));

            const allBtns = document.querySelectorAll('.nav-tab');
            allBtns.forEach(btn => btn.classList.remove('active'));

            const targetTab = document.getElementById(tabId + '-view');
            const targetBtn = document.getElementById('tab-' + tabId);

            if (targetTab) targetTab.classList.add('active');
            if (targetBtn) targetBtn.classList.add('active');

            localStorage.setItem('active_tab', tabId);
        }

        function setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('user_theme', theme);

            document.querySelectorAll('.theme-btn').forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.getElementById('theme-btn-' + theme);
            if (activeBtn) activeBtn.classList.add('active');
        }

        function openAddModal() {
            document.getElementById('addModal').style.display = 'flex';
        }

        function closeAddModal() {
            document.getElementById('addModal').style.display = 'none';
        }

        function executeTmdbSearch() {
            const query = document.getElementById('tmdb-search-input').value.trim();
            if (!query) return;

            const container = document.getElementById('tmdb-search-results');
            container.innerHTML = '<p style="color:var(--text-muted); grid-column: 1/-1;">Searching...</p>';

            fetch('/api/search?q=' + encodeURIComponent(query))
                .then(res => res.json())
                .then(data => {
                    if (data.length === 0) {
                        container.innerHTML = '<p style="color:var(--text-muted); grid-column: 1/-1;">No results found.</p>';
                        return;
                    }
                    container.innerHTML = data.map(m => `
                        <div class="app-card">
                            <img src="${m.poster}" alt="${m.title}">
                            <div class="card-overlay">
                                <div class="card-title">${m.title}</div>
                                <div class="card-meta">
                                    <span>${m.release}</span>
                                    <span>★ ${m.score}</span>
                                </div>
                            </div>
                        </div>
                    `).join('');
                })
                .catch(() => {
                    container.innerHTML = '<p style="color:var(--text-muted); grid-column: 1/-1;">Error loading results.</p>';
                });
        }

        document.addEventListener('DOMContentLoaded', () => {
            const savedTheme = localStorage.getItem('user_theme') || 'light';
            setTheme(savedTheme);

            const urlParams = new URLSearchParams(window.location.search);
            const tabParam = urlParams.get('tab');
            const savedTab = tabParam || localStorage.getItem('active_tab') || 'collection';
            switchTab(savedTab);
        });
    </script>
</body>
</html>
"""
AUTH_CSS = """
<style>
    body {
        display: flex; justify-content: center; align-items: center;
        min-height: 100vh; background: var(--bg); color: var(--text-primary);
    }
    .auth-card {
        background: var(--card-bg); border: 1px solid var(--border);
        padding: 36px; width: 100%; max-width: 380px; text-align: center;
    }
    .auth-card h2 { font-size: 1.2rem; font-weight: 600; margin-bottom: 20px; letter-spacing: 1px; }
    .auth-card input { margin-bottom: 14px; }
    .auth-card button { width: 100%; padding: 12px; margin-top: 6px; }
    .auth-link { display: block; margin-top: 18px; font-size: 0.75rem; color: var(--text-muted); text-decoration: none; }
    .error-banner { background: rgba(220, 38, 38, 0.1); color: #dc2626; border: 1px solid #dc2626; padding: 10px; font-size: 0.75rem; margin-bottom: 16px; }
</style>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8"><title>Login — The List</title>
    """ + BASE_CSS + AUTH_CSS + """
</head>
<body>
    <div class="auth-card">
        <div style="margin-bottom: 16px;">""" + LOGO_SVG + """</div>
        <h2>LOG IN</h2>
        {% if error %}<div class="error-banner">{{ error }}</div>{% endif %}
        <form method="POST" action="/login">
            <input type="text" name="username" class="app-input" placeholder="USERNAME" required>
            <input type="password" name="password" class="app-input" placeholder="PASSWORD" required>
            <button type="submit" class="btn-app">SIGN IN</button>
        </form>
        <a href="/register" class="auth-link">Need an account? Register here</a>
    </div>
    <script>
        document.documentElement.setAttribute('data-theme', localStorage.getItem('user_theme') || 'light');
    </script>
</body>
</html>
"""

REGISTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8"><title>Register — The List</title>
    """ + BASE_CSS + AUTH_CSS + """
</head>
<body>
    <div class="auth-card">
        <div style="margin-bottom: 16px;">""" + LOGO_SVG + """</div>
        <h2>CREATE ACCOUNT</h2>
        {% if error %}<div class="error-banner">{{ error }}</div>{% endif %}
        <form method="POST" action="/register">
            <input type="text" name="username" class="app-input" placeholder="USERNAME" required>
            <input type="password" name="password" class="app-input" placeholder="PASSWORD" required>
            <button type="submit" class="btn-app">REGISTER</button>
        </form>
        <a href="/login" class="auth-link">Already registered? Log in here</a>
    </div>
    <script>
        document.documentElement.setAttribute('data-theme', localStorage.getItem('user_theme') || 'light');
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        
        return render_template_string(LOGIN_TEMPLATE, error="Invalid username or password.")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template_string(REGISTER_TEMPLATE, error="All fields are required.")

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template_string(REGISTER_TEMPLATE, error="Username already taken.")

    return render_template_string(REGISTER_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    status_filter = request.args.get('status', 'ALL')
    genre_filter = request.args.get('genre', 'ALL')
    sort_filter = request.args.get('sort', 'TITLE')

    conn = get_db_connection()

    # Query setup
    query = "SELECT * FROM movies WHERE user_id = ?"
    params = [user_id]

    if status_filter != 'ALL':
        query += " AND status = ?"
        params.append(status_filter)

    if genre_filter != 'ALL':
        query += " AND genre = ?"
        params.append(genre_filter)

    if sort_filter == 'SCORE':
        query += " ORDER BY score DESC"
    else:
        query += " ORDER BY title ASC"

    user_movies = conn.execute(query, params).fetchall()

    # Get unique genres
    genres_query = conn.execute("SELECT DISTINCT genre FROM movies WHERE user_id = ? AND genre != ''", (user_id,)).fetchall()
    genres = [row['genre'] for row in genres_query]

    conn.close()

    news_feed = fetch_movie_news()
    upcoming_movies = fetch_upcoming_movies()

    return render_template_string(
        APP_TEMPLATE,
        user_movies=user_movies,
        genres=genres,
        current_status=status_filter,
        current_genre=genre_filter,
        current_sort=sort_filter,
        news_feed=news_feed,
        upcoming_movies=upcoming_movies
    )

@app.route('/add_movie', methods=['POST'])
def add_movie():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    title = request.form.get('title', '').strip()
    genre = request.form.get('genre', '').strip()
    status = request.form.get('status', 'WATCHED')
    score = request.form.get('score', 0)
    poster_url = request.form.get('poster_url', '').strip()

    if title:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO movies (user_id, title, genre, status, score, poster_url) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title, genre, status, score, poster_url)
        )
        conn.commit()
        conn.close()

    return redirect(url_for('dashboard', tab='collection'))

@app.route('/api/search')
def api_search():
    if 'user_id' not in session:
        return jsonify([])

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    results = fetch_tmdb_movies(query)
    return Response(json.dumps(results), mimetype='application/json')

@app.route('/export_csv')
def export_csv():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    movies = conn.execute("SELECT title, genre, status, score FROM movies WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Title', 'Genre', 'Status', 'Score'])

    for m in movies:
        writer.writerow([m['title'], m['genre'], m['status'], m['score']])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=my_movie_collection.csv"}
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
