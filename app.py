from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3
import os

# --------------------------------------------
# APP SETUP
# --------------------------------------------
app = Flask(__name__, template_folder="templates")
app.secret_key = "supersecret"
CORS(app)

DB_FILE = "database.db"


# --------------------------------------------
# DATABASE SETUP
# --------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            content TEXT DEFAULT '',
            locked INTEGER DEFAULT 0,
            password TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    conn.close()


# --------------------------------------------
# ROUTES
# --------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/workspaces", methods=["GET"])
def get_workspaces():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, locked FROM workspaces")
    rows = c.fetchall()
    conn.close()
    workspaces = [{"id": row[0], "name": row[1], "locked": bool(row[2])} for row in rows]
    return jsonify(workspaces)


@app.route("/api/workspaces/<int:ws_id>", methods=["GET"])
def get_workspace(ws_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, content, locked FROM workspaces WHERE id=?", (ws_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Workspace not found"}), 404
    return jsonify({
        "id": row[0],
        "name": row[1],
        "content": row[2],
        "locked": bool(row[3])
    })


@app.route("/api/workspaces", methods=["POST"])
def create_workspace():
    data = request.get_json()
    name = data.get("name", "Untitled")
    password = data.get("password", "")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO workspaces (name, password) VALUES (?, ?)", (name, password))
    conn.commit()
    conn.close()

    return jsonify({"message": "Workspace created"}), 201


@app.route("/api/workspaces/<int:ws_id>", methods=["PUT"])
def update_workspace(ws_id):
    data = request.get_json()
    content = data.get("content", "")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE workspaces SET content=? WHERE id=?", (content, ws_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Workspace updated"})


@app.route("/api/workspaces/<int:ws_id>/lock", methods=["POST"])
def lock_workspace(ws_id):
    data = request.get_json()
    password = data.get("password", "")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE workspaces SET locked=1, password=? WHERE id=?", (password, ws_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Workspace locked"})


@app.route("/api/workspaces/<int:ws_id>/unlock", methods=["POST"])
def unlock_workspace(ws_id):
    data = request.get_json()
    password = data.get("password", "")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password FROM workspaces WHERE id=?", (ws_id,))
    row = c.fetchone()

    if not row:
        return jsonify({"error": "Workspace not found"}), 404

    correct_password = row[0]
    if correct_password == password:
        c.execute("UPDATE workspaces SET locked=0 WHERE id=?", (ws_id,))
        conn.commit()
        message = "Workspace unlocked"
    else:
        message = "Incorrect password"
    conn.close()

    return jsonify({"message": message})


@app.route("/api/test", methods=["GET"])
def test():
    return jsonify({"message": "SQLite connection OK!"})


# --------------------------------------------
# MAIN ENTRY POINT
# --------------------------------------------
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
