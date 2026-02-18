<?php
include 'db.php';

// Si no hay sesión (no te has logueado), te expulsa al login
if (!isset($_SESSION['user_id'])) {
    header("Location: login.php");
    exit;
}

// Obtenemos los datos frescos de la sesión
$usuario_actual = $_SESSION['username'];
$rol_actual = isset($_SESSION['role']) ? $_SESSION['role'] : 'Desconocido';
?>

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Panel de Control - ACCESO RESTRINGIDO</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #0f0f13; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; }
        .card { background-color: #1a1f2b; border: 1px solid #e94560; min-width: 400px; }
        .role-badge { font-size: 0.9em; padding: 5px 10px; border-radius: 4px; }
        .admin-glow { box-shadow: 0 0 20px rgba(233, 69, 96, 0.4); }
    </style>
</head>
<body>

    <div class="card p-5 <?php echo ($rol_actual === 'admin') ? 'admin-glow' : ''; ?>">
        <div class="text-center mb-4">
            <h1 class="display-4">🔓 ACCESO CONCEDIDO</h1>
            <p class="text-muted">Sistema de Gestión Interna</p>
        </div>

        <hr class="border-secondary">

        <div class="mb-4">
            <h4>Identidad Confirmada:</h4>
            <h2 class="text-success fw-bold">
                <?php echo strtoupper($usuario_actual); ?>
            </h2>
        </div>

        <div class="mb-4">
            <h4>Nivel de Privilegios:</h4>
            <?php if($rol_actual === 'admin'): ?>
                <span class="badge bg-danger role-badge">👑 ADMINISTRADOR (ROOT)</span>
                <p class="mt-2 text-danger small">Tienes control total del sistema.</p>
            <?php else: ?>
                <span class="badge bg-primary role-badge">👤 USUARIO ESTÁNDAR</span>
            <?php endif; ?>
        </div>

        <div class="d-grid gap-2">
            <a href="index.php" class="btn btn-outline-light">Ir al Foro</a>
            <a href="logout.php" class="btn btn-secondary">Cerrar Sesión</a>
        </div>
    </div>

</body>
</html>