"""Écran matières : CRUD + déclaration des coefficients par niveau/série."""


def _login(client, email, mdp="motdepasse123"):
    tok = client.post("/auth/login", data={"username": email, "password": mdp}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_admin_cree_une_matiere(client, auth_headers):
    res = client.post("/matieres", headers=auth_headers, json={"nom": "Éducation civique et morale"})
    assert res.status_code == 201
    assert res.json()["nom"] == "Éducation civique et morale"
    assert res.json()["note_directe"] is False


def test_nom_de_matiere_insensible_a_la_casse(client, auth_headers):
    client.post("/matieres", headers=auth_headers, json={"nom": "Dessin"})
    assert client.post("/matieres", headers=auth_headers, json={"nom": "DESSIN"}).status_code == 409


def test_enseignant_ne_peut_pas_creer_de_matiere(client, auth_headers):
    client.post(
        "/utilisateurs", headers=auth_headers,
        json={"nom": "P", "prenom": "Q", "email": "p@ecole.bj", "mot_de_passe": "motdepasse123", "roles": ["enseignant"]},
    )
    h = _login(client, "p@ecole.bj")
    assert client.post("/matieres", headers=h, json={"nom": "X"}).status_code == 403


def test_renommer_matiere(client, auth_headers):
    mid = client.post("/matieres", headers=auth_headers, json={"nom": "Musique"}).json()["id"]
    res = client.patch(f"/matieres/{mid}", headers=auth_headers, json={"nom": "Éducation musicale"})
    assert res.status_code == 200 and res.json()["nom"] == "Éducation musicale"


def test_supprimer_matiere_sans_notes(client, auth_headers):
    mid = client.post("/matieres", headers=auth_headers, json={"nom": "Temporaire"}).json()["id"]
    assert client.delete(f"/matieres/{mid}", headers=auth_headers).status_code == 204
    assert client.get(f"/matieres/{mid}", headers=auth_headers).status_code == 404


def test_declarer_coefficient_pour_un_niveau_college(client, auth_headers, niveau_3e):
    mid = client.post("/matieres", headers=auth_headers, json={"nom": "ECM"}).json()["id"]
    res = client.put(
        f"/matieres/{mid}/coefficients", headers=auth_headers,
        json={"niveau_id": niveau_3e.id, "coefficient": 2},
    )
    assert res.status_code == 200
    assert res.json()["coefficient"] == 2.0

    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    noms = {m["nom"]: m["coefficient"] for m in client.get(f"/classes/{classe['id']}/matieres", headers=auth_headers).json()}
    assert noms.get("ECM") == 2.0


def test_declarer_coefficient_est_un_upsert(client, auth_headers, niveau_3e):
    mid = client.post("/matieres", headers=auth_headers, json={"nom": "ECM"}).json()["id"]
    client.put(f"/matieres/{mid}/coefficients", headers=auth_headers, json={"niveau_id": niveau_3e.id, "coefficient": 2})
    client.put(f"/matieres/{mid}/coefficients", headers=auth_headers, json={"niveau_id": niveau_3e.id, "coefficient": 3})
    lignes = client.get(f"/matieres/{mid}/coefficients", headers=auth_headers).json()
    assert len(lignes) == 1 and lignes[0]["coefficient"] == 3.0


def test_coefficient_sans_niveau_ni_serie_refuse(client, auth_headers):
    mid = client.post("/matieres", headers=auth_headers, json={"nom": "ECM"}).json()["id"]
    assert client.put(f"/matieres/{mid}/coefficients", headers=auth_headers, json={"coefficient": 2}).status_code == 422


def test_serie_sur_un_niveau_college_refusee(client, auth_headers, niveau_3e, serie_d):
    mid = client.post("/matieres", headers=auth_headers, json={"nom": "ECM"}).json()["id"]
    res = client.put(
        f"/matieres/{mid}/coefficients", headers=auth_headers,
        json={"niveau_id": niveau_3e.id, "serie_id": serie_d.id, "coefficient": 2},
    )
    assert res.status_code == 422


def test_retirer_un_coefficient_retire_la_matiere_de_la_classe(client, auth_headers, niveau_3e):
    mid = client.post("/matieres", headers=auth_headers, json={"nom": "ECM"}).json()["id"]
    coef = client.put(
        f"/matieres/{mid}/coefficients", headers=auth_headers,
        json={"niveau_id": niveau_3e.id, "coefficient": 2},
    ).json()
    classe = client.post("/classes", headers=auth_headers, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()

    assert client.delete(f"/matieres/{mid}/coefficients/{coef['id']}", headers=auth_headers).status_code == 204
    noms = {m["nom"] for m in client.get(f"/classes/{classe['id']}/matieres", headers=auth_headers).json()}
    assert "ECM" not in noms
