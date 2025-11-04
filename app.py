from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3
import os
import random
import string

app = Flask(__name__, template_folder="templates")
app.secret_key = "supersecret"
CORS(app)

DB_FILE = "database.db"

# ----------------------------
# Database Setup
# ----------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            content TEXT DEFAULT '',
            locked INTEGER DEFAULT 0,
            password TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

# ----------------------------
# Helper
# ----------------------------
def get_workspace(name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name, content, locked, password FROM workspaces WHERE name=?", (name,))
    ws = c.fetchone()
    conn.close()
    return ws

def generate_random_text():
    # default random starter code/text
    sample_snippets = [
        "print('Hello, World!')",
        "# Welcome to your new workspace!",
        "def greet(name):\n    return f'Hello {name}'",
        "// Write your awesome code here!",
        "<!-- HTML Template -->\n<h1>Welcome!</h1>"
    ]
    return random.choice(sample_snippets)

# ----------------------------
# API Routes
# ----------------------------
@app.route("/api/<name>", methods=["GET", "POST"])
def workspace_api(name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if request.method == "GET":
        ws = get_workspace(name)
        if not ws:
            # auto-create new workspace
            default_code = generate_random_text()
            c.execute("INSERT INTO workspaces (name, content) VALUES (?, ?)", (name, default_code))
            conn.commit()
            conn.close()
            return jsonify({"workspace_name": name, "code": default_code, "locked": False})

        conn.close()
        return jsonify({
            "workspace_name": ws[0],
            "code": ws[1],
            "locked": bool(ws[2])
        })

    if request.method == "POST":
        data = request.get_json()
        code = data.get("code", "")
        ws = get_workspace(name)
        if ws:
            c.execute("UPDATE workspaces SET content=? WHERE name=?", (code, name))
        else:
            c.execute("INSERT INTO workspaces (name, content) VALUES (?, ?)", (name, code))
        conn.commit()
        conn.close()
        return jsonify({"status": "saved"})

@app.route("/api/<name>/lock", methods=["POST"])
def lock_workspace(name):
    data = request.get_json()
    password = data.get("password", "")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE workspaces SET locked=1, password=? WHERE name=?", (password, name))
    conn.commit()
    conn.close()
    return jsonify({"status": "locked"})

@app.route("/api/<name>/unlock", methods=["POST"])
def unlock_workspace(name):
    data = request.get_json()
    password = data.get("password", "")
    ws = get_workspace(name)
    if not ws:
        return jsonify({"error": "Workspace not found"}), 404

    correct_password = ws[3]
    if correct_password == password:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE workspaces SET locked=0 WHERE name=?", (name,))
        conn.commit()
        conn.close()
        return jsonify({"status": "unlocked", "code": ws[1]})
    else:
        return jsonify({"error": "Invalid password"}), 401

@app.route("/api/test")
def test():
    return jsonify({"message": "SQLite working!"})

# ----------------------------
# Workspace Page Routes
# ----------------------------
@app.route("/")
def home():
    # redirect or render default workspace page
    random_name = ''.join(random.choices(string.ascii_lowercase, k=6))
    return render_template("index.html", workspace_name=random_name)

@app.route("/<name>")
def workspace_page(name):
    # always render index.html for any workspace route
    return render_template("index.html", workspace_name=name)

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
