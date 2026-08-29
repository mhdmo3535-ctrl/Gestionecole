# Schoolaris — Frontend (React + Ant Design)

Plateforme web (SaaS) pour l'administration et les enseignants.

## Stack

- React 19 + TypeScript + Vite
- Ant Design 6 (interface, locale `fr_FR`)
- TanStack Query (état serveur) + Axios
- React Router 7

## Démarrer

```bash
npm install
npm run dev          # http://localhost:5173
```

Le backend doit tourner sur `http://localhost:8000` (voir `../backend`).
Pour pointer ailleurs : créer un fichier `.env` avec `VITE_API_URL=...`.

Compte de test (après `../backend/db/reset_db.ps1` + `scripts.create_admin`) :
`admin@ecole.bj` / `motdepasse123`.

## Scripts

- `npm run dev` — serveur de développement
- `npm run build` — build de production (`tsc -b && vite build`)
- `npm run lint` — oxlint

## Organisation

```
src/
  api/
    client.ts      instance axios, jeton, gestion du 401
    endpoints.ts   toutes les fonctions d'appel à l'API
    types.ts       types partagés (miroir des schémas backend)
  auth/
    AuthContext.tsx   session (localStorage), connexion / déconnexion
    ProtectedRoute.tsx
  layout/AppLayout.tsx   coquille : menu latéral + en-tête
  pages/                 un fichier par écran
  routes.tsx             déclaration des routes
```

## État

- Connexion + session : fait
- Écran **Élèves** (liste, recherche, création, modification) : fait
- Classes, Matières, Enseignants, Saisie des notes, Bulletins : à construire
