<?php
// index.php - Page publique de consultation des notes
require_once 'config/db.php';

$matricule = isset($_GET['matricule']) ? trim($_GET['matricule']) : null;
$eleve = null;
$notes = [];
$moyenne_generale = null;
$decision = null;

if ($matricule) {
    $stmt = $pdo->prepare("
        SELECT e.*, c.nom as classe_nom, c.avec_coefficients 
        FROM eleves e 
        JOIN classes c ON e.classe_id = c.id 
        WHERE e.matricule = ? OR e.id = ?
    ");
    $stmt->execute([$matricule, $matricule]);
    $eleve = $stmt->fetch();

    if ($eleve) {
        $stmt = $pdo->prepare("
            SELECT n.*, m.nom as matiere_nom, m.coefficient
            FROM notes n
            JOIN matieres m ON n.matiere_id = m.id
            WHERE n.eleve_id = ?
            ORDER BY m.nom, n.periode
        ");
        $stmt->execute([$eleve['id']]);
        $notes = $stmt->fetchAll();

        // Calcul des moyennes
        $matieres = [];
        foreach ($notes as $note) {
            $matiere = $note['matiere_nom'];
            if (!isset($matieres[$matiere])) {
                $matieres[$matiere] = [
                    'periodes' => [],
                    'coefficient' => $note['coefficient']
                ];
            }
            $moy_interro = ($note['interro1'] + $note['interro2'] + $note['interro3']) / 3;
            if ($eleve['avec_coefficients']) {
                $moy_periode = ($note['devoir1'] + $note['devoir2'] + $moy_interro) / 3;
            } else {
                $moy_periode = ($moy_interro + $note['devoir1'] + $note['devoir2']) / 3;
            }
            $matieres[$matiere]['periodes'][$note['periode']] = $moy_periode;
        }

        $somme_moyennes = 0;
        $somme_coeffs = 0;
        foreach ($matieres as $matiere => $data) {
            $moy_matiere = array_sum($data['periodes']) / count($data['periodes']);
            if ($eleve['avec_coefficients']) {
                $somme_moyennes += $moy_matiere * $data['coefficient'];
                $somme_coeffs += $data['coefficient'];
            } else {
                $somme_moyennes += $moy_matiere;
                $somme_coeffs++;
            }
        }
        if ($somme_coeffs > 0) {
            $moyenne_generale = $somme_moyennes / $somme_coeffs;
            $decision = $moyenne_generale >= 10 ? "ADMIS" : "REDOUBLEMENT";
        }
    }
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Consultation des notes - Collège Sainte Jeanne d'Arc</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
<div class="container">
    <!-- Drapeau du Bénin - VERT | JAUNE | ROUGE -->
    <div class="flag-wrapper">
        <div class="benin-flag">
            <div class="vertical-green"></div>
            <div class="horizontal-part">
                <div class="yellow-top"></div>
                <div class="red-bottom"></div>
            </div>
        </div>
    </div>

    <div class="hero">
        <h1>🏫 Collège Privé d'Enseignement Général</h1>
        <h2>"Sainte Jeanne d'Arc"</h2>
        <p>🇧🇯 République du Bénin - Année scolaire 2024/2025</p>
    </div>

    <div class="card">
        <h3 style="color: #008751; text-align: center; margin-bottom: 20px;">📖 Consultation des notes et résultats</h3>
        <form method="GET" class="search-form">
            <input type="text" name="matricule" placeholder="Code d'identification (ex: 15 ou CJS0012)" value="<?= htmlspecialchars($matricule) ?>" required>
            <button type="submit">🔍 Voir mes résultats</button>
        </form>
        <p style="text-align: center; font-size: 12px; color: #666; margin-top: 15px;">
            💡 Renseignez le code reçu à l'inscription
        </p>
    </div>

    <?php if ($matricule && !$eleve): ?>
        <div class="alert">
            ❌ Aucun élève trouvé avec le code "<strong><?= htmlspecialchars($matricule) ?></strong>"
        </div>
    <?php endif; ?>

    <?php if ($eleve): ?>
        <div class="info-eleve">
            <h3>👨‍🎓 <?= htmlspecialchars($eleve['prenom']) ?> <?= htmlspecialchars($eleve['nom']) ?></h3>
            <span class="badge">🎫 Code : <?= htmlspecialchars($eleve['matricule'] ?? $eleve['id']) ?></span>
            <span class="badge">📚 Classe : <?= htmlspecialchars($eleve['classe_nom']) ?></span>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Matière</th>
                        <th>Période</th>
                        <th>Interro 1</th>
                        <th>Interro 2</th>
                        <th>Interro 3</th>
                        <th>Devoir 1</th>
                        <th>Devoir 2</th>
                        <th>Moyenne</th>
                    </tr>
                </thead>
                <tbody>
                <?php foreach ($notes as $note):
                    $moy_interro = ($note['interro1'] + $note['interro2'] + $note['interro3']) / 3;
                    if ($eleve['avec_coefficients']) {
                        $moy_matiere = ($note['devoir1'] + $note['devoir2'] + $moy_interro) / 3;
                    } else {
                        $moy_matiere = ($moy_interro + $note['devoir1'] + $note['devoir2']) / 3;
                    }
                ?>
                    <tr>
                        <td><strong><?= htmlspecialchars($note['matiere_nom']) ?></strong></td>
                        <td>T<?= $note['periode'] ?></td>
                        <td><?= $note['interro1'] ?: '-' ?></td>
                        <td><?= $note['interro2'] ?: '-' ?></td>
                        <td><?= $note['interro3'] ?: '-' ?></td>
                        <td><?= $note['devoir1'] ?: '-' ?></td>
                        <td><?= $note['devoir2'] ?: '-' ?></td>
                        <td class="moyenne-cell"><?= round($moy_matiere, 2) ?>/20</td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>

        <div class="decision-box <?= $decision === 'ADMIS' ? 'admis' : 'redoublement' ?>">
            <h2><?= $decision === 'ADMIS' ? '🎓 ADMIS(E)' : '📚 REDOUBLEMENT' ?></h2>
            <p>Moyenne générale : <strong><?= round($moyenne_generale, 2) ?>/20</strong></p>
        </div>
    <?php endif; ?>

    <div class="admin-link">
        <a href="login.php">🔐 Espace administration</a>
    </div>

    <div class="footer">
        <p>© 2026 Collège Sainte Jeanne d'Arc - République du Bénin 🇧🇯</p>
    </div>
</div>
</body>
</html>