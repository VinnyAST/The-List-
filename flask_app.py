from flask import Flask, render_template_string, request, redirect, url_for
import os
import requests

app = Flask(__name__)

# HTML Template with integrated styling and layouts
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Movie & Media List</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background-color: #121212;
            color: #e0e0e0;
            margin: 0;
            padding: 0;
        }
        header {
            background-color: #1f1f1f;
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 2px solid #e50914;
        }
        .logo-container {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .logo-icon {
            font-size: 28px;
            color: #e50914;
        }
        h1 {
            color: #ffffff;
            font-size: 24px;
            margin: 0;
        }
        .container {
            max-width: 800px;
            margin: 30px auto;
            padding: 20px;
            background: #1e1e1e;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }
        form {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px;
            border: 1px solid #333;
            background: #2b2b2b;
            color: #fff;
            border-radius: 4px;
            font-size: 16px;
        }
        button {
            padding: 12px 20px;
            background-color: #e50914;
            color: white;
            border: none;
            border-radius: 4px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover {
            background-color: #b20710;
        }
        ul {
            list-style: none;
            padding: 0;
        }
        li {
            background: #2b2b2b;
            padding: 12px 15px;
            margin-bottom: 8px;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .delete-btn {
            background-color: #333;
            color: #ff5555;
            padding: 6px 10px;
            font-size: 14px;
            text-decoration: none;
            border-radius: 4px;
        }
        .delete-btn:hover {
            background-color: #ff5555;
            color: white;
        }
    </style>
</head>
<body>
    <header>
        <div class="logo-container">
            <span class="logo-icon">🎬</span>
            <h1>CineList</h1>
        </div>
    </header>

    <div class="container">
        <h3>Add to Your Watchlist</h3>
        <form method="POST" action="/add">
            <input type="text" name="item" placeholder="Search or type a movie name..." required>
            <button type="submit">Add Item</button>
        </form>

        <h3>Your Current List</h3>
        <ul>
            {% if items %}
                {% for item in items %}
                    <li>
                        <span>{{ item }}</span>
                        <a class="delete-btn" href="/delete/{{ loop.index0 }}">Remove</a>
                    </li>
                {% endfor %}
            {% else %}
                <p style="color: #777;">Your list is currently empty. Add something above!</p>
            {% endif %}
        </ul>
    </div>
</body>
</html>
"""

# Simple in-memory list storage (or you can expand this later)
watchlist = []

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, items=watchlist)

@app.route("/add", methods=["POST"])
def add_item():
    new_item = request.form.get("item")
    if new_item:
        watchlist.append(new_item)
    return redirect(url_for("home"))

@app.route("/delete/<int:index>")
def delete_item(index):
    if 0 <= index < len(watchlist):
        watchlist.pop(index)
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
