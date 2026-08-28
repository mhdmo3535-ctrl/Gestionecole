-- =====================================================================
-- GestionEcole — schéma PostgreSQL (base centrale, backend FastAPI)
-- Portée de ce fichier : modules nécessaires à la version WEB
-- (profils Administration + Enseignants). Parents/Élèves (mobile)
-- réutiliseront les mêmes tables plus tard, rien à refaire ici.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Décisions de conception — TOUTES VALIDÉES le 2026-08-28 :
--
-- 1. MULTI-ÉCOLE DÈS LE DÉPART.
--    Le projet prévoit plusieurs écoles pilotes puis des
--    écoles payantes, avec coefficients / mode de calcul / tranches de
--    paiement CONFIGURABLES PAR ÉCOLE. Donc toutes les tables
--    métier sont rattachées à une "ecole_id", même si en V1 une seule
--    école pilote utilise le système. Revenir à un modèle mono-école
--    plus tard serait un chantier de migration important — autant
--    payer ce coût une fois, maintenant, pendant que la base est vide.
--
-- 2. NOTES : table "large" (interro1..devoir2) plutôt que "évaluation +
--    note" ligne par ligne. La note de rattrapage est
--    "saisie comme une évaluation normale, à une date différente" — la
--    date de la session de rattrapage n'a donc pas besoin d'être tracée
--    au niveau base de données, seule la valeur finale compte. Plus
--    simple à requêter pour calculer les moyennes. Si un jour vous
--    voulez un nombre variable d'évaluations par matière, il faudra
--    remodeler vers une table "evaluations" — à garder en tête.
--
-- 3. LV1/LV2 : les séries A1/A2/B ont des lignes
--    "LV1"/"LV2" à coefficient configurable par élève, alors que les
--    séries scientifiques/techniques (C, D, E, F*, G*, Eau) ont une
--    ligne "Anglais" fixe. Modélisé ici comme une matière normale avec
--    un flag est_choix_langue : quand il est vrai, la "matière" réelle
--    de l'élève est déterminée par la table eleve_choix_langue plutôt
--    que d'être fixe. CONFIRMÉ : la série B n'a bien qu'une seule langue
--    vivante (LV1), pas de LV2 — ce n'est pas un oubli.
--
-- 4. INFOS MÉDICALES séparées dans leur propre table pour pouvoir
--    restreindre l'accès à l'API (réservé à l'administration)
--    sans risquer de les renvoyer accidentellement avec la fiche élève.
--
-- 5. Pas de table "bulletins" persistée en V1 : moyennes/décisions sont
--    calculées à la volée par le backend à partir des notes + coeffs.
--    On pourra ajouter un cache "bulletins_generes" plus tard si les
--    calculs deviennent coûteux ou s'il faut figer un bulletin signé.
-- ---------------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS pgcrypto; -- pour gen_random_uuid() si besoin plus tard

-- petite fonction utilitaire pour maintenir updated_at automatiquement
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 1. ÉCOLES & ANNÉES SCOLAIRES
-- =====================================================================

CREATE TABLE ecoles (
    id                          BIGSERIAL PRIMARY KEY,
    nom                         VARCHAR(150) NOT NULL,
    sigle                       VARCHAR(20),
    adresse                     VARCHAR(255),
    telephone                   VARCHAR(30),
    email                       VARCHAR(150),
    mode_calcul_moyenne_annuelle VARCHAR(20) NOT NULL DEFAULT 'poids_egal'
        CHECK (mode_calcul_moyenne_annuelle IN ('poids_egal', 't3_renforce')),
        -- poids_egal    : (T1 + T2 + T3) / 3
        -- t3_renforce   : (T1 + T2 + 2*T3) / 4
    est_pilote                  BOOLEAN NOT NULL DEFAULT false,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE annees_scolaires (
    id          BIGSERIAL PRIMARY KEY,
    ecole_id    BIGINT NOT NULL REFERENCES ecoles(id) ON DELETE CASCADE,
    libelle     VARCHAR(20) NOT NULL,      -- ex: '2025-2026'
    date_debut  DATE NOT NULL,
    date_fin    DATE NOT NULL,
    active      BOOLEAN NOT NULL DEFAULT true,
    UNIQUE (ecole_id, libelle)
);

CREATE TABLE trimestres (
    id                  BIGSERIAL PRIMARY KEY,
    annee_scolaire_id   BIGINT NOT NULL REFERENCES annees_scolaires(id) ON DELETE CASCADE,
    numero              SMALLINT NOT NULL CHECK (numero IN (1, 2, 3)),
    date_debut          DATE,
    date_fin            DATE,
    UNIQUE (annee_scolaire_id, numero)
);

-- =====================================================================
-- 2. UTILISATEURS & RÔLES
-- =====================================================================

CREATE TABLE utilisateurs (
    id              BIGSERIAL PRIMARY KEY,
    ecole_id        BIGINT NOT NULL REFERENCES ecoles(id) ON DELETE CASCADE,
    nom             VARCHAR(100) NOT NULL,
    prenom          VARCHAR(100) NOT NULL,
    email           VARCHAR(150) NOT NULL,
    mot_de_passe_hash VARCHAR(255) NOT NULL,
    -- rôle unique "admin" sans sous-niveaux, conforme
    -- (parent/eleve sont inclus ici aussi car le compte peut être créé
    -- côté web par l'admin même si la connexion se fait sur mobile)
    role            VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'enseignant', 'parent', 'eleve')),
    telephone       VARCHAR(30),
    actif           BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (ecole_id, email)
);

-- (la table enseignant_affectations est créée plus bas, section 3bis :
-- elle référence classes et matieres qui n'existent pas encore ici)

-- =====================================================================
-- 3. NIVEAUX, SÉRIES, CLASSES, MATIÈRES, COEFFICIENTS
-- =====================================================================

CREATE TABLE niveaux (
    id      BIGSERIAL PRIMARY KEY,
    nom     VARCHAR(20) NOT NULL UNIQUE,          -- '6e','5e','4e','3e','2nde','1ere','Tle'
    cycle   VARCHAR(10) NOT NULL CHECK (cycle IN ('college', 'lycee'))
);

CREATE TABLE series (
    id      BIGSERIAL PRIMARY KEY,
    nom     VARCHAR(30) NOT NULL UNIQUE            -- 'A1','A2','B','C','D','E','F2','F3','F4','G1','G2','G3','Eau et assainissement'
);

CREATE TABLE classes (
    id                  BIGSERIAL PRIMARY KEY,
    ecole_id            BIGINT NOT NULL REFERENCES ecoles(id) ON DELETE CASCADE,
    annee_scolaire_id   BIGINT NOT NULL REFERENCES annees_scolaires(id) ON DELETE CASCADE,
    niveau_id           BIGINT NOT NULL REFERENCES niveaux(id),
    serie_id            BIGINT REFERENCES series(id),   -- NULL pour le collège (6e-3e)
    nom                 VARCHAR(50) NOT NULL,            -- ex: '3e A', 'Terminale C'
    UNIQUE (ecole_id, annee_scolaire_id, nom)
);

CREATE TABLE matieres (
    id                  BIGSERIAL PRIMARY KEY,
    ecole_id            BIGINT NOT NULL REFERENCES ecoles(id) ON DELETE CASCADE,
    nom                 VARCHAR(100) NOT NULL,           -- 'Mathématiques', 'LV1', 'Anglais', ...
    code                VARCHAR(20),
    est_choix_langue    BOOLEAN NOT NULL DEFAULT false,   -- true pour les lignes LV1/LV2
    UNIQUE (ecole_id, nom)
);

CREATE TABLE langues (
    id      BIGSERIAL PRIMARY KEY,
    nom     VARCHAR(30) NOT NULL UNIQUE   -- Anglais, Allemand, Espagnol
);

-- (eleve_choix_langue est créée plus bas, section 4bis : elle référence
-- eleves qui n'existe pas encore ici)

-- Coefficient d'une matière, configurable par école (tous les
-- tableaux de coefficients, non codés en dur). Deux cas d'usage, jamais
-- les deux à la fois en V1 :
--   * collège : niveau_id renseigné, serie_id NULL
--   * lycée   : serie_id renseigné, niveau_id NULL
--               (les coefficients officiels sont donnés par série,
--                identiques en 2nde / 1ere / Tle)
-- Une matière sans ligne ici prend la valeur de coefficients_defaut.
CREATE TABLE coefficients (
    id          BIGSERIAL PRIMARY KEY,
    ecole_id    BIGINT NOT NULL REFERENCES ecoles(id) ON DELETE CASCADE,
    niveau_id   BIGINT REFERENCES niveaux(id),
    serie_id    BIGINT REFERENCES series(id),
    matiere_id  BIGINT NOT NULL REFERENCES matieres(id) ON DELETE CASCADE,
    coefficient NUMERIC(3,1) NOT NULL DEFAULT 1 CHECK (coefficient > 0),
    CONSTRAINT coefficients_cle UNIQUE NULLS NOT DISTINCT (ecole_id, niveau_id, serie_id, matiere_id),
    CONSTRAINT coefficients_niveau_ou_serie CHECK (niveau_id IS NOT NULL OR serie_id IS NOT NULL)
);

-- Coefficient par défaut appliqué à toute matière d'un niveau / d'une
-- série qui n'a pas de ligne explicite dans "coefficients".
-- Collège 6e-5e : 1 (uniforme). Collège 4e-3e : 2. Lycée : 1 par
-- défaut (valeur de repli, chaque série a normalement ses coefficients
-- explicites).
CREATE TABLE coefficients_defaut (
    id          BIGSERIAL PRIMARY KEY,
    ecole_id    BIGINT NOT NULL REFERENCES ecoles(id) ON DELETE CASCADE,
    niveau_id   BIGINT REFERENCES niveaux(id),
    serie_id    BIGINT REFERENCES series(id),
    coefficient NUMERIC(3,1) NOT NULL DEFAULT 1 CHECK (coefficient > 0),
    CONSTRAINT coefficients_defaut_cle UNIQUE NULLS NOT DISTINCT (ecole_id, niveau_id, serie_id),
    CONSTRAINT coefficients_defaut_niveau_ou_serie CHECK (niveau_id IS NOT NULL OR serie_id IS NOT NULL)
);

-- 3bis. Classes/matières qu'un enseignant est autorisé à saisir (accès
-- limité à ses propres classes et matières) — placée ici car elle
-- a besoin de classes et matieres, déjà créées juste au-dessus.
CREATE TABLE enseignant_affectations (
    id              BIGSERIAL PRIMARY KEY,
    enseignant_id   BIGINT NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    classe_id       BIGINT NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    matiere_id      BIGINT NOT NULL REFERENCES matieres(id) ON DELETE CASCADE,
    UNIQUE (enseignant_id, classe_id, matiere_id)
);

-- =====================================================================
-- 4. ÉLÈVES
-- =====================================================================

CREATE TABLE eleves (
    id              BIGSERIAL PRIMARY KEY,
    ecole_id        BIGINT NOT NULL REFERENCES ecoles(id) ON DELETE CASCADE,
    matricule       VARCHAR(30) NOT NULL,
    nom             VARCHAR(100) NOT NULL,
    prenom          VARCHAR(100) NOT NULL,
    date_naissance  DATE,
    sexe            VARCHAR(1) CHECK (sexe IN ('M', 'F')),
    classe_id       BIGINT REFERENCES classes(id),
    statut          VARCHAR(20) NOT NULL DEFAULT 'actif'
        CHECK (statut IN ('actif', 'archive', 'redoublant')),
    photo_url       VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (ecole_id, matricule)
);

CREATE TRIGGER trg_eleves_updated_at
    BEFORE UPDATE ON eleves
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Historique des classes fréquentées, pour l'historique scolaire
CREATE TABLE eleves_historique_classes (
    id              BIGSERIAL PRIMARY KEY,
    eleve_id        BIGINT NOT NULL REFERENCES eleves(id) ON DELETE CASCADE,
    classe_id       BIGINT NOT NULL REFERENCES classes(id),
    annee_scolaire_id BIGINT NOT NULL REFERENCES annees_scolaires(id),
    decision_fin_annee VARCHAR(20) CHECK (decision_fin_annee IN ('admis', 'redouble', NULL))
);

-- Infos médicales isolées : accès strictement réservé à l'administration
CREATE TABLE eleve_infos_medicales (
    eleve_id        BIGINT PRIMARY KEY REFERENCES eleves(id) ON DELETE CASCADE,
    groupe_sanguin  VARCHAR(5),
    allergies       TEXT,
    contacts_urgence TEXT,
    remarques       TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_par     BIGINT REFERENCES utilisateurs(id)
);

CREATE TRIGGER trg_infos_medicales_updated_at
    BEFORE UPDATE ON eleve_infos_medicales
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Parents / tuteurs et leur lien avec un ou plusieurs élèves
CREATE TABLE parents (
    id              BIGSERIAL PRIMARY KEY,
    ecole_id        BIGINT NOT NULL REFERENCES ecoles(id) ON DELETE CASCADE,
    utilisateur_id  BIGINT REFERENCES utilisateurs(id),  -- compte de connexion (mobile), nullable tant que non activé
    nom             VARCHAR(100) NOT NULL,
    prenom          VARCHAR(100) NOT NULL,
    telephone       VARCHAR(30),
    email           VARCHAR(150)
);

CREATE TABLE eleve_parents (
    eleve_id    BIGINT NOT NULL REFERENCES eleves(id) ON DELETE CASCADE,
    parent_id   BIGINT NOT NULL REFERENCES parents(id) ON DELETE CASCADE,
    lien        VARCHAR(20) CHECK (lien IN ('pere', 'mere', 'tuteur')),
    PRIMARY KEY (eleve_id, parent_id)
);

-- 4bis. Choix de langue par élève pour chaque emplacement LV1/LV2 de sa
-- série — placée ici car elle a besoin de eleves, créée juste au-dessus
-- (et de matieres/langues, déjà créées en section 3).
CREATE TABLE eleve_choix_langue (
    id          BIGSERIAL PRIMARY KEY,
    eleve_id    BIGINT NOT NULL REFERENCES eleves(id) ON DELETE CASCADE,
    matiere_id  BIGINT NOT NULL REFERENCES matieres(id) ON DELETE CASCADE, -- doit avoir est_choix_langue = true
    langue_id   BIGINT NOT NULL REFERENCES langues(id),
    UNIQUE (eleve_id, matiere_id)
);

-- =====================================================================
-- 5. NOTES
-- =====================================================================

CREATE TABLE notes (
    id              BIGSERIAL PRIMARY KEY,
    eleve_id        BIGINT NOT NULL REFERENCES eleves(id) ON DELETE CASCADE,
    matiere_id      BIGINT NOT NULL REFERENCES matieres(id) ON DELETE CASCADE,
    trimestre_id    BIGINT NOT NULL REFERENCES trimestres(id) ON DELETE CASCADE,
    interro1        NUMERIC(4,2) CHECK (interro1 BETWEEN 0 AND 20),
    interro2        NUMERIC(4,2) CHECK (interro2 BETWEEN 0 AND 20),
    interro3        NUMERIC(4,2) CHECK (interro3 BETWEEN 0 AND 20),
    devoir1         NUMERIC(4,2) CHECK (devoir1 BETWEEN 0 AND 20),
    devoir2         NUMERIC(4,2) CHECK (devoir2 BETWEEN 0 AND 20),
    saisi_par       BIGINT REFERENCES utilisateurs(id),      -- enseignant
    valide          BOOLEAN NOT NULL DEFAULT false,           -- validation admin
    valide_par      BIGINT REFERENCES utilisateurs(id),
    valide_le       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (eleve_id, matiere_id, trimestre_id)
);

CREATE TRIGGER trg_notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_notes_eleve ON notes(eleve_id);
CREATE INDEX idx_notes_trimestre ON notes(trimestre_id);

-- =====================================================================
-- 6. PRÉSENCES & PERMISSIONS D'ABSENCE
-- =====================================================================

CREATE TABLE permissions_absence (
    id              BIGSERIAL PRIMARY KEY,
    eleve_id        BIGINT NOT NULL REFERENCES eleves(id) ON DELETE CASCADE,
    date_debut      DATE NOT NULL,
    date_fin        DATE NOT NULL,
    motif           TEXT NOT NULL,
    statut          VARCHAR(20) NOT NULL DEFAULT 'en_attente'
        CHECK (statut IN ('en_attente', 'approuve', 'rejete')),
    traite_par      BIGINT REFERENCES utilisateurs(id),
    commentaire_traitement TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    traite_le       TIMESTAMPTZ
);

CREATE TABLE absences (
    id              BIGSERIAL PRIMARY KEY,
    eleve_id        BIGINT NOT NULL REFERENCES eleves(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    matiere_id      BIGINT REFERENCES matieres(id),   -- NULL = absence à la journée entière
    type            VARCHAR(20) NOT NULL DEFAULT 'absence' CHECK (type IN ('absence', 'retard')),
    justifiee       BOOLEAN NOT NULL DEFAULT false,
    permission_id   BIGINT REFERENCES permissions_absence(id),
    saisi_par       BIGINT REFERENCES utilisateurs(id),  -- enseignant
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_absences_eleve ON absences(eleve_id);

-- =====================================================================
-- 7. DISCIPLINE
-- =====================================================================

CREATE TABLE discipline (
    id              BIGSERIAL PRIMARY KEY,
    eleve_id        BIGINT NOT NULL REFERENCES eleves(id) ON DELETE CASCADE,
    date            DATE NOT NULL DEFAULT CURRENT_DATE,
    description     TEXT NOT NULL,
    gravite         VARCHAR(10) NOT NULL DEFAULT 'mineure'
        CHECK (gravite IN ('mineure', 'moyenne', 'grave')),
    sanction        TEXT,
    signale_par     BIGINT REFERENCES utilisateurs(id),   -- enseignant ou admin
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_discipline_eleve ON discipline(eleve_id);

-- =====================================================================
-- 8. PAIEMENTS — nombre/montant de tranches configurables
-- =====================================================================

CREATE TABLE tranches_paiement (
    id                  BIGSERIAL PRIMARY KEY,
    ecole_id            BIGINT NOT NULL REFERENCES ecoles(id) ON DELETE CASCADE,
    annee_scolaire_id   BIGINT NOT NULL REFERENCES annees_scolaires(id) ON DELETE CASCADE,
    numero              SMALLINT NOT NULL,
    libelle             VARCHAR(50),           -- ex: '1ère tranche'
    montant             NUMERIC(10,2) NOT NULL,
    date_limite         DATE,
    UNIQUE (ecole_id, annee_scolaire_id, numero)
);

CREATE TABLE paiements (
    id              BIGSERIAL PRIMARY KEY,
    eleve_id        BIGINT NOT NULL REFERENCES eleves(id) ON DELETE CASCADE,
    tranche_id      BIGINT NOT NULL REFERENCES tranches_paiement(id),
    montant_paye    NUMERIC(10,2) NOT NULL,
    date_paiement   DATE NOT NULL DEFAULT CURRENT_DATE,
    mode_paiement   VARCHAR(20) CHECK (mode_paiement IN ('especes', 'mobile_money', 'virement', 'cheque')),
    numero_recu     VARCHAR(50),
    enregistre_par  BIGINT REFERENCES utilisateurs(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_paiements_eleve ON paiements(eleve_id);

-- =====================================================================
-- Fin du brouillon — reste hors périmètre de ce fichier :
--   - table de synchronisation offline (Windows/SQLite <-> ici) : à
--     concevoir séparément, c'est le point le plus délicat du projet.
--   - table "bulletins_generes" (cache/figeage), si besoin plus tard.
--   - journal d'audit pour les accès aux données médicales/paiement.
-- =====================================================================
