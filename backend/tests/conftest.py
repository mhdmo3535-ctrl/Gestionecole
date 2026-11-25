"""Fixtures de test.

Les tests tournent sur une base PostgreSQL dédiée (par défaut
``gestionecole_test``), recréée à partir de ``db/schema.sql`` + ``db/seed.sql``
au début de chaque session de test. Chaque test s'exécute dans une transaction
annulée à la fin : la base reste propre d'un test à l'autre.

Surcharge possible via la variable d'environnement ``TEST_DATABASE_URL``.
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.deps import get_db
from app.core.security import hash_password
from app.database import Base
from app.main import app
from app.models import AnneeScolaire, Ecole, Niveau, Serie, Utilisateur

DB_DIR = Path(__file__).resolve().parents[1] / "db"
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/gestionecole_test",
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL)
    fichiers = ["schema.sql", "seed.sql", "seed_coefficients.sql"]
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
        for nom in fichiers:
            conn.exec_driver_sql((DB_DIR / nom).read_text(encoding="utf-8"))
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    """Session isolée : tout est annulé (ROLLBACK) à la fin du test."""
    connection = engine.connect()
    trans = connection.begin()
    session = sessionmaker(bind=connection, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        if trans.is_active:          # un test peut avoir déclenché un abandon (IntegrityError)
            trans.rollback()
        connection.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def ecole(db) -> Ecole:
    return db.query(Ecole).filter_by(est_pilote=True).order_by(Ecole.id).first()


@pytest.fixture
def admin(db, ecole) -> Utilisateur:
    user = Utilisateur(
        ecole_id=ecole.id,
        nom="Admin",
        prenom="Test",
        email="admin@test.local",
        mot_de_passe_hash=hash_password("motdepasse"),
        roles=["directeur"],
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def auth_headers(client, admin) -> dict:
    resp = client.post(
        "/auth/login",
        data={"username": admin.email, "password": "motdepasse"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def annee_active(db, ecole) -> AnneeScolaire:
    return db.query(AnneeScolaire).filter_by(ecole_id=ecole.id, active=True).first()


@pytest.fixture
def niveau_3e(db) -> Niveau:
    return db.query(Niveau).filter_by(nom="3e").first()


@pytest.fixture
def niveau_tle(db) -> Niveau:
    return db.query(Niveau).filter_by(nom="Tle").first()


@pytest.fixture
def serie_d(db) -> Serie:
    return db.query(Serie).filter_by(nom="D").first()
