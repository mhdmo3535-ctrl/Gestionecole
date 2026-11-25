"""Autorisations d'absence : liste de toute l'école, traitement par le surveillant."""

import pytest


def _login(client, email, mdp="motdepasse123"):
    tok = client.post("/auth/login", data={"username": email, "password": mdp}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _compte(client, auth_headers, email, role):
    client.post("/utilisateurs", headers=auth_headers, json={
        "nom": "T", "prenom": "T", "email": email, "mot_de_passe": "motdepasse123", "roles": [role]})
    return _login(client, email)


@pytest.fixture
def demandes(client, auth_headers, niveau_3e):
    h = auth_headers
    classe = client.post("/classes", headers=h, json={"nom": "3e A", "niveau_id": niveau_3e.id}).json()
    a = client.post("/eleves", headers=h, json={"matricule": "A1", "nom": "Ahouansou", "prenom": "Léa",
                                               "classe_id": classe["id"]}).json()
    b = client.post("/eleves", headers=h, json={"matricule": "B1", "nom": "Bio", "prenom": "Sam"}).json()

    def demande(eleve, debut, fin, motif):
        return client.post(f"/eleves/{eleve['id']}/permissions", headers=h,
                           json={"date_debut": debut, "date_fin": fin, "motif": motif}).json()

    p1 = demande(a, "2026-02-10", "2026-02-10", "Rendez-vous médical")
    p2 = demande(b, "2026-02-03", "2026-02-04", "Décès dans la famille")
    p3 = demande(a, "2026-01-20", "2026-01-20", "Compétition sportive")
    client.patch(f"/eleves/{a['id']}/permissions/{p3['id']}", headers=h, json={"statut": "approuve"})
    return {"a": a, "b": b, "p1": p1, "p2": p2, "p3": p3}


def test_liste_de_l_ecole_en_attente_d_abord(client, auth_headers, demandes):
    d = demandes
    liste = client.get("/autorisations-absence", headers=auth_headers).json()
    # en attente : la plus ancienne date d'absence d'abord ; puis les traitées
    assert [l["id"] for l in liste] == [d["p2"]["id"], d["p1"]["id"], d["p3"]["id"]]
    p1 = next(l for l in liste if l["id"] == d["p1"]["id"])
    assert p1["eleve_nom"] == "Ahouansou Léa" and p1["classe_nom"] == "3e A"
    assert next(l for l in liste if l["id"] == d["p2"]["id"])["classe_nom"] is None
    p3 = next(l for l in liste if l["id"] == d["p3"]["id"])
    assert p3["statut"] == "approuve" and p3["traite_par_nom"] == "Test Admin"


def test_filtre_par_statut(client, auth_headers, demandes):
    attente = client.get("/autorisations-absence", headers=auth_headers, params={"statut": "en_attente"}).json()
    assert {l["statut"] for l in attente} == {"en_attente"} and len(attente) == 2
    assert client.get("/autorisations-absence", headers=auth_headers, params={"statut": "x"}).status_code == 422


def test_le_surveillant_traite_les_demandes(client, auth_headers, demandes):
    d = demandes
    h = _compte(client, auth_headers, "surv@ecole.bj", "surveillant")
    res = client.patch(f"/eleves/{d['a']['id']}/permissions/{d['p1']['id']}", headers=h,
                       json={"statut": "rejete", "commentaire_traitement": "Justificatif manquant"})
    assert res.status_code == 200 and res.json()["statut"] == "rejete"


def test_le_censeur_consulte_sans_traiter(client, auth_headers, demandes):
    d = demandes
    h = _compte(client, auth_headers, "cens@ecole.bj", "censeur")
    assert client.get("/autorisations-absence", headers=h).status_code == 200
    assert client.patch(f"/eleves/{d['a']['id']}/permissions/{d['p1']['id']}", headers=h,
                        json={"statut": "approuve"}).status_code == 403


def test_la_daf_n_y_a_pas_acces(client, auth_headers, demandes):
    h = _compte(client, auth_headers, "daf@ecole.bj", "comptable")
    assert client.get("/autorisations-absence", headers=h).status_code == 403


def test_alerte_du_tableau_de_bord_pour_qui_decide(client, auth_headers, demandes):
    surv = _compte(client, auth_headers, "surv2@ecole.bj", "surveillant")
    cens = _compte(client, auth_headers, "cens2@ecole.bj", "censeur")
    alerte = next(a for a in client.get("/tableau-de-bord", headers=surv).json()["alertes"]
                  if a["code"] == "permissions")
    assert alerte["nombre"] == 2 and alerte["lien"] == "/autorisations"
    assert "permissions" not in {a["code"] for a in client.get("/tableau-de-bord", headers=cens).json()["alertes"]}
