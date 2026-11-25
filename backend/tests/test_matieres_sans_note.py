"""Matières sans note (ex : Travaux dirigés) : à l'emploi du temps, hors moyennes."""

import pytest


def _login(client, email, mdp="motdepasse123"):
    tok = client.post("/auth/login", data={"username": email, "password": mdp}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture
def td(client, auth_headers, niveau_3e):
    h = auth_headers
    matiere = client.post("/matieres", headers=h, json={"nom": "Travaux dirigés", "evaluee": False})
    assert matiere.status_code == 201, matiere.text
    classe = client.post("/classes", headers=h, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    prof = client.post("/utilisateurs", headers=h, json={
        "nom": "Prof", "prenom": "Koffi", "email": "koffi@ecole.bj", "mot_de_passe": "motdepasse123",
        "roles": ["enseignant"]}).json()
    client.post(f"/utilisateurs/{prof['id']}/affectations", headers=h,
                json={"classe_id": classe["id"], "matiere_id": matiere.json()["id"]})
    eleve = client.post("/eleves", headers=h, json={"matricule": "T1", "nom": "T", "prenom": "T",
                                                   "classe_id": classe["id"]}).json()
    return {"matiere": matiere.json(), "classe": classe, "prof": prof, "eleve": eleve}


def test_matiere_sans_note_creee(td):
    assert td["matiere"]["evaluee"] is False


def test_pas_de_coefficient(client, auth_headers, td, niveau_3e):
    res = client.put(f"/matieres/{td['matiere']['id']}/coefficients", headers=auth_headers,
                     json={"niveau_id": niveau_3e.id, "coefficient": 1})
    assert res.status_code == 422


def test_pas_de_note(client, td):
    t1 = client.get("/trimestres", headers=_login(client, "koffi@ecole.bj")).json()[0]["id"]
    res = client.put("/notes", headers=_login(client, "koffi@ecole.bj"), json={
        "eleve_id": td["eleve"]["id"], "matiere_id": td["matiere"]["id"], "trimestre_id": t1,
        "interro1": 12})
    assert res.status_code == 422
    assert "n'est pas notée" in res.json()["detail"]


def test_absente_des_matieres_de_la_classe(client, auth_headers, td):
    noms = {m["nom"] for m in client.get(f"/classes/{td['classe']['id']}/matieres", headers=auth_headers).json()}
    assert "Travaux dirigés" not in noms and "Mathématiques" in noms


def test_presente_a_l_emploi_du_temps(client, auth_headers, td):
    res = client.post("/emploi-du-temps", headers=auth_headers, json={
        "classe_id": td["classe"]["id"], "matiere_id": td["matiere"]["id"], "enseignant_id": td["prof"]["id"],
        "jour": 3, "heure_debut": "15:00", "heure_fin": "17:00"})
    assert res.status_code == 201, res.text
    assert res.json()["duree_minutes"] == 120


def test_basculer_une_matiere_en_sans_note_retire_ses_coefficients(client, auth_headers, niveau_3e):
    h = auth_headers
    m = client.post("/matieres", headers=h, json={"nom": "Étude"}).json()
    client.put(f"/matieres/{m['id']}/coefficients", headers=h, json={"niveau_id": niveau_3e.id, "coefficient": 1})
    assert len(client.get(f"/matieres/{m['id']}/coefficients", headers=h).json()) == 1
    res = client.patch(f"/matieres/{m['id']}", headers=h, json={"evaluee": False})
    assert res.status_code == 200 and res.json()["evaluee"] is False
    assert client.get(f"/matieres/{m['id']}/coefficients", headers=h).json() == []


def test_sans_note_et_note_directe_incompatibles(client, auth_headers):
    res = client.post("/matieres", headers=auth_headers,
                      json={"nom": "Bizarre", "evaluee": False, "note_directe": True})
    assert res.status_code == 422
