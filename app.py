import os
import sqlite3
from datetime import date
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, g, abort)
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


ITEM_SELECT = """SELECT items.*, users.username
                 FROM items JOIN users ON users.id = items.user_id"""


@app.route("/")
def index():
    items = get_db().execute(ITEM_SELECT + " ORDER BY found_date DESC").fetchall()
    return render_template("index.html", items=items)