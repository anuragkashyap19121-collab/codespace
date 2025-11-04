from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3
import os

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

# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/<name>", methods=["GET", "POST"])
def workspace_api(name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if request.method == "GET":
        ws = get_workspace(name)
        if not ws:
            # Create workspace automatically if not found
            c.execute("INSERT INTO workspaces (name) VALUES (?)", (name,))
            conn.commit()
            conn.close()
            return jsonify({"workspace_name": name, "code": "", "locked": False})
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

@app.route("/workspace/<name>")
def workspace_page(name):
    return render_template("index.html")

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
