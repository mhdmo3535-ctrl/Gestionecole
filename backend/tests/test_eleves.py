import pytest

from app.core.security import hash_password
from app.models import Utilisateur


@pytest.fixture
def enseignant(db, ecole):
    user = Utilisateur(
        ecole_id=ecole.id,
        nom="Prof",
        prenom="Test",
        email="prof@test.local",
        mot_de_passe_hash=hash_password("motdepasse"),
        roles=["enseignant"],
    )
    db.add(user)
    db.flush()
    return user


def _headers(client, email):
    resp = client.post("/auth/login", data={"username": email, "password": "motdepasse"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_creer_puis_lister_eleve(client, auth_headers):
    resp = client.post(
        "/eleves",
        headers=auth_headers,
        json={"matricule": "M001", "nom": "Kossi", "prenom": "Ama", "sexe": "F"},
    )
    assert resp.status_code == 201, resp.text
    eleve = resp.json()
    assert eleve["matricule"] == "M001"
    assert eleve["statut"] == "actif"

    liste = client.get("/eleves", headers=auth_headers).json()
    assert [e["matricule"] for e in liste] == ["M001"]


def test_matricule_en_double_refuse(client, auth_headers):
    payload = {"matricule": "M001", "nom": "Kossi", "prenom": "Ama"}
    assert client.post("/eleves", headers=auth_headers, json=payload).status_code == 201
    assert client.post("/eleves", headers=auth_headers, json=payload).status_code == 409


def test_recherche_par_nom(client, auth_headers):
    for m, nom in [("M1", "Adjovi"), ("M2", "Bello"), ("M3", "Adamou")]:
        client.post("/eleves", headers=auth_headers, json={"matricule": m, "nom": nom, "prenom": "X"})
    res = client.get("/eleves", headers=auth_headers, params={"q": "ad"}).json()
    assert {e["nom"] for e in res} == {"Adjovi", "Adamou"}


def test_modifier_eleve(client, auth_headers):
    eleve = client.post(
        "/eleves", headers=auth_headers, json={"matricule": "M9", "nom": "X", "prenom": "Y"}
    ).json()
    resp = client.patch(
        f"/eleves/{eleve['id']}", headers=auth_headers, json={"nom": "Nouveau", "statut": "archive"}
    )
    assert resp.status_code == 200
    assert resp.json()["nom"] == "Nouveau"
    assert resp.json()["statut"] == "archive"


def test_enseignant_ne_peut_pas_creer(client, enseignant):
    headers = _headers(client, enseignant.email)
    resp = client.post(
        "/eleves", headers=headers, json={"matricule": "M100", "nom": "A", "prenom": "B"}
    )
    assert resp.status_code == 403


def test_enseignant_peut_lister(client, enseignant, admin):
    admin_headers = _headers(client, admin.email)
    client.post("/eleves", headers=admin_headers, json={"matricule": "M1", "nom": "A", "prenom": "B"})
    resp = client.get("/eleves", headers=_headers(client, enseignant.email))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_acces_refuse_sans_jeton(client):
    assert client.get("/eleves").status_code == 401
