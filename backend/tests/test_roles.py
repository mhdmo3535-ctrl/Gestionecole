"""Rôles de l'administration et droits par domaine."""

import pytest


def _login(client, email, mdp="motdepasse123"):
    tok = client.post("/auth/login", data={"username": email, "password": mdp}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture
def compte(client, auth_headers):
    """Crée un compte avec les rôles donnés (par le directeur) et renvoie ses en-têtes."""
    n = {"i": 0}

    def creer(*roles):
        n["i"] += 1
        email = f"{'-'.join(roles)}{n['i']}@ecole.bj"
        res = client.post("/utilisateurs", headers=auth_headers, json={
            "nom": "Test", "prenom": roles[0].capitalize(), "email": email,
            "mot_de_passe": "motdepasse123", "roles": list(roles)})
        assert res.status_code == 201, res.text
        return _login(client, email)

    return creer


@pytest.fixture
def eleve(client, auth_headers):
    return client.post("/eleves", headers=auth_headers,
                       json={"matricule": "R-001", "nom": "Houngbo", "prenom": "Ella"}).json()


def _nouvelle_classe(client, h, niveau, nom="3e Z"):
    return client.post("/classes", headers=h, json={"nom": nom, "niveau_id": niveau.id})


# ---------- Comptes et rôles ----------

def test_role_inconnu_refuse(client, auth_headers):
    res = client.post("/utilisateurs", headers=auth_headers, json={
        "nom": "X", "prenom": "Y", "email": "x@ecole.bj", "mot_de_passe": "motdepasse123", "roles": ["admin"]})
    assert res.status_code == 422


def test_au_moins_un_role(client, auth_headers):
    res = client.post("/utilisateurs", headers=auth_headers, json={
        "nom": "X", "prenom": "Y", "email": "x@ecole.bj", "mot_de_passe": "motdepasse123", "roles": []})
    assert res.status_code == 422


def test_seul_le_directeur_cree_des_comptes(client, compte):
    for roles in (("censeur",), ("surveillant",), ("comptable",), ("secretaire",)):
        h = compte(*roles)
        res = client.post("/utilisateurs", headers=h, json={
            "nom": "X", "prenom": "Y", "email": f"n-{roles[0]}@ecole.bj",
            "mot_de_passe": "motdepasse123", "roles": ["enseignant"]})
        assert res.status_code == 403, roles


def test_le_censeur_ne_voit_que_les_enseignants(client, compte, admin):
    compte("enseignant")
    compte("comptable")
    h = compte("censeur")
    liste = client.get("/utilisateurs", headers=h).json()
    assert liste and all("enseignant" in u["roles"] for u in liste)
    # la fiche du directeur ou d'un autre membre de l'administration lui est cachée
    assert client.get(f"/utilisateurs/{admin.id}", headers=h).status_code == 404
    assert client.patch(f"/utilisateurs/{admin.id}", headers=h, json={"nom": "Pirate"}).status_code == 403


def test_le_directeur_voit_tout_le_personnel(client, compte, auth_headers):
    compte("enseignant")
    compte("comptable")
    roles = {r for u in client.get("/utilisateurs", headers=auth_headers).json() for r in u["roles"]}
    assert {"directeur", "enseignant", "comptable"} <= roles


def test_l_ecole_garde_toujours_un_directeur(client, auth_headers, admin):
    res = client.patch(f"/utilisateurs/{admin.id}", headers=auth_headers, json={"roles": ["censeur"]})
    assert res.status_code == 422
    # avec un second directeur, le premier peut changer de rôle
    client.post("/utilisateurs", headers=auth_headers, json={
        "nom": "D", "prenom": "Deux", "email": "d2@ecole.bj", "mot_de_passe": "motdepasse123",
        "roles": ["directeur"]})
    res = client.patch(f"/utilisateurs/{admin.id}", headers=auth_headers, json={"roles": ["directeur", "censeur"]})
    assert res.status_code == 200 and res.json()["roles"] == ["censeur", "directeur"]


def test_matrice_des_droits_exposee(client, auth_headers):
    droits = client.get("/auth/droits", headers=auth_headers).json()
    assert droits["notes"]["ecrire"] == []                       # personne ne modifie les notes
    assert "secretaire" in droits["encaissements"]["ecrire"]
    assert droits["personnel"]["ecrire"] == ["directeur"]


# ---------- Censeur : pédagogie ----------

def test_censeur_pedagogie_et_bulletins(client, compte, niveau_3e, eleve):
    h = compte("censeur")
    classe = _nouvelle_classe(client, h, niveau_3e)
    assert classe.status_code == 201
    t1 = client.get("/trimestres", headers=h).json()[0]["id"]
    assert client.get(f"/classes/{classe.json()['id']}/bulletins", headers=h,
                      params={"trimestre_id": t1}).status_code == 200
    assert client.get("/notes/historique", headers=h).status_code == 200
    # hors de son domaine
    assert client.get(f"/eleves/{eleve['id']}/infos-medicales", headers=h).status_code == 403
    assert client.get("/paiements/suivi", headers=h).status_code == 403
    assert client.post("/eleves", headers=h, json={"matricule": "X", "nom": "X", "prenom": "X"}).status_code == 403


def test_censeur_ne_saisit_pas_de_note(client, compte, auth_headers, niveau_3e, eleve):
    h = compte("censeur")
    classe = _nouvelle_classe(client, auth_headers, niveau_3e).json()
    client.patch(f"/eleves/{eleve['id']}", headers=auth_headers, json={"classe_id": classe["id"]})
    mid = next(m["matiere_id"] for m in client.get(f"/classes/{classe['id']}/matieres", headers=h).json()
               if not m["note_directe"])
    t1 = client.get("/trimestres", headers=h).json()[0]["id"]
    res = client.put("/notes", headers=h, json={
        "eleve_id": eleve["id"], "matiere_id": mid, "trimestre_id": t1, "interro1": 20})
    assert res.status_code == 403


# ---------- Surveillant général : vie scolaire ----------

def test_surveillant_vie_scolaire(client, compte, eleve):
    h = compte("surveillant")
    res = client.post(f"/eleves/{eleve['id']}/absences", headers=h, json={"date": "2026-01-12"})
    assert res.status_code == 201, res.text
    assert client.post(f"/eleves/{eleve['id']}/discipline", headers=h,
                       json={"date": "2026-01-12", "description": "Retards répétés"}).status_code == 201
    # consulte le médical (urgences) sans le modifier
    assert client.get(f"/eleves/{eleve['id']}/infos-medicales", headers=h).status_code == 200
    assert client.put(f"/eleves/{eleve['id']}/infos-medicales", headers=h,
                      json={"allergies": "Arachide"}).status_code == 403
    # pas d'accès aux finances ni aux bulletins
    assert client.get("/paiements/suivi", headers=h).status_code == 403
    assert client.get(f"/eleves/{eleve['id']}/paiements", headers=h).status_code == 403


def test_censeur_consulte_la_vie_scolaire_sans_la_modifier(client, compte, eleve):
    h = compte("censeur")
    assert client.get(f"/eleves/{eleve['id']}/absences", headers=h).status_code == 200
    assert client.post(f"/eleves/{eleve['id']}/absences", headers=h,
                       json={"date": "2026-01-12"}).status_code == 403


# ---------- Secrétaire et DAF : scolarité et finances ----------

def test_secretaire_inscrit_et_encaisse_mais_n_annule_pas(client, compte, annee_active):
    sec = compte("secretaire")
    daf = compte("comptable")

    eleve = client.post("/eleves", headers=sec, json={"matricule": "S-1", "nom": "Agossa", "prenom": "Noé"})
    assert eleve.status_code == 201
    eid = eleve.json()["id"]
    assert client.put(f"/eleves/{eid}/infos-medicales", headers=sec, json={"allergies": "Aucune"}).status_code == 200

    # les tranches sont fixées par le DAF, pas par la secrétaire
    assert client.post("/paiements/tranches", headers=sec, json={"montant": 50000}).status_code == 403
    tranche = client.post("/paiements/tranches", headers=daf, json={"montant": 50000})
    assert tranche.status_code == 201

    paiement = client.post(f"/eleves/{eid}/paiements", headers=sec,
                           json={"tranche_id": tranche.json()["id"], "montant_paye": 20000})
    assert paiement.status_code == 201, paiement.text
    pid = paiement.json()["id"]
    assert client.get(f"/paiements/{pid}/recu", headers=sec).status_code == 200
    assert client.get("/paiements/suivi", headers=sec).status_code == 200

    # seule la DAF (ou le directeur) annule un paiement
    assert client.delete(f"/eleves/{eid}/paiements/{pid}", headers=sec).status_code == 403
    assert client.delete(f"/eleves/{eid}/paiements/{pid}", headers=daf).status_code == 204


def test_daf_hors_pedagogie_et_vie_scolaire(client, compte, niveau_3e, eleve):
    h = compte("comptable")
    assert _nouvelle_classe(client, h, niveau_3e).status_code == 403
    assert client.get(f"/eleves/{eleve['id']}/absences", headers=h).status_code == 403
    assert client.get(f"/eleves/{eleve['id']}/infos-medicales", headers=h).status_code == 403
    assert client.get("/notes/historique", headers=h).status_code == 403


def test_secretaire_ne_gere_pas_la_pedagogie(client, compte, niveau_3e):
    h = compte("secretaire")
    assert _nouvelle_classe(client, h, niveau_3e).status_code == 403
    assert client.get("/classes", headers=h).status_code == 200


# ---------- Cumul de rôles ----------

def test_cumul_de_roles_additionne_les_droits(client, compte, eleve):
    h = compte("secretaire", "surveillant")
    assert client.post("/eleves", headers=h, json={"matricule": "C-1", "nom": "C", "prenom": "C"}).status_code == 201
    assert client.post(f"/eleves/{eleve['id']}/absences", headers=h, json={"date": "2026-01-12"}).status_code == 201
    # mais toujours pas les finances réservées au DAF
    assert client.post("/paiements/tranches", headers=h, json={"montant": 1000}).status_code == 403


def test_enseignant_n_a_aucun_droit_administratif(client, compte, eleve):
    h = compte("enseignant")
    assert client.post("/eleves", headers=h, json={"matricule": "E-1", "nom": "E", "prenom": "E"}).status_code == 403
    assert client.get(f"/eleves/{eleve['id']}/absences", headers=h).status_code == 403
    assert client.get("/paiements/suivi", headers=h).status_code == 403
    assert client.get("/utilisateurs", headers=h).status_code == 403
