<?php 
include 'db.php'; 

// VULNERABILIDAD: SQL Injection (No se valida que sea INT ni se usan Prepared Statements)
$id = $_GET['id']; 

// Inyección directa
$query = "SELECT posts.*, users.username FROM posts JOIN users ON posts.author_id = users.id WHERE posts.id = $id";
$result = mysqli_query($conn, $query);

if (!$result) {
    // VULNERABILIDAD: Error-Based SQLi (Muestra errores internos)
    die("<div class='container mt-5 text-danger'>Error SQL: " . mysqli_error($conn) . "</div>");
}

$post = mysqli_fetch_assoc($result);
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title><?php echo $post ? $post['title'] : 'Error'; ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #0b0e14; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
        .navbar { background-color: #161b22 !important; border-bottom: 2px solid #e94560; }
        .card { background-color: #161b22; border: 1px solid #30363d; color: white; }
        .btn-primary { background-color: #e94560; border: none; }
        .btn-primary:hover { background-color: #ff2e63; }
        .post-content { font-size: 1.1em; line-height: 1.6; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark mb-4">
        <div class="container">
            <a class="navbar-brand text-danger fw-bold" href="index.php">CYBER-SOC FORUM</a>
            <div class="d-flex">
                <?php if (!empty($_SESSION['user_id'])): ?>
                    <span class="text-muted small align-self-center me-3">User: <?php echo $_SESSION['username']; ?></span>
                    <a href="logout.php" class="btn btn-outline-light btn-sm me-2">Salir</a>
                <?php else: ?>
                    <a href="login.php" class="btn btn-outline-light btn-sm me-2">Login</a>
                <?php endif; ?>
                <a href="tools.php" class="btn btn-outline-danger btn-sm">Herramientas</a>
            </div>
        </div>
    </nav>

    <div class="container mt-5">
        <?php if($post): ?>
            <div class="card p-4 shadow-lg">
                <h1 class="display-5 text-danger"><?php echo $post['title']; ?></h1>
                <div class="d-flex justify-content-between text-muted border-bottom border-secondary pb-2 mb-3">
                    <span class="text-white">Publicado por: <strong><?php echo $post['username']; ?></strong></span>
                    <span>ID del Post: <?php echo $post['id']; ?></span>
                </div>
                
                <div class="post-content">
                    <?php echo $post['content']; ?>
                </div>
                
                <br>
                <div class="mt-4">
                    <a href="index.php" class="btn btn-secondary">Volver al inicio</a>
                </div>
            </div>
        <?php else: ?>
            <div class="alert alert-warning">Publicación no encontrada.</div>
            <a href="index.php" class="btn btn-secondary">Volver</a>
        <?php endif; ?>
    </div>
</body>
</html>