def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_login_ok(client, admin):
    resp = client.post("/auth/login", data={"username": admin.email, "password": "motdepasse"})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


def test_login_mauvais_mot_de_passe(client, admin):
    resp = client.post("/auth/login", data={"username": admin.email, "password": "faux"})
    assert resp.status_code == 401


def test_me_sans_jeton(client):
    assert client.get("/auth/me").status_code == 401


def test_me_avec_jeton(client, auth_headers, admin):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == admin.email
    assert resp.json()["roles"] == ["directeur"]
