from flask import Flask, jsonify, request, render_template, redirect, url_for
from flask_cors import CORS
import sqlite3
import os
import random
import string
from flask import session
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
            name TEXT UNIQUE,
            content TEXT DEFAULT '',
            locked INTEGER DEFAULT 0,
            password TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    conn.close()


def get_workspace(name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name, content, locked, password FROM workspaces WHERE name=?", (name,))
    ws = c.fetchone()
    conn.close()
    return ws


# --------------------------------------------
# ROUTES
# --------------------------------------------


ADMIN_PASSWORD = "andimandi"  # 🔒 change this to your own secure password


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin login page"""
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin_login.html", error="Invalid password!")
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    """Show list of all workspaces"""
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name, locked FROM workspaces ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    workspaces = [{"workspace_name": r[0], "locked": bool(r[1])} for r in rows]
    return render_template("workspaces.html", workspaces=workspaces)


@app.route("/admin/logout")
def admin_logout():
    """Logout admin"""
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/")
def home():
    """Redirects to a new random workspace."""
    new_name = "code" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    # Auto-create workspace entry in DB
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO workspaces (name) VALUES (?)", (new_name,))
    conn.commit()
    conn.close()
    return redirect(url_for("workspace_page", name=new_name))


@app.route("/<name>")
def workspace_page(name):
    """Renders the workspace page for a given name."""
    ws = get_workspace(name)
    if not ws:
        # Auto-create workspace if not found
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO workspaces (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
    return render_template("index.html", workspace_name=name)


# ------------- API ----------------

@app.route("/api/<name>", methods=["GET", "POST"])
def workspace_api(name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if request.method == "GET":
        ws = get_workspace(name)
        if not ws:
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


# --------------------------------------------
# MAIN ENTRY POINT
# --------------------------------------------
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
