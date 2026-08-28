-- =====================================================================
-- Schoolaris — matières et coefficients de l'école pilote
-- Coefficients officiels par niveau et par série. À exécuter APRÈS seed.sql.
--
-- Rappel des libellés de matières : repris MOT POUR MOT des
-- tableaux officiels (y compris les variantes « Sciences physiques » vs
-- « Sciences physiques/PCT »). À faire valider / fusionner avec l'école
-- pilote si certaines désignent la même matière.
--
-- Collège : les tableaux officiels n'énumèrent pas les matières. On ne pose donc que les
-- coefficients par défaut (6e-5e = 1, 4e-3e = 2) + les exceptions 4e-3e
-- (Maths = 3, EPS = 1). Les matières du collège seront créées à l'usage
-- et hériteront du défaut.
-- =====================================================================

-- ---------- Matières (école pilote) ----------
WITH e AS (SELECT id FROM ecoles WHERE est_pilote = true ORDER BY id LIMIT 1)
INSERT INTO matieres (ecole_id, nom, est_choix_langue)
SELECT e.id, m.nom, m.clv
FROM e CROSS JOIN (VALUES
    ('Français', false),
    ('Philosophie', false),
    ('Histoire-Géographie', false),
    ('Mathématiques', false),
    ('Mathématiques appliquées', false),
    ('SVT', false),
    ('EPS', false),
    ('Anglais', false),
    ('Économie', false),
    ('Sciences physiques', false),
    ('Sciences physiques/PCT', false),
    ('LV1', true),
    ('LV2', true),
    ('Construction mécanique', false),
    ('Manipulation/TP', false),
    ('Manipulation pratique', false),
    ('Étude de fabrication ou Technologie', false),
    ('Réalisation de maquette TP', false),
    ('Étude d''un système technique', false),
    ('Mesures/essais laboratoire TP', false),
    ('Informatique TP', false),
    ('Étude de système technique', false),
    ('Construction TP', false),
    ('Électrotechnique', false),
    ('Construction/Projet d''exploitation TP', false),
    ('Dessin technique TP', false),
    ('Résistance des matériaux', false),
    ('Béton armé', false),
    ('Métré et étude de prix', false),
    ('Procédé de construction', false),
    ('Étude de cas', false),
    ('Compte-rendu/PV/Rapport', false),
    ('Techniques de base de secrétariat', false),
    ('Droit administratif + droit du travail', false),
    ('Droit (TBAD/Finances publiques)', false),
    ('Mobilisation des ressources en eau', false),
    ('Projet d''exploitation', false),
    ('Traitement de l''eau TP', false),
    ('Réseaux hydrauliques TP', false),
    ('Assainissement', false)
) AS m(nom, clv)
ON CONFLICT (ecole_id, nom) DO NOTHING;

-- ---------- Coefficients par défaut ----------
WITH e AS (SELECT id FROM ecoles WHERE est_pilote = true ORDER BY id LIMIT 1)
INSERT INTO coefficients_defaut (ecole_id, niveau_id, serie_id, coefficient)
SELECT e.id, n.id, NULL, v.coef
FROM e
CROSS JOIN (VALUES ('6e', 1), ('5e', 1), ('4e', 2), ('3e', 2)) AS v(niveau, coef)
JOIN niveaux n ON n.nom = v.niveau
ON CONFLICT ON CONSTRAINT coefficients_defaut_cle DO NOTHING;

WITH e AS (SELECT id FROM ecoles WHERE est_pilote = true ORDER BY id LIMIT 1)
INSERT INTO coefficients_defaut (ecole_id, niveau_id, serie_id, coefficient)
SELECT e.id, NULL, s.id, 1
FROM e CROSS JOIN series s
ON CONFLICT ON CONSTRAINT coefficients_defaut_cle DO NOTHING;

-- ---------- Collège 4e-3e : exceptions au défaut ----------
WITH e AS (SELECT id FROM ecoles WHERE est_pilote = true ORDER BY id LIMIT 1)
INSERT INTO coefficients (ecole_id, niveau_id, serie_id, matiere_id, coefficient)
SELECT e.id, n.id, NULL, mat.id, v.coef
FROM e
CROSS JOIN (VALUES
    ('4e', 'Mathématiques', 3), ('3e', 'Mathématiques', 3),
    ('4e', 'EPS', 1),           ('3e', 'EPS', 1)
) AS v(niveau, matiere, coef)
JOIN niveaux n  ON n.nom = v.niveau
JOIN matieres mat ON mat.ecole_id = e.id AND mat.nom = v.matiere
ON CONFLICT ON CONSTRAINT coefficients_cle DO NOTHING;

