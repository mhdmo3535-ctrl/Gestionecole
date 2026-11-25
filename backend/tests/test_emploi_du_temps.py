"""Emploi du temps : affectations, conflits de classe et de professeur, droits."""

import pytest


def _login(client, email, mdp="motdepasse123"):
    tok = client.post("/auth/login", data={"username": email, "password": mdp}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _mid(client, h, nom):
    return next(m["id"] for m in client.get("/matieres", headers=h).json() if m["nom"] == nom)


@pytest.fixture
def etab(client, auth_headers, niveau_3e):
    """Deux classes de 3e, deux profs : Koffi (Maths en 3e A et 3e B), Awa (Français en 3e A)."""
    h = auth_headers
    a = client.post("/classes", headers=h, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    b = client.post("/classes", headers=h, json={"nom": "3e B", "niveau_id": niveau_3e.id}).json()
    profs = {}
    for prenom in ("Koffi", "Awa"):
        profs[prenom] = client.post("/utilisateurs", headers=h, json={
            "nom": "Prof", "prenom": prenom, "email": f"{prenom.lower()}@ecole.bj",
            "mot_de_passe": "motdepasse123", "roles": ["enseignant"]}).json()
    maths, francais = _mid(client, h, "Mathématiques"), _mid(client, h, "Français")
    for prof, classe, matiere in (("Koffi", a, maths), ("Koffi", b, maths), ("Awa", a, francais)):
        client.post(f"/utilisateurs/{profs[prof]['id']}/affectations", headers=h,
                    json={"classe_id": classe["id"], "matiere_id": matiere})
    return {"a": a, "b": b, "koffi": profs["Koffi"], "awa": profs["Awa"], "maths": maths, "francais": francais}


def _cours(client, h, classe, matiere, prof, jour=1, debut="07:30", fin="09:30"):
    return client.post("/emploi-du-temps", headers=h, json={
        "classe_id": classe["id"], "matiere_id": matiere, "enseignant_id": prof["id"],
        "jour": jour, "heure_debut": debut, "heure_fin": fin})


def test_ajouter_et_lire_un_cours(client, auth_headers, etab):
    e = etab
    res = _cours(client, auth_headers, e["a"], e["maths"], e["koffi"])
    assert res.status_code == 201, res.text
    c = res.json()
    assert c["duree_minutes"] == 120 and c["matiere_nom"] == "Mathématiques"
    assert c["enseignant_nom"] == "Koffi Prof"
    edt = client.get("/emploi-du-temps", headers=auth_headers, params={"classe_id": e["a"]["id"]}).json()
    assert [x["id"] for x in edt] == [c["id"]]


def test_professeur_non_affecte_refuse(client, auth_headers, etab):
    e = etab
    res = _cours(client, auth_headers, e["b"], e["francais"], e["awa"])   # Awa n'enseigne pas en 3e B
    assert res.status_code == 422
    assert "n'est pas affecté" in res.json()["detail"]


def test_conduite_n_est_pas_un_cours(client, auth_headers, etab):
    e = etab
    conduite = _mid(client, auth_headers, "Conduite")
    client.post(f"/utilisateurs/{e['koffi']['id']}/affectations", headers=auth_headers,
                json={"classe_id": e["a"]["id"], "matiere_id": conduite})
    assert _cours(client, auth_headers, e["a"], conduite, e["koffi"]).status_code == 422


def test_heure_de_fin_apres_le_debut(client, auth_headers, etab):
    e = etab
    assert _cours(client, auth_headers, e["a"], e["maths"], e["koffi"], debut="10:00", fin="09:00").status_code == 422


def test_une_classe_ne_peut_pas_avoir_deux_cours_en_meme_temps(client, auth_headers, etab):
    e = etab
    _cours(client, auth_headers, e["a"], e["maths"], e["koffi"], debut="07:30", fin="09:30")
    res = _cours(client, auth_headers, e["a"], e["francais"], e["awa"], debut="09:00", fin="10:00")
    assert res.status_code == 409
    assert "3e A a déjà Mathématiques le lundi de 7h30 à 9h30" in res.json()["detail"]


def test_un_professeur_ne_peut_pas_etre_dans_deux_classes(client, auth_headers, etab):
    e = etab
    _cours(client, auth_headers, e["a"], e["maths"], e["koffi"], debut="07:30", fin="09:30")
    res = _cours(client, auth_headers, e["b"], e["maths"], e["koffi"], debut="08:00", fin="09:00")
    assert res.status_code == 409
    assert "Koffi Prof a déjà cours en 3e A" in res.json()["detail"]


def test_cours_qui_se_suivent_sans_se_chevaucher(client, auth_headers, etab):
    e = etab
    _cours(client, auth_headers, e["a"], e["maths"], e["koffi"], debut="07:30", fin="09:30")
    assert _cours(client, auth_headers, e["b"], e["maths"], e["koffi"], debut="09:30", fin="11:30").status_code == 201
    assert _cours(client, auth_headers, e["a"], e["maths"], e["koffi"], jour=6, debut="07:30", fin="09:30").status_code == 201


def test_deplacer_un_cours_verifie_les_conflits(client, auth_headers, etab):
    e = etab
    c1 = _cours(client, auth_headers, e["a"], e["maths"], e["koffi"], debut="07:30", fin="09:30").json()
    _cours(client, auth_headers, e["a"], e["francais"], e["awa"], debut="10:00", fin="12:00")
    # déplacer sur lui-même : pas de conflit avec soi-même
    assert client.patch(f"/emploi-du-temps/{c1['id']}", headers=auth_headers,
                        json={"heure_fin": "09:00"}).status_code == 200
    # déplacer sur le cours de français : conflit
    assert client.patch(f"/emploi-du-temps/{c1['id']}", headers=auth_headers,
                        json={"heure_debut": "10:30", "heure_fin": "11:30"}).status_code == 409
    assert client.delete(f"/emploi-du-temps/{c1['id']}", headers=auth_headers).status_code == 204


def test_dimanche_refuse(client, auth_headers, etab):
    e = etab
    assert _cours(client, auth_headers, e["a"], e["maths"], e["koffi"], jour=7).status_code == 422


def test_affectations_de_la_classe(client, auth_headers, etab):
    e = etab
    aff = client.get(f"/classes/{e['a']['id']}/affectations", headers=auth_headers).json()
    assert {(a["enseignant_nom"], a["matiere_nom"]) for a in aff} == {
        ("Koffi Prof", "Mathématiques"), ("Awa Prof", "Français")}


def test_censeur_gere_l_emploi_du_temps(client, auth_headers, etab):
    e = etab
    client.post("/utilisateurs", headers=auth_headers, json={
        "nom": "C", "prenom": "C", "email": "censeur@ecole.bj", "mot_de_passe": "motdepasse123",
        "roles": ["censeur"]})
    h = _login(client, "censeur@ecole.bj")
    assert _cours(client, h, e["a"], e["maths"], e["koffi"]).status_code == 201


def test_enseignant_voit_son_emploi_du_temps_seulement(client, auth_headers, etab):
    e = etab
    _cours(client, auth_headers, e["a"], e["maths"], e["koffi"])
    h = _login(client, "koffi@ecole.bj")
    assert len(client.get("/emploi-du-temps", headers=h, params={"enseignant_id": e["koffi"]["id"]}).json()) == 1
    assert client.get("/emploi-du-temps", headers=h, params={"enseignant_id": e["awa"]["id"]}).status_code == 403
    assert client.get("/emploi-du-temps", headers=h, params={"classe_id": e["a"]["id"]}).status_code == 403
    assert _cours(client, h, e["a"], e["maths"], e["koffi"], jour=2).status_code == 403


def test_secretaire_consulte_sans_modifier(client, auth_headers, etab):
    e = etab
    client.post("/utilisateurs", headers=auth_headers, json={
        "nom": "S", "prenom": "S", "email": "sec@ecole.bj", "mot_de_passe": "motdepasse123",
        "roles": ["secretaire"]})
    h = _login(client, "sec@ecole.bj")
    assert client.get("/emploi-du-temps", headers=h, params={"classe_id": e["a"]["id"]}).status_code == 200
    assert _cours(client, h, e["a"], e["maths"], e["koffi"]).status_code == 403


def test_creer_l_affectation_avec_le_cours(client, auth_headers, etab):
    e = etab
    base = {"classe_id": e["b"]["id"], "matiere_id": e["francais"], "enseignant_id": e["awa"]["id"],
            "jour": 2, "heure_debut": "07:30", "heure_fin": "09:30"}
    # sans l'option : refusé (Awa n'enseigne pas en 3e B)
    assert client.post("/emploi-du-temps", headers=auth_headers, json=base).status_code == 422
    # avec l'option : le cours est créé et Awa est désormais affectée à la 3e B en Français
    res = client.post("/emploi-du-temps", headers=auth_headers, json={**base, "creer_affectation": True})
    assert res.status_code == 201, res.text
    aff = client.get(f"/classes/{e['b']['id']}/affectations", headers=auth_headers).json()
    assert ("Awa Prof", "Français") in {(a["enseignant_nom"], a["matiere_nom"]) for a in aff}


def test_pas_d_affectation_creee_si_le_cours_est_refuse(client, auth_headers, etab):
    e = etab
    _cours(client, auth_headers, e["b"], e["maths"], e["koffi"], jour=2, debut="07:30", fin="09:30")
    res = client.post("/emploi-du-temps", headers=auth_headers, json={
        "classe_id": e["b"]["id"], "matiere_id": e["francais"], "enseignant_id": e["awa"]["id"],
        "jour": 2, "heure_debut": "08:00", "heure_fin": "09:00", "creer_affectation": True})
    assert res.status_code == 409
    aff = client.get(f"/classes/{e['b']['id']}/affectations", headers=auth_headers).json()
    assert "Awa Prof" not in {a["enseignant_nom"] for a in aff}
