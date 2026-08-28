# GestionEcole — Backend (FastAPI + PostgreSQL)

API du système de gestion scolaire. Périmètre actuel (V1 web) : profils
Administration et Enseignants. Les profils mobiles (parents / élèves) et la
synchronisation hors-ligne viendront plus tard.

## Prérequis

- Python 3.12+
- PostgreSQL 18 (service `postgresql-x64-18`), `psql` accessible

## Installation

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env   # puis adapter DATABASE_URL et SECRET_KEY
```

## Base de données

Le fichier `db/schema.sql` fait foi pour la structure. `db/seed.sql` charge les
données de référence (niveaux, séries, langues, école pilote, année courante).

```powershell
.\db\reset_db.ps1   # DROP + CREATE + schema + seed
```

## Lancer l'API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- Documentation interactive : http://localhost:8000/docs
- Santé : http://localhost:8000/health

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Structure

```
app/
  main.py          point d'entrée FastAPI
  config.py        configuration (.env)
  database.py      moteur + session SQLAlchemy
  models.py        modèles SQLAlchemy (tables utilisées par l'API)
  schemas.py       schémas Pydantic (entrées / sorties)
  core/
    security.py    hachage bcrypt + jetons JWT
    deps.py        session, utilisateur courant, contrôle de rôle
  routers/
    auth.py        /auth/login, /auth/me
    eleves.py      CRUD élèves (limité à l'école de l'utilisateur)
db/
  schema.sql       schéma PostgreSQL complet (référence)
  seed.sql         données de départ
  reset_db.ps1     recrée la base de zéro
```
