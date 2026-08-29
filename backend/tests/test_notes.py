"""Saisie et validation des notes, résolveur de coefficient, trimestres."""

import pytest


def _login(client, email, mdp="motdepasse123"):
    tok = client.post("/auth/login", data={"username": email, "password": mdp}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _mid(client, headers, nom):
    return next(m["id"] for m in client.get("/matieres", headers=headers).json() if m["nom"] == nom)


@pytest.fixture
def scenario(client, auth_headers, niveau_tle, serie_d):
    """Tle D + un élève dedans + un prof de Maths affecté + le trimestre 1."""
    classe = client.post(
        "/classes", headers=auth_headers,
        json={"nom": "Tle D", "niveau_id": niveau_tle.id, "serie_id": serie_d.id},
    ).json()
    eleve = client.post(
        "/eleves", headers=auth_headers,
        json={"matricule": "T-001", "nom": "Zinsou", "prenom": "Ivan", "classe_id": classe["id"]},
    ).json()
    prof = client.post(
        "/utilisateurs", headers=auth_headers,
        json={"nom": "P", "prenom": "M", "email": "prof.maths@ecole.bj",
              "mot_de_passe": "motdepasse123", "role": "enseignant"},
    ).json()
    maths = _mid(client, auth_headers, "Mathématiques")
    client.post(
        f"/utilisateurs/{prof['id']}/affectations", headers=auth_headers,
        json={"classe_id": classe["id"], "matiere_id": maths},
    )
    trimestres = client.get("/trimestres", headers=auth_headers).json()
    t1 = next(t["id"] for t in trimestres if t["numero"] == 1)
    return {
        "classe_id": classe["id"],
        "eleve_id": eleve["id"],
        "prof_headers": _login(client, "prof.maths@ecole.bj"),
        "maths_id": maths,
        "francais_id": _mid(client, auth_headers, "Français"),
        "conduite_id": _mid(client, auth_headers, "Conduite"),
        "trimestre_id": t1,
    }


# ---------- Résolveur de coefficient ----------

def test_classe_matieres_expose_les_coefficients(client, auth_headers, scenario):
    matieres = client.get(f"/classes/{scenario['classe_id']}/matieres", headers=auth_headers).json()
    par_nom = {m["nom"]: m for m in matieres}
    assert par_nom["Mathématiques"]["coefficient"] == 4.0      # Tle D, coefficient officiel
    assert par_nom["SVT"]["coefficient"] == 5.0
    assert par_nom["Conduite"]["coefficient"] == 1.0
    assert par_nom["Conduite"]["note_directe"] is True


def test_college_resout_niveau_sans_serie(client, auth_headers, niveau_3e):
    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    par_nom = {m["nom"]: m["coefficient"]
               for m in client.get(f"/classes/{classe['id']}/matieres", headers=auth_headers).json()}
    # 4e-3e : Maths = 3, EPS = 1 (exceptions) ; Conduite = 1 (explicite)
    assert par_nom["Mathématiques"] == 3.0
    assert par_nom["EPS"] == 1.0
    assert par_nom["Conduite"] == 1.0


# ---------- Trimestres ----------

def test_annee_active_a_trois_trimestres(client, auth_headers):
    assert sorted(t["numero"] for t in client.get("/trimestres", headers=auth_headers).json()) == [1, 2, 3]


def test_creer_une_annee_cree_ses_trois_trimestres(client, auth_headers):
    client.post(
        "/annees-scolaires", headers=auth_headers,
        json={"libelle": "2027-2028", "date_debut": "2027-09-15", "date_fin": "2028-07-15"},
    )
    annees = client.get("/annees-scolaires", headers=auth_headers).json()
    nouvelle = next(a["id"] for a in annees if a["libelle"] == "2027-2028")
    tri = client.get("/trimestres", headers=auth_headers, params={"annee_scolaire_id": nouvelle}).json()
    assert [t["numero"] for t in tri] == [1, 2, 3]


# ---------- Saisie par un enseignant ----------

def test_prof_saisit_une_note_complete(client, scenario):
    s = scenario
    res = client.put(
        "/notes", headers=s["prof_headers"],
        json={"eleve_id": s["eleve_id"], "matiere_id": s["maths_id"], "trimestre_id": s["trimestre_id"],
              "interro1": 12, "interro2": 12, "interro3": 12, "devoir1": 15, "devoir2": 9},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["statut"] == "calculee"
    assert body["moyenne"] == 12.0   # (12 + 15 + 9) / 3
    assert body["valide"] is False


def test_note_incomplete(client, scenario):
    s = scenario
    body = client.put(
        "/notes", headers=s["prof_headers"],
        json={"eleve_id": s["eleve_id"], "matiere_id": s["maths_id"], "trimestre_id": s["trimestre_id"],
              "interro1": 10},
    ).json()
    assert body["statut"] == "incomplete" and body["moyenne"] is None


def test_prof_ne_peut_pas_saisir_une_matiere_non_affectee(client, scenario):
    s = scenario
    res = client.put(
        "/notes", headers=s["prof_headers"],
        json={"eleve_id": s["eleve_id"], "matiere_id": s["francais_id"], "trimestre_id": s["trimestre_id"],
              "interro1": 10, "interro2": 10, "interro3": 10, "devoir1": 10, "devoir2": 10},
    )
    assert res.status_code == 403


def test_prof_ne_peut_pas_saisir_la_conduite(client, scenario):
    s = scenario
    res = client.put(
        "/notes", headers=s["prof_headers"],
        json={"eleve_id": s["eleve_id"], "matiere_id": s["conduite_id"],
              "trimestre_id": s["trimestre_id"], "note_directe": 14},
    )
    assert res.status_code == 403


def test_note_hors_bareme_refusee(client, scenario):
    s = scenario
    res = client.put(
        "/notes", headers=s["prof_headers"],
        json={"eleve_id": s["eleve_id"], "matiere_id": s["maths_id"], "trimestre_id": s["trimestre_id"],
              "interro1": 25},
    )
    assert res.status_code == 422


# ---------- Conduite (administration) ----------

def test_admin_saisit_la_conduite(client, auth_headers, scenario):
    s = scenario
    body = client.put(
        "/notes", headers=auth_headers,
        json={"eleve_id": s["eleve_id"], "matiere_id": s["conduite_id"],
              "trimestre_id": s["trimestre_id"], "note_directe": 13.5, "appreciation": "Correct"},
    ).json()
    assert body["statut"] == "directe" and body["moyenne"] == 13.5
    assert body["appreciation"] == "Correct"


def test_conduite_refuse_les_interros(client, auth_headers, scenario):
    s = scenario
    res = client.put(
        "/notes", headers=auth_headers,
        json={"eleve_id": s["eleve_id"], "matiere_id": s["conduite_id"],
              "trimestre_id": s["trimestre_id"], "interro1": 10},
    )
    assert res.status_code == 422


def test_matiere_normale_refuse_note_directe(client, auth_headers, scenario):
    s = scenario
    res = client.put(
        "/notes", headers=auth_headers,
        json={"eleve_id": s["eleve_id"], "matiere_id": s["maths_id"],
              "trimestre_id": s["trimestre_id"], "note_directe": 12},
    )
    assert res.status_code == 422


# ---------- Consultation ----------

def test_prof_ne_voit_que_ses_matieres_dans_la_grille(client, auth_headers, scenario):
    s = scenario
    client.put("/notes", headers=s["prof_headers"],
               json={"eleve_id": s["eleve_id"], "matiere_id": s["maths_id"], "trimestre_id": s["trimestre_id"],
                     "interro1": 10, "interro2": 10, "interro3": 10, "devoir1": 10, "devoir2": 10})
    client.put("/notes", headers=auth_headers,
               json={"eleve_id": s["eleve_id"], "matiere_id": s["conduite_id"], "trimestre_id": s["trimestre_id"],
                     "note_directe": 12})

    vue_admin = client.get("/notes", headers=auth_headers,
                           params={"classe_id": s["classe_id"], "trimestre_id": s["trimestre_id"]}).json()
    assert len(vue_admin) == 2
    vue_prof = client.get("/notes", headers=s["prof_headers"],
                          params={"classe_id": s["classe_id"], "trimestre_id": s["trimestre_id"]}).json()
    assert {n["matiere_id"] for n in vue_prof} == {s["maths_id"]}


# ---------- Validation ----------

def test_validation_verrouille_pour_le_prof_mais_pas_pour_l_admin(client, auth_headers, scenario):
    s = scenario
    note = client.put(
        "/notes", headers=s["prof_headers"],
        json={"eleve_id": s["eleve_id"], "matiere_id": s["maths_id"], "trimestre_id": s["trimestre_id"],
              "interro1": 11, "interro2": 11, "interro3": 11, "devoir1": 11, "devoir2": 11},
    ).json()

    v = client.post(f"/notes/{note['id']}/validation", headers=auth_headers, json={"valide": True}).json()
    assert v["valide"] is True

    # le prof ne peut plus modifier
    bloc = client.put(
        "/notes", headers=s["prof_headers"],
        json={"eleve_id": s["eleve_id"], "matiere_id": s["maths_id"], "trimestre_id": s["trimestre_id"],
              "interro1": 20},
    )
    assert bloc.status_code == 409

    # l'admin peut, et cela remet la validation à zéro
    maj = client.put(
        "/notes", headers=auth_headers,
        json={"eleve_id": s["eleve_id"], "matiere_id": s["maths_id"], "trimestre_id": s["trimestre_id"],
              "interro1": 13, "interro2": 13, "interro3": 13, "devoir1": 13, "devoir2": 13},
    ).json()
    assert maj["valide"] is False


def test_prof_ne_peut_pas_valider(client, scenario):
    s = scenario
    note = client.put(
        "/notes", headers=s["prof_headers"],
        json={"eleve_id": s["eleve_id"], "matiere_id": s["maths_id"], "trimestre_id": s["trimestre_id"],
              "interro1": 10, "interro2": 10, "interro3": 10, "devoir1": 10, "devoir2": 10},
    ).json()
    assert client.post(f"/notes/{note['id']}/validation", headers=s["prof_headers"], json={"valide": True}).status_code == 403


# ---------- Isolation entre écoles ----------

def test_un_autre_admin_ne_peut_pas_noter_notre_eleve(client, auth_headers, scenario, db):
    from app.core.security import hash_password
    from app.models import Ecole, Utilisateur

    autre = Ecole(nom="Autre", mode_calcul_moyenne_annuelle="poids_egal")
    db.add(autre)
    db.flush()
    db.add(Utilisateur(ecole_id=autre.id, nom="X", prenom="Y", email="x@autre.bj",
                       mot_de_passe_hash=hash_password("motdepasse123"), role="admin"))
    db.flush()

    s = scenario
    res = client.put(
        "/notes", headers=_login(client, "x@autre.bj"),
        json={"eleve_id": s["eleve_id"], "matiere_id": s["maths_id"], "trimestre_id": s["trimestre_id"],
              "interro1": 10},
    )
    assert res.status_code == 404
