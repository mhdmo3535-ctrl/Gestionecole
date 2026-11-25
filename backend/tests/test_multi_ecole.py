"""Cloisonnement des données entre écoles + unicité globale de l'email."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models import Ecole, Utilisateur


@pytest.fixture
def autre_ecole(db) -> Ecole:
    e = Ecole(nom="Autre école", mode_calcul_moyenne_annuelle="poids_egal", est_pilote=False)
    db.add(e)
    db.flush()
    return e


@pytest.fixture
def autre_admin(db, autre_ecole) -> Utilisateur:
    u = Utilisateur(
        ecole_id=autre_ecole.id,
        nom="Bar",
        prenom="Foo",
        email="admin@autre.local",
        mot_de_passe_hash=hash_password("motdepasse"),
        roles=["directeur"],
    )
    db.add(u)
    db.flush()
    return u


def _headers(client, email):
    tok = client.post("/auth/login", data={"username": email, "password": "motdepasse"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_un_admin_ne_voit_pas_les_eleves_d_une_autre_ecole(client, auth_headers, autre_admin):
    eleve = client.post(
        "/eleves", headers=auth_headers, json={"matricule": "P1", "nom": "Pilote", "prenom": "X"}
    ).json()

    autres = _headers(client, "admin@autre.local")
    assert client.get("/eleves", headers=autres).json() == []
    # même en visant directement l'id : introuvable
    assert client.get(f"/eleves/{eleve['id']}", headers=autres).status_code == 404
    assert client.patch(f"/eleves/{eleve['id']}", headers=autres, json={"nom": "Pirate"}).status_code == 404


def test_les_classes_sont_cloisonnees(client, auth_headers, autre_admin, niveau_3e):
    classe = client.post(
        "/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}
    ).json()

    autres = _headers(client, "admin@autre.local")
    # l'autre école n'a pas d'année active -> elle doit d'abord en créer une
    client.post(
        "/annees-scolaires",
        headers=autres,
        json={"libelle": "2025-2026", "date_debut": "2025-09-15", "date_fin": "2026-07-15"},
    )
    assert client.get("/classes", headers=autres).json() == []
    assert client.get(f"/classes/{classe['id']}", headers=autres).status_code == 404


def test_email_unique_au_niveau_global(db, ecole, autre_ecole):
    db.add(Utilisateur(
        ecole_id=ecole.id, nom="A", prenom="A", email="doublon@x.local",
        mot_de_passe_hash=hash_password("motdepasse"), roles=["directeur"],
    ))
    db.flush()
    db.add(Utilisateur(
        ecole_id=autre_ecole.id, nom="B", prenom="B", email="doublon@x.local",
        mot_de_passe_hash=hash_password("motdepasse"), roles=["directeur"],
    ))
    with pytest.raises(IntegrityError):
        db.flush()
