<?php
// gestion_admins.php - Gestion des administrateurs (réservé aux Super Admin)
require_once 'includes/auth.php';
verifierSuperAdmin();

require_once 'config/db.php';

// Ajouter un utilisateur
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['ajouter'])) {
    $nom = trim($_POST['nom']);
    $email = trim($_POST['email']);
    $password = $_POST['password'];
    $role = $_POST['role'];
    
    $hash = password_hash($password, PASSWORD_DEFAULT);
    $stmt = $pdo->prepare("INSERT INTO utilisateurs (nom, email, mot_de_passe, role) VALUES (?, ?, ?, ?)");
    
    if ($stmt->execute([$nom, $email, $hash, $role])) {
        $succes = "Utilisateur ajouté avec succès !";
    } else {
        $erreur = "Erreur lors de l'ajout (email peut-être déjà utilisé).";
    }
}

// Modifier le rôle d'un utilisateur
if (isset($_POST['modifier_role'])) {
    $id = $_POST['user_id'];
    $nouveau_role = $_POST['nouveau_role'];
    
    if ($id != $_SESSION['user_id']) {
        $stmt = $pdo->prepare("UPDATE utilisateurs SET role = ? WHERE id = ?");
        $stmt->execute([$nouveau_role, $id]);
        $succes = "Rôle modifié !";
    } else {
        $erreur = "Vous ne pouvez pas modifier votre propre rôle.";
    }
}

// Supprimer un utilisateur
if (isset($_GET['supprimer'])) {
    $id = $_GET['supprimer'];
    if ($id != $_SESSION['user_id']) {
        $stmt = $pdo->prepare("DELETE FROM utilisateurs WHERE id = ?");
        $stmt->execute([$id]);
        $succes = "Utilisateur supprimé !";
    } else {
        $erreur = "Vous ne pouvez pas vous supprimer vous-même.";
    }
}

$utilisateurs = $pdo->query("SELECT * FROM utilisateurs ORDER BY role DESC, created_at ASC")->fetchAll();
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gestion des administrateurs - GestionEcole</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f2f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: linear-gradient(135deg, #008751, #006442);
            color: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 25px;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: #008751;
            margin-bottom: 20px;
            border-left: 4px solid #FCD116;
            padding-left: 15px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
        }
        
        input, select {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: #FCD116;
        }
        
        button {
            background: #008751;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        button:hover {
            background: #006442;
            transform: translateY(-2px);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background: #f8f9fa;
            color: #333;
        }
        
        .badge-super {
            background: #E8112D;
            color: white;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
        }
        
        .badge-admin {
            background: #FCD116;
            color: #333;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            text-decoration: none;
            font-size: 12px;
        }
        
        .btn-danger:hover {
            background: #c82333;
        }
        
        .nav {
            margin-bottom: 20px;
        }
        
        .nav a {
            text-decoration: none;
            color: #008751;
            margin-right: 15px;
            padding: 8px 15px;
            background: white;
            border-radius: 8px;
            transition: all 0.3s;
        }
        
        .nav a:hover {
            background: #FCD116;
        }
        
        .message-succes {
            background: #D4EDDA;
            color: #155724;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #008751;
        }
        
        .message-erreur {
            background: #F8D7DA;
            color: #721C24;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #E8112D;
        }
        
        .role-form {
            display: inline-block;
        }
        
        .role-select {
            width: auto;
            padding: 5px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👥 Gestion des administrateurs</h1>
            <p>Bienvenue, <strong><?= htmlspecialchars($_SESSION['nom']) ?></strong> ⭐ Super Administrateur</p>
        </div>
        
        <div class="nav">
            <a href="index.php">🏠 Accueil</a>
            <a href="eleves.php">👨‍🎓 Élèves</a>
            <a href="matieres.php">📚 Matières</a>
            <a href="notes.php">✏️ Notes</a>
            <a href="decisions.php">🎓 Décisions</a>
        </div>
        
        <?php if (isset($succes)): ?>
            <div class="message-succes">✅ <?= $succes ?></div>
        <?php endif; ?>
        
        <?php if (isset($erreur)): ?>
            <div class="message-erreur">❌ <?= $erreur ?></div>
        <?php endif; ?>
        
        <!-- Formulaire d'ajout -->
        <div class="card">
            <h2>➕ Ajouter un utilisateur</h2>
            <form method="POST">
                <div class="form-group">
                    <label>👤 Nom complet</label>
                    <input type="text" name="nom" required placeholder="Jean KPODA">
                </div>
                <div class="form-group">
                    <label>📧 Email</label>
                    <input type="email" name="email" required placeholder="exemple@ecole.bj">
                </div>
                <div class="form-group">
                    <label>🔒 Mot de passe (min 6 caractères)</label>
                    <input type="password" name="password" required minlength="6">
                </div>
                <div class="form-group">
                    <label>⭐ Rôle</label>
                    <select name="role">
                        <option value="admin">👤 Admin (gestion des notes)</option>
                        <option value="super_admin">⭐ Super Admin (gestion complète + utilisateurs)</option>
                    </select>
                </div>
                <button type="submit" name="ajouter">✅ Créer l'utilisateur</button>
            </form>
        </div>
        
        <!-- Liste des utilisateurs -->
        <div class="card">
            <h2>📋 Liste des administrateurs</h2>
            <?php if (count($utilisateurs) > 0): ?>
                <table>
                    <thead>
                        <tr>
                            <th>Nom</th>
                            <th>Email</th>
                            <th>Rôle</th>
                            <th>Date de création</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($utilisateurs as $user): ?>
                        <tr>
                            <td><?= htmlspecialchars($user['nom']) ?></td>
                            <td><?= htmlspecialchars($user['email']) ?></td>
                            <td>
                                <?php if ($user['role'] == 'super_admin'): ?>
                                    <span class="badge-super">⭐ Super Admin</span>
                                <?php else: ?>
                                    <span class="badge-admin">👤 Admin</span>
                                <?php endif; ?>
                            </td>
                            <td><?= date('d/m/Y H:i', strtotime($user['created_at'])) ?></td>
                            <td>
                                <?php if ($user['id'] != $_SESSION['user_id']): ?>
                                    <form method="POST" class="role-form">
                                        <input type="hidden" name="user_id" value="<?= $user['id'] ?>">
                                        <select name="nouveau_role" class="role-select" onchange="this.form.submit()">
                                            <option value="admin" <?= $user['role'] == 'admin' ? 'selected' : '' ?>>👤 Admin</option>
                                            <option value="super_admin" <?= $user['role'] == 'super_admin' ? 'selected' : '' ?>>⭐ Super Admin</option>
                                        </select>
                                        <input type="hidden" name="modifier_role" value="1">
                                    </form>
                                    <a href="?supprimer=<?= $user['id'] ?>" class="btn-danger" onclick="return confirm('Supprimer définitivement cet utilisateur ?')">🗑️ Supprimer</a>
                                <?php else: ?>
                                    <span style="color:#999;">🔒 Vous-même</span>
                                <?php endif; ?>
                            </td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            <?php else: ?>
                <p>Aucun utilisateur trouvé.</p>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>