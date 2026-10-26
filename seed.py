import sqlite3
from werkzeug.security import generate_password_hash

USERS = ["alice", "bob", "carol"]   # all use password: password123

ITEMS = [
    ("alice", "Blue water bottle", "Hydro Flask with a mountain sticker", "Library, 2nd floor", "2026-10-02", "https://picsum.photos/seed/bottle/400/300", 0),
    ("bob", "AirPods case", "White case, no earbuds inside", "Student Union food court", "2026-10-05", "https://picsum.photos/seed/airpods/400/300", 0),
    ("carol", "Black umbrella", "Compact, one broken spoke", "Engineering building lobby", "2026-10-06", "", 1),
    ("alice", "Calculus textbook", "Stewart 8th edition", "Math building room 101", "2026-10-09", "https://picsum.photos/seed/book/400/300", 0),
    ("bob", "Car keys", "Toyota key on a red lanyard", "Parking lot C", "2026-10-11", "https://picsum.photos/seed/keys/400/300", 1),
    ("carol", "Gray hoodie", "Size M, university logo", "Gym locker room", "2026-10-13", "https://picsum.photos/seed/hoodie/400/300", 0),
    ("alice", "Student ID card", "Name starts with J, bring ID to claim", "Bus stop on Main St", "2026-10-15", "", 0),
    ("bob", "Laptop charger", "USB-C 65W", "Library quiet study area", "2026-10-18", "https://picsum.photos/seed/charger/400/300", 0),
    ("carol", "Reading glasses", "Tortoiseshell frames in a blue case", "Lecture Hall B", "2026-10-20", "https://picsum.photos/seed/glasses/400/300", 0),
    ("alice", "Silver ring", "Thin band, found near the fountain", "Main quad", "2026-10-22", "https://picsum.photos/seed/ring/400/300", 1),
]


def seed(db_path):
    """Insert demo data only if the database is empty."""
    db = sqlite3.connect(db_path)
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        for u in USERS:
            db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                       (u, generate_password_hash("password123", method="pbkdf2:sha256")))
        for username, title, desc, loc, day, photo, returned in ITEMS:
            uid = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()[0]
            db.execute("""INSERT INTO items
                          (user_id, title, description, location, found_date, photo_url, returned)
                          VALUES (?, ?, ?, ?, ?, ?, ?)""",
                       (uid, title, desc, loc, day, photo, returned))
        db.commit()
    db.close()
    