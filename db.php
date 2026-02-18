<?php
// db.php - VERSIÓN VULNERABLE PARA LABORATORIO
$conn = mysqli_connect("localhost", "root", "", "foro_pro_db");

if (!$conn) {
    die("Error de conexión: " . mysqli_connect_error());
}

// Iniciamos sesión sin flags de seguridad (HttpOnly/Secure) para permitir robo de cookies
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

// Función helper que NO sanitiza (permite XSS)
function e($value) {
    return $value; 
}
?>