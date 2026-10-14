"""
Emergency Readiness Forge — Flask app.

POST /api/analyze -> run engine.analyze(brief), persist session
GET /api/sessions -> list sessions
GET /api/sessions/<id> -> get a session
PATCH /api/sessions/<id> -> update rating/notes
GET /api/export/<id>?fmt=md|json -> export
GET / -> static/index.html
GET /api/health -> ping
"""

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, Response, abort

import engine

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = DATA_DIR / "sessions.db"

os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
app.config["JSON_SORT_KEYS"] = False


# --------------------------------------------------------------------------
# DB
# --------------------------------------------------------------------------

def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                brief TEXT NOT NULL,
                result_json TEXT NOT NULL,
                verdict TEXT,
                score INTEGER,
                rating INTEGER,
                notes TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        conn.commit()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def serialize_session(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "brief": row["brief"],
        "result": json.loads(row["result_json"]),
        "verdict": row["verdict"],
        "score": row["score"],
        "rating": row["rating"],
        "notes": row["notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def persist_session(brief: str, result: Dict[str, Any], rating: Optional[int] = None,
                    notes: Optional[str] = None) -> str:
    sid = uuid.uuid4().hex[:12]
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO sessions (id, brief, result_json, verdict, score, rating, notes, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sid,
                brief,
                json.dumps(result, ensure_ascii=False),
                result.get("score", {}).get("verdict"),
                result.get("score", {}).get("score"),
                rating,
                notes,
                now,
                now,
            ),
        )
        conn.commit()
    return sid


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "ts": int(time.time())})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    brief = (data.get("brief") or "").strip()
    if not brief:
        return jsonify({"error": "missing brief"}), 400
    if len(brief) > 8000:
        return jsonify({"error": "brief too long (max 8000 chars)"}), 400

    result = engine.analyze(brief)
    sid = persist_session(brief, result)
    return jsonify({"session_id": sid, "result": result})


@app.route("/api/sessions")
def list_sessions():
    with db() as conn:
        rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
    return jsonify({"sessions": [serialize_session(r) for r in rows]})


@app.route("/api/sessions/<sid>", methods=["GET"])
def get_session(sid):
    with db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    if not row:
        abort(404)
    return jsonify(serialize_session(row))


@app.route("/api/sessions/<sid>", methods=["PATCH"])
def patch_session(sid):
    data = request.get_json(silent=True) or {}
    fields = []
    values: List[Any] = []
    if "rating" in data:
        rating = int(data["rating"]) if data["rating"] is not None else None
        if rating is not None and not (1 <= rating <= 5):
            return jsonify({"error": "rating must be 1-5"}), 400
        fields.append("rating = ?")
        values.append(rating)
    if "notes" in data:
        fields.append("notes = ?")
        values.append(data["notes"])
    if not fields:
        return jsonify({"error": "no fields to update"}), 400
    values.append(int(time.time()))
    values.append(sid)
    with db() as conn:
        cur = conn.execute(
            f"UPDATE sessions SET {', '.join(fields)}, updated_at = ? WHERE id = ?",
            values,
        )
        conn.commit()
        if cur.rowcount == 0:
            abort(404)
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    return jsonify(serialize_session(row))


@app.route("/api/export/<sid>")
def export_session(sid):
    fmt = (request.args.get("fmt") or "md").lower()
    with db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    if not row:
        abort(404)
    result = json.loads(row["result_json"])
    if fmt in ("md", "markdown"):
        text = engine.render_markdown(result)
        return Response(text, mimetype="text/markdown",
                        headers={"Content-Disposition": f"attachment; filename=emergency-readiness-{sid}.md"})
    elif fmt == "json":
        return jsonify({
            "id": sid,
            "brief": row["brief"],
            "result": result,
            "rating": row["rating"],
            "notes": row["notes"],
        })
    else:
        return jsonify({"error": f"unknown fmt {fmt}"}), 400


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5031))
    print(f"emergency-readiness-forge on http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
