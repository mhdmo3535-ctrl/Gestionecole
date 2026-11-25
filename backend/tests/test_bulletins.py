"""Bulletins : moyennes, rang, décision (calcul à la volée)."""

import pytest


def _login(client, email, mdp="motdepasse123"):
    tok = client.post("/auth/login", data={"username": email, "password": mdp}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _saisir_tout(client, headers, db, classe_id, eleve_id, trimestre_id, valeur):
    """Met la même valeur partout : la moyenne générale vaut alors exactement `valeur`.

    Les notes sont écrites directement en base : l'administration n'a pas le
    droit de les saisir via l'API (seuls les enseignants le peuvent).
    """
    from app.models import Note

    for m in client.get(f"/classes/{classe_id}/matieres", headers=headers).json():
        if m["note_directe"]:
            champs = {"note_directe": valeur}
        else:
            champs = {c: valeur for c in ("interro1", "interro2", "interro3", "devoir1", "devoir2")}
        db.add(Note(eleve_id=eleve_id, matiere_id=m["matiere_id"], trimestre_id=trimestre_id, **champs))
    db.flush()


@pytest.fixture
def classe_tle_d(client, auth_headers, niveau_tle, serie_d):
    classe = client.post(
        "/classes", headers=auth_headers,
        json={"nom": "Tle D", "niveau_id": niveau_tle.id, "serie_id": serie_d.id},
    ).json()
    a = client.post("/eleves", headers=auth_headers, json={
        "matricule": "A1", "nom": "Alpha", "prenom": "A", "classe_id": classe["id"]}).json()
    b = client.post("/eleves", headers=auth_headers, json={
        "matricule": "B1", "nom": "Beta", "prenom": "B", "classe_id": classe["id"]}).json()
    trimestres = {t["numero"]: t["id"] for t in client.get("/trimestres", headers=auth_headers).json()}
    return {"classe_id": classe["id"], "a": a["id"], "b": b["id"], "trimestres": trimestres}


def test_bulletin_classe_moyennes_et_rang(client, auth_headers, db, classe_tle_d):
    s = classe_tle_d
    t1 = s["trimestres"][1]
    _saisir_tout(client, auth_headers, db, s["classe_id"], s["a"], t1, 14)
    _saisir_tout(client, auth_headers, db, s["classe_id"], s["b"], t1, 11)

    res = client.get(f"/classes/{s['classe_id']}/bulletins", headers=auth_headers, params={"trimestre_id": t1})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["effectif_classe"] == 2
    par_eleve = {e["eleve_id"]: e for e in data["eleves"]}
    assert par_eleve[s["a"]]["moyenne_generale"] == 14.0
    assert par_eleve[s["a"]]["moyenne_generale_affichee"] == "14,00"
    assert par_eleve[s["a"]]["rang"] == 1
    assert par_eleve[s["b"]]["rang"] == 2
    # année incomplète -> pas de décision
    assert par_eleve[s["a"]]["decision"] is None


def test_bulletin_eleve_detail_par_matiere(client, auth_headers, db, classe_tle_d):
    s = classe_tle_d
    t1 = s["trimestres"][1]
    _saisir_tout(client, auth_headers, db, s["classe_id"], s["a"], t1, 14)
    _saisir_tout(client, auth_headers, db, s["classe_id"], s["b"], t1, 11)

    b = client.get(f"/eleves/{s['a']}/bulletin", headers=auth_headers, params={"trimestre_id": t1}).json()
    assert b["moyenne_generale"] == 14.0
    assert b["rang"] == 1 and b["effectif_classe"] == 2

    lignes = {ligne["matiere_nom"]: ligne for ligne in b["lignes"]}
    maths = lignes["Mathématiques"]
    assert maths["coefficient"] == 4.0
    assert maths["moyenne"] == 14.0
    assert maths["moyenne_coefficientee"] == 56.0     # 14 x 4
    assert maths["rang"] == 1
    conduite = lignes["Conduite"]
    assert conduite["note_directe"] is True and conduite["statut"] == "directe"


def test_decision_apparait_quand_les_trois_trimestres_sont_complets(client, auth_headers, db, classe_tle_d):
    s = classe_tle_d
    for numero in (1, 2, 3):
        _saisir_tout(client, auth_headers, db, s["classe_id"], s["a"], s["trimestres"][numero], 14)
        _saisir_tout(client, auth_headers, db, s["classe_id"], s["b"], s["trimestres"][numero], 8)

    t3 = s["trimestres"][3]
    ba = client.get(f"/eleves/{s['a']}/bulletin", headers=auth_headers, params={"trimestre_id": t3}).json()
    bb = client.get(f"/eleves/{s['b']}/bulletin", headers=auth_headers, params={"trimestre_id": t3}).json()
    assert ba["moyenne_annuelle"] == 14.0 and ba["decision"] == "admis"
    assert bb["moyenne_annuelle"] == 8.0 and bb["decision"] == "redouble"


def test_bulletins_reserves_a_l_administration(client, auth_headers, classe_tle_d):
    s = classe_tle_d
    client.post("/utilisateurs", headers=auth_headers, json={
        "nom": "P", "prenom": "Q", "email": "prof@ecole.bj", "mot_de_passe": "motdepasse123", "roles": ["enseignant"]})
    h = _login(client, "prof@ecole.bj")
    t1 = s["trimestres"][1]
    assert client.get(f"/classes/{s['classe_id']}/bulletins", headers=h, params={"trimestre_id": t1}).status_code == 403
    assert client.get(f"/eleves/{s['a']}/bulletin", headers=h, params={"trimestre_id": t1}).status_code == 403


def test_eleve_sans_classe_pas_de_bulletin(client, auth_headers, classe_tle_d):
    s = classe_tle_d
    orphelin = client.post("/eleves", headers=auth_headers, json={
        "matricule": "ORPH", "nom": "Sans", "prenom": "Classe"}).json()
    res = client.get(f"/eleves/{orphelin['id']}/bulletin", headers=auth_headers,
                     params={"trimestre_id": s["trimestres"][1]})
    assert res.status_code == 422


def test_matiere_sans_note_est_exclue_de_la_moyenne(client, auth_headers, db, classe_tle_d):
    """Une matière sans note ne compte ni au numérateur ni au dénominateur."""
    s = classe_tle_d
    t1 = s["trimestres"][1]
    matieres = client.get(f"/classes/{s['classe_id']}/matieres", headers=auth_headers).json()
    # on ne note que Mathématiques (coef 4) à 12
    maths = next(m["matiere_id"] for m in matieres if m["nom"] == "Mathématiques")
    from app.models import Note
    db.add(Note(eleve_id=s["a"], matiere_id=maths, trimestre_id=t1,
                interro1=12, interro2=12, interro3=12, devoir1=12, devoir2=12))
    db.flush()

    b = client.get(f"/eleves/{s['a']}/bulletin", headers=auth_headers, params={"trimestre_id": t1}).json()
    assert b["moyenne_generale"] == 12.0     # seule Maths compte
    lignes = {ligne["matiere_nom"]: ligne["statut"] for ligne in b["lignes"]}
    assert lignes["Mathématiques"] == "calculee"
    assert lignes["SVT"] == "sans_note"
