import datetime as dt

import pytest

from app.core.security import hash_password
from app.models import Utilisateur
from app.routers.paiements import statut_global, statut_tranche
from decimal import Decimal


@pytest.fixture
def eleve(client, auth_headers):
    resp = client.post(
        "/eleves", headers=auth_headers, json={"matricule": "P001", "nom": "Dossou", "prenom": "Afi"}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _tranche(client, h, montant, date_limite=None, libelle=None):
    resp = client.post(
        "/paiements/tranches",
        headers=h,
        json={"montant": montant, "date_limite": date_limite, "libelle": libelle},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _payer(client, h, eleve_id, tranche_id, montant, **extra):
    return client.post(
        f"/eleves/{eleve_id}/paiements",
        headers=h,
        json={"tranche_id": tranche_id, "montant_paye": montant, **extra},
    )


# ---------- Règles de statut ----------

def test_statut_tranche():
    j = dt.date(2026, 1, 10)
    assert statut_tranche(Decimal(100), Decimal(100), None, j) == "solde"
    assert statut_tranche(Decimal(100), Decimal(40), None, j) == "partiel"
    assert statut_tranche(Decimal(100), Decimal(0), None, j) == "non_paye"
    assert statut_tranche(Decimal(100), Decimal(40), dt.date(2026, 1, 9), j) == "en_retard"
    assert statut_tranche(Decimal(100), Decimal(0), dt.date(2026, 1, 10), j) == "non_paye"   # le jour J n'est pas en retard


def test_statut_global():
    assert statut_global([], Decimal(0)) == "aucune_tranche"
    assert statut_global(["solde", "solde"], Decimal(200)) == "solde"
    assert statut_global(["solde", "en_retard"], Decimal(100)) == "en_retard"
    assert statut_global(["solde", "non_paye"], Decimal(100)) == "partiel"
    assert statut_global(["non_paye", "non_paye"], Decimal(0)) == "non_paye"


# ---------- Tranches ----------

def test_tranches_numerotees_et_libellees(client, auth_headers, annee_active):
    t1 = _tranche(client, auth_headers, 60000)
    t2 = _tranche(client, auth_headers, 45000, libelle="Solde")
    assert (t1["numero"], t1["libelle"], t1["annee_scolaire_id"]) == (1, "1re tranche", annee_active.id)
    assert (t2["numero"], t2["libelle"]) == (2, "Solde")
    liste = client.get("/paiements/tranches", headers=auth_headers).json()
    assert [t["montant"] for t in liste] == [60000, 45000]


def test_tranche_avec_paiements_non_supprimable(client, auth_headers, eleve):
    t = _tranche(client, auth_headers, 50000)
    assert _payer(client, auth_headers, eleve["id"], t["id"], 10000).status_code == 201
    resp = client.delete(f"/paiements/tranches/{t['id']}", headers=auth_headers)
    assert resp.status_code == 409


def test_montant_tranche_pas_sous_le_deja_verse(client, auth_headers, eleve):
    t = _tranche(client, auth_headers, 50000)
    _payer(client, auth_headers, eleve["id"], t["id"], 30000)
    bas = client.patch(f"/paiements/tranches/{t['id']}", headers=auth_headers, json={"montant": 20000})
    assert bas.status_code == 409
    ok = client.patch(f"/paiements/tranches/{t['id']}", headers=auth_headers, json={"montant": 30000})
    assert ok.status_code == 200 and ok.json()["montant"] == 30000


# ---------- Paiements ----------

def test_paiement_partiel_puis_solde(client, auth_headers, eleve):
    t1 = _tranche(client, auth_headers, 60000)
    _tranche(client, auth_headers, 40000)

    p = _payer(client, auth_headers, eleve["id"], t1["id"], 25000, mode_paiement="mobile_money")
    assert p.status_code == 201, p.text
    assert p.json()["numero_recu"] == f"REC-{p.json()['id']:06d}"
    assert p.json()["enregistre_par_nom"] == "Test Admin"

    s = client.get(f"/eleves/{eleve['id']}/paiements", headers=auth_headers).json()
    assert (s["total_du"], s["total_paye"], s["reste"], s["statut"]) == (100000, 25000, 75000, "partiel")
    assert [t["statut"] for t in s["tranches"]] == ["partiel", "non_paye"]

    trop = _payer(client, auth_headers, eleve["id"], t1["id"], 40000)
    assert trop.status_code == 422
    assert "35 000" in trop.json()["detail"]

    assert _payer(client, auth_headers, eleve["id"], t1["id"], 35000).status_code == 201
    s = client.get(f"/eleves/{eleve['id']}/paiements", headers=auth_headers).json()
    assert s["tranches"][0]["statut"] == "solde"
    assert len(s["paiements"]) == 2

    deja = _payer(client, auth_headers, eleve["id"], t1["id"], 1000)
    assert deja.status_code == 409


def test_paiement_date_future_refusee(client, auth_headers, eleve):
    t = _tranche(client, auth_headers, 10000)
    demain = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    assert _payer(client, auth_headers, eleve["id"], t["id"], 5000, date_paiement=demain).status_code == 422


def test_tranche_echue_en_retard(client, auth_headers, eleve):
    hier = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    _tranche(client, auth_headers, 10000, date_limite=hier)
    s = client.get(f"/eleves/{eleve['id']}/paiements", headers=auth_headers).json()
    assert s["statut"] == "en_retard"


def test_annuler_paiement(client, auth_headers, eleve):
    t = _tranche(client, auth_headers, 10000)
    p = _payer(client, auth_headers, eleve["id"], t["id"], 10000).json()
    assert client.delete(f"/eleves/{eleve['id']}/paiements/{p['id']}", headers=auth_headers).status_code == 204
    s = client.get(f"/eleves/{eleve['id']}/paiements", headers=auth_headers).json()
    assert s["total_paye"] == 0 and s["paiements"] == []


def test_recu_fige_a_la_date_du_paiement(client, auth_headers, eleve):
    t = _tranche(client, auth_headers, 50000)
    _tranche(client, auth_headers, 50000)
    p1 = _payer(client, auth_headers, eleve["id"], t["id"], 20000).json()
    _payer(client, auth_headers, eleve["id"], t["id"], 30000)

    r = client.get(f"/paiements/{p1['id']}/recu", headers=auth_headers).json()
    assert r["eleve_matricule"] == "P001"
    assert r["paiement"]["montant_paye"] == 20000
    assert r["tranche_reste_apres"] == 30000       # le 2e versement n'existait pas encore
    assert (r["total_du"], r["total_paye_a_date"], r["reste_global"]) == (100000, 20000, 80000)


# ---------- Suivi ----------

def test_suivi_par_classe(client, auth_headers, niveau_3e):
    classe = client.post(
        "/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}
    ).json()
    ids = []
    for i in range(3):
        e = client.post(
            "/eleves",
            headers=auth_headers,
            json={"matricule": f"S{i}", "nom": f"Nom{i}", "prenom": "X", "classe_id": classe["id"]},
        ).json()
        ids.append(e["id"])
    t = _tranche(client, auth_headers, 30000)
    _payer(client, auth_headers, ids[0], t["id"], 30000)
    _payer(client, auth_headers, ids[1], t["id"], 10000)

    s = client.get("/paiements/suivi", headers=auth_headers, params={"classe_id": classe["id"]}).json()
    assert (s["nb_eleves"], s["nb_soldes"], s["total_attendu"], s["total_encaisse"], s["reste"]) == (
        3, 1, 90000, 40000, 50000,
    )
    assert [l["statut"] for l in s["lignes"]] == ["solde", "partiel", "non_paye"]
    assert s["lignes"][0]["dernier_paiement"] == dt.date.today().isoformat()


# ---------- Sécurité ----------

def test_enseignant_refuse(client, db, ecole, eleve):
    db.add(
        Utilisateur(
            ecole_id=ecole.id, nom="P", prenom="Q", email="prof.paie@test.local",
            mot_de_passe_hash=hash_password("motdepasse"), role="enseignant",
        )
    )
    db.flush()
    tok = client.post("/auth/login", data={"username": "prof.paie@test.local", "password": "motdepasse"})
    h = {"Authorization": f"Bearer {tok.json()['access_token']}"}
    assert client.get(f"/eleves/{eleve['id']}/paiements", headers=h).status_code == 403
    assert client.get("/paiements/suivi", headers=h).status_code == 403
    assert client.get("/paiements/tranches", headers=h).status_code == 403
