-- =====================================================================
-- GestionEcole — données de départ (seed)
-- À exécuter APRÈS schema.sql, sur une base vide.
--
-- Contenu : données de référence structurelles (niveaux, séries, langues)
-- + une école pilote + l'année scolaire courante + ses trimestres.
--
-- Les matières et leurs coefficients sont chargés à part
-- (db/seed_coefficients.sql).
-- =====================================================================

-- ---------- Niveaux (communs à toutes les écoles) ----------
INSERT INTO niveaux (nom, cycle) VALUES
    ('6e',   'college'),
    ('5e',   'college'),
    ('4e',   'college'),
    ('3e',   'college'),
    ('2nde', 'lycee'),
    ('1ere', 'lycee'),
    ('Tle',  'lycee')
ON CONFLICT (nom) DO NOTHING;

-- ---------- Séries du lycée ----------
INSERT INTO series (nom) VALUES
    ('A1'), ('A2'), ('B'),
    ('C'), ('D'), ('E'),
    ('F2'), ('F3'), ('F4'),
    ('G1'), ('G2'), ('G3'),
    ('Eau et assainissement')
ON CONFLICT (nom) DO NOTHING;

-- ---------- Langues vivantes proposées ----------
INSERT INTO langues (nom) VALUES
    ('Anglais'), ('Allemand'), ('Espagnol')
ON CONFLICT (nom) DO NOTHING;

-- ---------- École pilote ----------
INSERT INTO ecoles (nom, sigle, mode_calcul_moyenne_annuelle, est_pilote)
VALUES ('École pilote', 'EP', 'poids_egal', true)
ON CONFLICT DO NOTHING;

-- ---------- Année scolaire courante + trimestres ----------
WITH e AS (SELECT id FROM ecoles WHERE est_pilote = true ORDER BY id LIMIT 1),
     a AS (
        INSERT INTO annees_scolaires (ecole_id, libelle, date_debut, date_fin, active)
        SELECT e.id, '2025-2026', DATE '2025-09-15', DATE '2026-07-15', true FROM e
        ON CONFLICT (ecole_id, libelle) DO NOTHING
        RETURNING id
     )
INSERT INTO trimestres (annee_scolaire_id, numero, date_debut, date_fin)
SELECT a.id, v.numero, v.d1, v.d2
FROM a
CROSS JOIN (VALUES
    (1, DATE '2025-09-15', DATE '2025-12-19'),
    (2, DATE '2026-01-05', DATE '2026-03-27'),
    (3, DATE '2026-04-06', DATE '2026-07-03')
) AS v(numero, d1, d2)
ON CONFLICT (annee_scolaire_id, numero) DO NOTHING;
