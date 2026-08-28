r"""Crée un compte administrateur.

Aucun compte n'existe au départ (sécurité). Ce script sert à créer le
tout premier admin ; ensuite, la création des comptes se fera depuis l'API.

Usage :
    .\.venv\Scripts\python.exe -m scripts.create_admin --email admin@ecole.bj --prenom Awa --nom Doe
Le mot de passe est demandé de façon masquée (ou via --password).
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import Ecole, Utilisateur


def main() -> int:
    parser = argparse.ArgumentParser(description="Créer un compte administrateur")
    parser.add_argument("--email", required=True)
    parser.add_argument("--prenom", required=True)
    parser.add_argument("--nom", required=True)
    parser.add_argument("--password", help="si omis, demandé en interactif")
    parser.add_argument("--ecole-id", type=int, help="par défaut : l'école pilote")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Mot de passe : ")
    if len(password) < 8:
        print("Le mot de passe doit faire au moins 8 caractères.", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        if args.ecole_id is not None:
            ecole = db.get(Ecole, args.ecole_id)
        else:
            ecole = db.scalar(select(Ecole).where(Ecole.est_pilote.is_(True)).order_by(Ecole.id))
        if ecole is None:
            print("Aucune école trouvée. Charge d'abord db/seed.sql.", file=sys.stderr)
            return 1

        if db.scalar(select(Utilisateur).where(Utilisateur.email == args.email)):
            print(f"Un utilisateur avec l'email {args.email} existe déjà.", file=sys.stderr)
            return 1

        user = Utilisateur(
            ecole_id=ecole.id,
            nom=args.nom,
            prenom=args.prenom,
            email=args.email,
            mot_de_passe_hash=hash_password(password),
            role="admin",
        )
        db.add(user)
        db.commit()
        print(f"Admin créé : {args.prenom} {args.nom} <{args.email}> (école {ecole.id} — {ecole.nom})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
