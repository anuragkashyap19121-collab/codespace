from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

app = Flask(__name__, template_folder="templates")
app.secret_key = "supersecret"
CORS(app)

mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["code_notepad"]
workspaces = db["workspaces"]

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # fallback

# ----------------------------
# 🔐 Workspace CRUD & Lock API
# ----------------------------
@app.route('/api/<workspace_name>', methods=['GET', 'POST'])
def handle_workspace(workspace_name):
    workspace = workspaces.find_one({"workspace_name": workspace_name})
    is_admin = session.get("is_admin", False)

    if request.method == 'GET':
        if not workspace:
            return jsonify({"workspace_name": workspace_name, "code": "", "locked": False})
        if workspace.get("locked") and not is_admin:
            return jsonify({"locked": True})
        return jsonify({
            "workspace_name": workspace["workspace_name"],
            "code": workspace.get("code", ""),
            "locked": workspace.get("locked", False)
        })

    if request.method == 'POST':
        data = request.get_json()
        workspaces.update_one(
            {"workspace_name": workspace_name},
            {"$set": {
                "code": data.get("code", ""),
                "last_updated": datetime.utcnow()
            }},
            upsert=True
        )
        return jsonify({"status": "saved"})


# ----------------------------
# 🔒 Lock / Unlock Endpoints
# ----------------------------
@app.route('/api/<workspace_name>/lock', methods=['POST'])
def lock_workspace(workspace_name):
    data = request.get_json()
    password = data.get("password")
    if not password:
        return jsonify({"error": "Password required"}), 400

    hashed_pw = generate_password_hash(password)
    workspaces.update_one(
        {"workspace_name": workspace_name},
        {"$set": {"locked": True, "password": hashed_pw}},
        upsert=True
    )
    return jsonify({"status": "locked"})


@app.route('/api/<workspace_name>/unlock', methods=['POST'])
def unlock_workspace(workspace_name):
    data = request.get_json()
    password = data.get("password")
    is_admin = session.get("is_admin", False)
    ws = workspaces.find_one({"workspace_name": workspace_name})

    if not ws:
        return jsonify({"error": "Workspace not found"}), 404

    if is_admin:
        return jsonify({"status": "unlocked", "code": ws.get("code", "")})

    if ws.get("password") and check_password_hash(ws["password"], password):
        workspaces.update_one({"workspace_name": workspace_name}, {"$set": {"locked": False}})
        return jsonify({"status": "unlocked", "code": ws.get("code", "")})
    else:
        return jsonify({"error": "Invalid password"}), 401


# ----------------------------
# 🧭 Admin Routes
# ----------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('secure_workspaces'))
        return render_template("admin_login.html", error="Invalid password")
    return render_template("admin_login.html")


@app.route('/admin')
def secure_workspaces():
    if not session.get("is_admin"):
        return redirect(url_for('admin_login'))
    all_ws = list(workspaces.find({}, {"workspace_name": 1, "_id": 0, "locked": 1}))
    for ws in all_ws:
        ws["locked"] = ws.get("locked", False)
    return render_template("workspaces.html", workspaces=all_ws)


@app.route('/admin/logout')
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for('admin_login'))


# ----------------------------
# 🧩 Editor Route
# ----------------------------
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_editor(path):
    return render_template('index.html')


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

