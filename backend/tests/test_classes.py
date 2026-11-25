"""Tests des classes et du référentiel (niveaux, séries, années scolaires)."""


# ---------- Référentiel ----------

def test_lister_niveaux(client, auth_headers):
    res = client.get("/niveaux", headers=auth_headers)
    assert res.status_code == 200
    noms = [n["nom"] for n in res.json()]
    assert noms == ["6e", "5e", "4e", "3e", "2nde", "1ere", "Tle"]


def test_lister_series(client, auth_headers):
    res = client.get("/series", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 13


def test_annee_active_presente_dans_le_seed(client, auth_headers):
    res = client.get("/annees-scolaires", headers=auth_headers)
    assert res.status_code == 200
    actives = [a for a in res.json() if a["active"]]
    assert len(actives) == 1
    assert actives[0]["libelle"] == "2025-2026"


def test_creer_annee_desactive_les_autres(client, auth_headers):
    res = client.post(
        "/annees-scolaires",
        headers=auth_headers,
        json={"libelle": "2026-2027", "date_debut": "2026-09-15", "date_fin": "2027-07-15"},
    )
    assert res.status_code == 201
    toutes = client.get("/annees-scolaires", headers=auth_headers).json()
    actives = [a["libelle"] for a in toutes if a["active"]]
    assert actives == ["2026-2027"]


def test_creer_annee_dates_incoherentes(client, auth_headers):
    res = client.post(
        "/annees-scolaires",
        headers=auth_headers,
        json={"libelle": "2027-2028", "date_debut": "2028-01-01", "date_fin": "2027-01-01"},
    )
    assert res.status_code == 422


# ---------- Classes ----------

def test_creer_classe_college(client, auth_headers, niveau_3e):
    res = client.post(
        "/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}
    )
    assert res.status_code == 201, res.text
    c = res.json()
    assert c["nom"] == "3e A"
    assert c["cycle"] == "college"
    assert c["serie_id"] is None
    assert c["annee_libelle"] == "2025-2026"   # année active par défaut
    assert c["effectif"] == 0


def test_creer_classe_lycee_avec_serie(client, auth_headers, niveau_tle, serie_d):
    res = client.post(
        "/classes",
        headers=auth_headers,
        json={"nom": "Tle D", "niveau_id": niveau_tle.id, "serie_id": serie_d.id},
    )
    assert res.status_code == 201
    assert res.json()["serie_nom"] == "D"


def test_college_refuse_une_serie(client, auth_headers, niveau_3e, serie_d):
    res = client.post(
        "/classes",
        headers=auth_headers,
        json={"nom": "3e D", "niveau_id": niveau_3e.id, "serie_id": serie_d.id},
    )
    assert res.status_code == 422


def test_nom_de_classe_en_double_meme_annee(client, auth_headers, niveau_3e):
    payload = {"nom": "3e B", "niveau_id": niveau_3e.id}
    assert client.post("/classes", headers=auth_headers, json=payload).status_code == 201
    assert client.post("/classes", headers=auth_headers, json=payload).status_code == 409


def test_enseignant_ne_peut_pas_creer_de_classe(client, admin, db, ecole, niveau_3e):
    from app.core.security import hash_password
    from app.models import Utilisateur

    prof = Utilisateur(
        ecole_id=ecole.id, nom="P", prenom="Q", email="p@test.local",
        mot_de_passe_hash=hash_password("motdepasse"), roles=["enseignant"],
    )
    db.add(prof)
    db.flush()
    token = client.post("/auth/login", data={"username": "p@test.local", "password": "motdepasse"}).json()["access_token"]
    res = client.post(
        "/classes",
        headers={"Authorization": f"Bearer {token}"},
        json={"nom": "3e C", "niveau_id": niveau_3e.id},
    )
    assert res.status_code == 403


def test_lister_et_filtrer_classes(client, auth_headers, niveau_3e, niveau_tle, serie_d):
    client.post("/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id})
    client.post("/classes", headers=auth_headers, json={"nom": "Tle D", "niveau_id": niveau_tle.id, "serie_id": serie_d.id})

    toutes = client.get("/classes", headers=auth_headers).json()
    assert {c["nom"] for c in toutes} == {"3e A", "Tle D"}

    filtre = client.get("/classes", headers=auth_headers, params={"niveau_id": niveau_3e.id}).json()
    assert [c["nom"] for c in filtre] == ["3e A"]


def test_affecter_eleve_a_une_classe_et_lister(client, auth_headers, niveau_3e):
    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    eleve = client.post(
        "/eleves", headers=auth_headers, json={"matricule": "M1", "nom": "Kossi", "prenom": "Ama"}
    ).json()

    maj = client.patch(f"/eleves/{eleve['id']}", headers=auth_headers, json={"classe_id": classe["id"]})
    assert maj.status_code == 200

    dans_la_classe = client.get(f"/classes/{classe['id']}/eleves", headers=auth_headers).json()
    assert [e["matricule"] for e in dans_la_classe] == ["M1"]
    assert client.get(f"/classes/{classe['id']}", headers=auth_headers).json()["effectif"] == 1


def test_supprimer_classe_vide_ok_mais_pas_si_elle_a_des_eleves(client, auth_headers, niveau_3e):
    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e Z", "niveau_id": niveau_3e.id}).json()
    cid = classe["id"]

    eleve = client.post(
        "/eleves", headers=auth_headers, json={"matricule": "M2", "nom": "X", "prenom": "Y", "classe_id": cid}
    ).json()
    assert client.delete(f"/classes/{cid}", headers=auth_headers).status_code == 409

    client.patch(f"/eleves/{eleve['id']}", headers=auth_headers, json={"classe_id": None})
    assert client.delete(f"/classes/{cid}", headers=auth_headers).status_code == 204
    assert client.get(f"/classes/{cid}", headers=auth_headers).status_code == 404


def test_renommer_classe(client, auth_headers, niveau_3e):
    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    res = client.patch(f"/classes/{classe['id']}", headers=auth_headers, json={"nom": "3e A bis"})
    assert res.status_code == 200
    assert res.json()["nom"] == "3e A bis"


def test_acces_sans_jeton_refuse(client):
    assert client.get("/classes").status_code == 401
    assert client.get("/niveaux").status_code == 401


# ---------- Professeur principal ----------

def _creer_utilisateur(client, auth_headers, email, role="enseignant"):
    return client.post("/utilisateurs", headers=auth_headers, json={
        "nom": "Dossou", "prenom": "Mireille", "email": email,
        "mot_de_passe": "motdepasse123", "roles": [role]}).json()


def test_designer_un_professeur_principal(client, auth_headers, niveau_3e):
    prof = _creer_utilisateur(client, auth_headers, "pp@ecole.bj")
    classe = client.post("/classes", headers=auth_headers, json={
        "nom": "3e B", "niveau_id": niveau_3e.id, "professeur_principal_id": prof["id"]}).json()
    assert classe["professeur_principal_id"] == prof["id"]
    assert classe["professeur_principal_nom"] == "Mireille Dossou"

    retire = client.patch(f"/classes/{classe['id']}", headers=auth_headers,
                          json={"professeur_principal_id": None}).json()
    assert retire["professeur_principal_id"] is None and retire["professeur_principal_nom"] is None


def test_professeur_principal_doit_etre_un_enseignant(client, auth_headers, niveau_3e):
    autre_admin = _creer_utilisateur(client, auth_headers, "censeur@ecole.bj", role="censeur")
    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e C", "niveau_id": niveau_3e.id}).json()
    res = client.patch(f"/classes/{classe['id']}", headers=auth_headers,
                       json={"professeur_principal_id": autre_admin["id"]})
    assert res.status_code == 422
