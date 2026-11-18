from datetime import date, timedelta

from conftest import login


def test_home_page_lists_seeded_items(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Blue water bottle" in resp.data
    assert b"Car keys" in resp.data


def test_search_filters_items(client):
    resp = client.get("/?q=umbrella")
    assert b"Black umbrella" in resp.data
    assert b"Blue water bottle" not in resp.data


def test_unclaimed_filter_hides_returned_items(client):
    resp = client.get("/?unclaimed=1")
    assert b"Blue water bottle" in resp.data
    assert b"Car keys" not in resp.data  # seeded as returned


def test_register_then_login(client):
    resp = client.post("/register", data={"username": "dave", "password": "secret1"},
                       follow_redirects=True)
    assert b"Account created" in resp.data
    resp = login(client, "dave", "secret1")
    assert b"Welcome, dave!" in resp.data


def test_register_rejects_short_password(client):
    resp = client.post("/register", data={"username": "erin", "password": "123"},
                       follow_redirects=True)
    assert b"at least 6 characters" in resp.data


def test_login_with_wrong_password_fails(client):
    resp = login(client, "alice", "nope")
    assert b"Wrong username or password" in resp.data


def test_posting_requires_login(client):
    resp = client.get("/items/new")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_logged_in_user_can_post_item(client):
    login(client)
    resp = client.post("/items/new", data={
        "title": "Green backpack",
        "description": "Has a keychain",
        "location": "Cafeteria",
        "found_date": date.today().isoformat(),
        "photo_url": "",
    }, follow_redirects=True)
    assert b"Item posted!" in resp.data
    assert b"Green backpack" in client.get("/").data


def test_post_rejects_future_date(client):
    login(client)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    resp = client.post("/items/new", data={
        "title": "Watch", "location": "Gym", "found_date": tomorrow,
    }, follow_redirects=True)
    assert b"can&#39;t be in the future" in resp.data or b"can't be in the future" in resp.data


def test_only_owner_can_mark_returned(client):
    login(client, "bob")
    resp = client.post("/items/1/returned")  # item 1 belongs to alice
    assert resp.status_code == 403


def test_missing_item_returns_404(client):
    assert client.get("/items/9999").status_code == 404