-- ---------- Lycée : coefficients par série ----------
-- Coefficients identiques en 2nde / 1ere / Tle -> niveau_id = NULL.
WITH e AS (SELECT id FROM ecoles WHERE est_pilote = true ORDER BY id LIMIT 1)
INSERT INTO coefficients (ecole_id, niveau_id, serie_id, matiere_id, coefficient)
SELECT e.id, NULL, s.id, mat.id, v.coef
FROM e
CROSS JOIN (VALUES
    -- Série A1
    ('A1', 'Français', 5), ('A1', 'Philosophie', 4), ('A1', 'Histoire-Géographie', 3),
    ('A1', 'LV1', 3), ('A1', 'LV2', 2), ('A1', 'Mathématiques', 2), ('A1', 'SVT', 2), ('A1', 'EPS', 1),
    -- Série A2
    ('A2', 'Français', 4), ('A2', 'Philosophie', 3), ('A2', 'Histoire-Géographie', 5),
    ('A2', 'LV1', 3), ('A2', 'LV2', 2), ('A2', 'Mathématiques', 2), ('A2', 'SVT', 2), ('A2', 'EPS', 1),
    -- Série B (LV1 seule, pas de LV2)
    ('B', 'Français', 4), ('B', 'Philosophie', 3), ('B', 'Histoire-Géographie', 4),
    ('B', 'LV1', 2), ('B', 'Économie', 4), ('B', 'Mathématiques', 2), ('B', 'SVT', 2), ('B', 'EPS', 1),
    -- Série C
    ('C', 'Mathématiques', 6), ('C', 'Sciences physiques', 5), ('C', 'Français', 2), ('C', 'Anglais', 2),
    ('C', 'SVT', 2), ('C', 'Histoire-Géographie', 2), ('C', 'Philosophie', 2), ('C', 'EPS', 1),
    -- Série D
    ('D', 'SVT', 5), ('D', 'Mathématiques', 4), ('D', 'Sciences physiques/PCT', 4), ('D', 'Français', 2),
    ('D', 'Anglais', 2), ('D', 'Histoire-Géographie', 2), ('D', 'Philosophie', 2), ('D', 'EPS', 1),
    -- Série E
    ('E', 'Mathématiques', 5), ('E', 'Sciences physiques', 4), ('E', 'Construction mécanique', 3),
    ('E', 'Manipulation/TP', 3), ('E', 'Manipulation pratique', 3), ('E', 'Français', 2),
    ('E', 'Étude de fabrication ou Technologie', 2), ('E', 'EPS', 1),
    -- Série F2
    ('F2', 'Réalisation de maquette TP', 4), ('F2', 'Étude d''un système technique', 4),
    ('F2', 'Mathématiques', 3), ('F2', 'Mesures/essais laboratoire TP', 3), ('F2', 'Informatique TP', 2),
    ('F2', 'Français', 2), ('F2', 'Sciences physiques', 2), ('F2', 'Construction mécanique', 2), ('F2', 'EPS', 1),
    -- Série F3
    ('F3', 'Étude de système technique', 5), ('F3', 'Construction TP', 4), ('F3', 'Électrotechnique', 3),
    ('F3', 'Mathématiques', 3), ('F3', 'Mesures/essais laboratoire TP', 3), ('F3', 'Français', 2),
    ('F3', 'Sciences physiques', 2), ('F3', 'EPS', 1),
    -- Série F4
    ('F4', 'Construction/Projet d''exploitation TP', 3), ('F4', 'Dessin technique TP', 3),
    ('F4', 'Résistance des matériaux', 3), ('F4', 'Mathématiques', 3), ('F4', 'Français', 2),
    ('F4', 'Sciences physiques', 2), ('F4', 'Béton armé', 2), ('F4', 'Métré et étude de prix', 2),
    ('F4', 'Procédé de construction', 2), ('F4', 'EPS', 1),
    -- Série G1
    ('G1', 'Étude de cas', 4), ('G1', 'Français', 3), ('G1', 'Économie', 3),
    ('G1', 'Compte-rendu/PV/Rapport', 3), ('G1', 'Techniques de base de secrétariat', 3),
    ('G1', 'Anglais', 2), ('G1', 'Droit administratif + droit du travail', 2), ('G1', 'EPS', 1),
    -- Séries G2 et G3 (coefficients identiques, confirmé)
    ('G2', 'Étude de cas', 6), ('G2', 'Français', 3), ('G2', 'Économie', 3),
    ('G2', 'Mathématiques appliquées', 3), ('G2', 'Anglais', 2), ('G2', 'Droit (TBAD/Finances publiques)', 2), ('G2', 'EPS', 1),
    ('G3', 'Étude de cas', 6), ('G3', 'Français', 3), ('G3', 'Économie', 3),
    ('G3', 'Mathématiques appliquées', 3), ('G3', 'Anglais', 2), ('G3', 'Droit (TBAD/Finances publiques)', 2), ('G3', 'EPS', 1),
    -- Série Eau et assainissement
    ('Eau et assainissement', 'Mobilisation des ressources en eau', 4),
    ('Eau et assainissement', 'Projet d''exploitation', 4),
    ('Eau et assainissement', 'Traitement de l''eau TP', 4),
    ('Eau et assainissement', 'Réseaux hydrauliques TP', 3),
    ('Eau et assainissement', 'Mathématiques', 3),
    ('Eau et assainissement', 'Assainissement', 2),
    ('Eau et assainissement', 'Français', 2),
    ('Eau et assainissement', 'Sciences physiques/PCT', 2),
    ('Eau et assainissement', 'Anglais', 1),
    ('Eau et assainissement', 'EPS', 1)
) AS v(serie, matiere, coef)
JOIN series s     ON s.nom = v.serie
JOIN matieres mat ON mat.ecole_id = e.id AND mat.nom = v.matiere
ON CONFLICT ON CONSTRAINT coefficients_cle DO NOTHING;
