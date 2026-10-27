import os
import sqlite3
from datetime import date
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, g, abort)
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash, check_password_hash

from seed import seed

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me")
DB_PATH = os.environ.get("DB_PATH", "lostfound.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row   # lets us write row["title"]
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    with open(os.path.join(os.path.dirname(__file__), "schema.sql")) as f:
        db.executescript(f.read())
    db.close()


init_db()
seed(DB_PATH)


# ---------- auth helpers ----------

@app.before_request
def load_user():
    uid = session.get("user_id")
    g.user = (get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
              if uid else None)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


# ---------- pages ----------

ITEM_SELECT = """SELECT items.*, users.username
                 FROM items JOIN users ON users.id = items.user_id"""


def get_item_or_404(item_id):
    item = get_db().execute(ITEM_SELECT + " WHERE items.id = ?", (item_id,)).fetchone()
    if item is None:
        abort(404, f"Item #{item_id} does not exist.")
    return item


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    unclaimed = request.args.get("unclaimed") == "1"

    sql = ITEM_SELECT + " WHERE 1 = 1"
    params = []
    if q:
        sql += " AND (title LIKE ? OR description LIKE ? OR location LIKE ?)"
        params += [f"%{q}%"] * 3
    if unclaimed:
        sql += " AND returned = 0"
    sql += " ORDER BY found_date DESC"

    items = get_db().execute(sql, params).fetchall()
    return render_template("index.html", items=items, q=q, unclaimed=unclaimed)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None
        if not username or not password:
            error = "Username and password are required."
        elif len(username) > 30:
            error = "Username must be 30 characters or fewer."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        if error is None:
            try:
                db = get_db()
                db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                           (username, generate_password_hash(password, method="pbkdf2:sha256")))
                db.commit()
            except sqlite3.IntegrityError:
                error = f"Username '{username}' is already taken."
            else:
                flash("Account created. Please log in.", "success")
                return redirect(url_for("login"))
        flash(error, "error")
    return render_template("auth.html", title="Register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Wrong username or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome, {user['username']}!", "success")
            nxt = request.args.get("next", "")
            # only follow local paths, to avoid open redirects
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("index"))
    return render_template("auth.html", title="Log in")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("index"))


@app.route("/items/new", methods=["GET", "POST"])
@login_required
def new_item():
    if request.method == "POST":
        f = request.form
        title = f.get("title", "").strip()
        description = f.get("description", "").strip()
        location = f.get("location", "").strip()
        found_date = f.get("found_date", "")
        photo_url = f.get("photo_url", "").strip()

        errors = []
        if not title:
            errors.append("Please say what you found.")
        if not location:
            errors.append("Please say where you found it.")
        try:
            if date.fromisoformat(found_date) > date.today():
                errors.append("The date can't be in the future.")
        except ValueError:
            errors.append("Please enter a valid date.")
        if photo_url and not photo_url.startswith(("http://", "https://")):
            errors.append("Photo URL must start with http:// or https://")

        if errors:
            for e in errors:
                flash(e, "error")
        else:
            db = get_db()
            cur = db.execute("""INSERT INTO items (user_id, title, description, location, found_date, photo_url)
                                VALUES (?, ?, ?, ?, ?, ?)""",
                             (g.user["id"], title, description, location, found_date, photo_url))
            db.commit()
            flash("Item posted!", "success")
            return redirect(url_for("item_detail", item_id=cur.lastrowid))
    return render_template("new_item.html", today=date.today().isoformat())


@app.route("/items/<int:item_id>")
def item_detail(item_id):
    return render_template("item.html", item=get_item_or_404(item_id))


@app.route("/items/<int:item_id>/returned", methods=["POST"])
@login_required
def mark_returned(item_id):
    item = get_item_or_404(item_id)
    if item["user_id"] != g.user["id"]:
        abort(403, "You can only update your own posts.")
    db = get_db()
    db.execute("UPDATE items SET returned = 1 WHERE id = ?", (item_id,))
    db.commit()
    flash("Marked as returned. Nice work!", "success")
    return redirect(url_for("item_detail", item_id=item_id))


@app.route("/users/<username>")
def user_page(username):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user is None:
        abort(404, f"No user named '{username}'.")
    items = db.execute(ITEM_SELECT + " WHERE items.user_id = ? ORDER BY found_date DESC",
                       (user["id"],)).fetchall()
    unclaimed_count = sum(1 for i in items if not i["returned"])
    return render_template("user.html", user=user, items=items, unclaimed_count=unclaimed_count)


# ---------- errors ----------

@app.errorhandler(HTTPException)
def handle_http_error(e):
    return render_template("error.html", error=e), e.code


if __name__ == "__main__":
    app.run(debug=True, port=5001)
    