"""Tests des comptes utilisateurs et des affectations d'enseignants."""

PROF = {
    "nom": "Adjovi",
    "prenom": "Koffi",
    "email": "koffi.adjovi@ecole.bj",
    "mot_de_passe": "motdepasse123",
    "roles": ["enseignant"],
}


def _login(client, email, mdp="motdepasse123"):
    tok = client.post("/auth/login", data={"username": email, "password": mdp}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _id_matiere(client, headers, nom):
    matieres = client.get("/matieres", headers=headers).json()
    return next(m["id"] for m in matieres if m["nom"] == nom)


# ---------- Comptes ----------

def test_admin_cree_un_enseignant(client, auth_headers):
    res = client.post("/utilisateurs", headers=auth_headers, json=PROF)
    assert res.status_code == 201, res.text
    u = res.json()
    assert u["roles"] == ["enseignant"]
    assert u["email"] == "koffi.adjovi@ecole.bj"
    assert u["actif"] is True


def test_email_normalise_et_unique(client, auth_headers):
    client.post("/utilisateurs", headers=auth_headers, json=PROF)
    doublon = {**PROF, "email": "KOFFI.ADJOVI@ECOLE.BJ"}
    assert client.post("/utilisateurs", headers=auth_headers, json=doublon).status_code == 409


def test_role_parent_refuse_sur_cette_route(client, auth_headers):
    res = client.post("/utilisateurs", headers=auth_headers, json={**PROF, "roles": ["parent"]})
    assert res.status_code == 422


def test_enseignant_ne_peut_pas_creer_de_compte(client, auth_headers):
    client.post("/utilisateurs", headers=auth_headers, json=PROF)
    h = _login(client, PROF["email"])
    res = client.post("/utilisateurs", headers=h, json={**PROF, "email": "autre@ecole.bj"})
    assert res.status_code == 403


def test_lister_et_filtrer_par_role(client, auth_headers):
    client.post("/utilisateurs", headers=auth_headers, json=PROF)
    profs = client.get("/utilisateurs", headers=auth_headers, params={"role": "enseignant"}).json()
    assert [u["email"] for u in profs] == ["koffi.adjovi@ecole.bj"]
    directeurs = client.get("/utilisateurs", headers=auth_headers, params={"role": "directeur"}).json()
    assert directeurs and all("directeur" in u["roles"] for u in directeurs)


def test_desactiver_un_compte_bloque_la_connexion(client, auth_headers):
    uid = client.post("/utilisateurs", headers=auth_headers, json=PROF).json()["id"]
    assert client.patch(f"/utilisateurs/{uid}", headers=auth_headers, json={"actif": False}).status_code == 200
    resp = client.post("/auth/login", data={"username": PROF["email"], "password": PROF["mot_de_passe"]})
    assert resp.status_code == 403


def test_admin_ne_peut_pas_se_desactiver_lui_meme(client, auth_headers, admin):
    res = client.patch(f"/utilisateurs/{admin.id}", headers=auth_headers, json={"actif": False})
    assert res.status_code == 422


def test_reinitialiser_mot_de_passe(client, auth_headers):
    uid = client.post("/utilisateurs", headers=auth_headers, json=PROF).json()["id"]
    assert client.put(
        f"/utilisateurs/{uid}/mot-de-passe", headers=auth_headers, json={"nouveau_mot_de_passe": "nouveau-secret"}
    ).status_code == 204
    assert client.post("/auth/login", data={"username": PROF["email"], "password": "motdepasse123"}).status_code == 401
    assert client.post("/auth/login", data={"username": PROF["email"], "password": "nouveau-secret"}).status_code == 200


def test_isolation_entre_ecoles_sur_les_utilisateurs(client, auth_headers, db):
    from app.core.security import hash_password
    from app.models import Ecole, Utilisateur

    autre = Ecole(nom="Autre", mode_calcul_moyenne_annuelle="poids_egal")
    db.add(autre)
    db.flush()
    autre_admin = Utilisateur(
        ecole_id=autre.id, nom="X", prenom="Y", email="x@autre.bj",
        mot_de_passe_hash=hash_password("motdepasse123"), roles=["directeur"],
    )
    db.add(autre_admin)
    db.flush()

    uid = client.post("/utilisateurs", headers=auth_headers, json=PROF).json()["id"]
    h = _login(client, "x@autre.bj")
    assert client.get(f"/utilisateurs/{uid}", headers=h).status_code == 404


# ---------- Affectations ----------

def test_affecter_classe_matiere_a_un_enseignant(client, auth_headers, niveau_tle, serie_d):
    uid = client.post("/utilisateurs", headers=auth_headers, json=PROF).json()["id"]
    classe = client.post(
        "/classes", headers=auth_headers,
        json={"nom": "Tle D", "niveau_id": niveau_tle.id, "serie_id": serie_d.id},
    ).json()
    mid = _id_matiere(client, auth_headers, "Mathématiques")

    res = client.post(
        f"/utilisateurs/{uid}/affectations",
        headers=auth_headers,
        json={"classe_id": classe["id"], "matiere_id": mid},
    )
    assert res.status_code == 201, res.text
    a = res.json()
    assert a["classe_nom"] == "Tle D" and a["matiere_nom"] == "Mathématiques"


def test_affectation_en_double_refusee(client, auth_headers, niveau_3e):
    uid = client.post("/utilisateurs", headers=auth_headers, json=PROF).json()["id"]
    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    mid = _id_matiere(client, auth_headers, "Français")
    payload = {"classe_id": classe["id"], "matiere_id": mid}
    assert client.post(f"/utilisateurs/{uid}/affectations", headers=auth_headers, json=payload).status_code == 201
    assert client.post(f"/utilisateurs/{uid}/affectations", headers=auth_headers, json=payload).status_code == 409


def test_affectation_impossible_sur_un_admin(client, auth_headers, admin, niveau_3e):
    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    mid = _id_matiere(client, auth_headers, "Français")
    res = client.post(
        f"/utilisateurs/{admin.id}/affectations",
        headers=auth_headers,
        json={"classe_id": classe["id"], "matiere_id": mid},
    )
    assert res.status_code == 422


def test_enseignant_voit_ses_affectations_pas_celles_des_autres(client, auth_headers, niveau_3e):
    uid = client.post("/utilisateurs", headers=auth_headers, json=PROF).json()["id"]
    autre_uid = client.post(
        "/utilisateurs", headers=auth_headers, json={**PROF, "email": "autre.prof@ecole.bj"}
    ).json()["id"]
    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    mid = _id_matiere(client, auth_headers, "Français")
    client.post(f"/utilisateurs/{uid}/affectations", headers=auth_headers, json={"classe_id": classe["id"], "matiere_id": mid})

    h = _login(client, PROF["email"])
    assert len(client.get(f"/utilisateurs/{uid}/affectations", headers=h).json()) == 1
    assert client.get(f"/utilisateurs/{autre_uid}/affectations", headers=h).status_code == 403


def test_retirer_une_affectation(client, auth_headers, niveau_3e):
    uid = client.post("/utilisateurs", headers=auth_headers, json=PROF).json()["id"]
    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    mid = _id_matiere(client, auth_headers, "Français")
    aff = client.post(
        f"/utilisateurs/{uid}/affectations", headers=auth_headers,
        json={"classe_id": classe["id"], "matiere_id": mid},
    ).json()
    assert client.delete(f"/utilisateurs/{uid}/affectations/{aff['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/utilisateurs/{uid}/affectations", headers=auth_headers).json() == []
