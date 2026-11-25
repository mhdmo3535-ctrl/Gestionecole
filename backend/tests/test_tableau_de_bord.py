"""Tableau de bord : indicateurs par classe / niveau et visibilité selon le rôle."""

import datetime as dt

import pytest

from app.models import Note
from app.routers.tableau_de_bord import _jours_ouvres


def _login(client, email, mdp="motdepasse123"):
    tok = client.post("/auth/login", data={"username": email, "password": mdp}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _compte(client, auth_headers, email, *roles):
    client.post("/utilisateurs", headers=auth_headers, json={
        "nom": "T", "prenom": "T", "email": email, "mot_de_passe": "motdepasse123", "roles": list(roles)})
    return _login(client, email)


@pytest.fixture
def ecole_remplie(client, auth_headers, db, niveau_3e):
    """Une 3e de 2 élèves, notes du T1, une absence et une tranche partiellement payée."""
    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    a = client.post("/eleves", headers=auth_headers, json={
        "matricule": "A", "nom": "A", "prenom": "A", "sexe": "F", "classe_id": classe["id"]}).json()
    b = client.post("/eleves", headers=auth_headers, json={
        "matricule": "B", "nom": "B", "prenom": "B", "sexe": "M", "classe_id": classe["id"]}).json()
    t1 = next(t for t in client.get("/trimestres", headers=auth_headers).json() if t["numero"] == 1)

    maths = next(m["matiere_id"] for m in client.get(f"/classes/{classe['id']}/matieres", headers=auth_headers).json()
                 if m["nom"] == "Mathématiques")
    for eleve, valeur in ((a, 14), (b, 8)):
        db.add(Note(eleve_id=eleve["id"], matiere_id=maths, trimestre_id=t1["id"],
                    interro1=valeur, interro2=valeur, interro3=valeur, devoir1=valeur, devoir2=valeur))
    db.flush()

    # une journée d'absence un mercredi du T1
    client.post(f"/eleves/{a['id']}/absences", headers=auth_headers, json={"date": "2025-10-01"})

    tranche = client.post("/paiements/tranches", headers=auth_headers, json={"montant": 100000}).json()
    client.post(f"/eleves/{a['id']}/paiements", headers=auth_headers,
                json={"tranche_id": tranche["id"], "montant_paye": 100000})
    return {"classe": classe, "t1": t1}


def test_jours_ouvres_du_lundi_au_samedi():
    assert _jours_ouvres(dt.date(2026, 1, 5), dt.date(2026, 1, 11)) == 6     # lundi -> dimanche
    assert _jours_ouvres(dt.date(2026, 1, 10), dt.date(2026, 1, 10)) == 1    # samedi
    assert _jours_ouvres(dt.date(2026, 1, 11), dt.date(2026, 1, 11)) == 0    # dimanche
    assert _jours_ouvres(dt.date(2026, 1, 12), dt.date(2026, 1, 5)) == 0     # période vide


def test_directeur_voit_tout(client, auth_headers, ecole_remplie):
    s = ecole_remplie
    tdb = client.get("/tableau-de-bord", headers=auth_headers, params={"trimestre_id": s["t1"]["id"]}).json()

    assert tdb["effectifs"]["eleves_actifs"] == 2
    assert tdb["effectifs"]["filles"] == 1 and tdb["effectifs"]["garcons"] == 1

    assert tdb["scolarite"]["moyenne_ecole"] == 11.0          # (14 + 8) / 2
    assert tdb["scolarite"]["taux_reussite"] == 0.5

    jours = tdb["periode_presence"]["jours_ouvres"]
    assert jours > 0
    assert tdb["vie_scolaire"]["jours_absence"] == 1
    assert tdb["vie_scolaire"]["taux_presence"] == round(1 - 1 / (2 * jours), 4)

    assert tdb["finances"]["attendu"] == 200000 and tdb["finances"]["encaisse"] == 100000
    assert tdb["finances"]["taux_recouvrement"] == 0.5

    ligne = next(l for l in tdb["classes"] if l["classe_id"] == s["classe"]["id"])
    assert ligne["effectif"] == 2 and ligne["moyenne"] == 11.0 and ligne["taux_recouvrement"] == 0.5
    niveau = next(l for l in tdb["niveaux"] if l["niveau_nom"] == "3e")
    assert niveau["effectif"] == 2 and niveau["moyenne"] == 11.0


def test_alerte_classe_sans_professeur_principal(client, auth_headers, ecole_remplie):
    tdb = client.get("/tableau-de-bord", headers=auth_headers).json()
    assert "sans_pp" in {a["code"] for a in tdb["alertes"]}


def test_surveillant_ne_voit_que_la_vie_scolaire(client, auth_headers, ecole_remplie):
    h = _compte(client, auth_headers, "surv@ecole.bj", "surveillant")
    tdb = client.get("/tableau-de-bord", headers=h).json()
    assert tdb["vie_scolaire"] is not None
    assert tdb["scolarite"] is None and tdb["finances"] is None
    assert all(l["moyenne"] is None and l["taux_recouvrement"] is None for l in tdb["classes"])
    assert "impayes" not in {a["code"] for a in tdb["alertes"]}


def test_daf_ne_voit_que_les_finances(client, auth_headers, ecole_remplie):
    h = _compte(client, auth_headers, "daf@ecole.bj", "comptable")
    tdb = client.get("/tableau-de-bord", headers=h).json()
    assert tdb["finances"] is not None
    assert tdb["scolarite"] is None and tdb["vie_scolaire"] is None


def test_secretaire_sans_bilan_financier(client, auth_headers, ecole_remplie):
    h = _compte(client, auth_headers, "sec@ecole.bj", "secretaire")
    tdb = client.get("/tableau-de-bord", headers=h).json()
    assert tdb["finances"] is None and tdb["scolarite"] is None
    assert tdb["effectifs"]["eleves_actifs"] == 2


def test_enseignant_sans_tableau_de_bord(client, auth_headers):
    h = _compte(client, auth_headers, "prof@ecole.bj", "enseignant")
    assert client.get("/tableau-de-bord", headers=h).status_code == 403
