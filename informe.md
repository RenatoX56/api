# 🔐 Resumen Ejecutivo — Análisis de Superficie de Ataque
**SUTEX SA / IFX Networks | Marzo 2026 | CONFIDENCIAL**

---

## ⚡ Conclusión Principal

El incidente de ransomware que cifró **14 máquinas** con `Generic.Ransom.N (CryptoGuard)` tuvo como vector de acceso inicial más probable la explotación de vulnerabilidades críticas en los servidores Apache/PHP expuestos públicamente, **no** el puerto SMB 445 (que operó solo como vector de movimiento lateral interno).

---

## 🗺️ Cadena de Ataque Reconstruida

```
[INTERNET]
    ↓ CVE-2024-4577 (RCE, CVSS 9.8) o CVE-2021-40438 (SSRF, CVSS 9.0)
190.60.215.92 — Apache 2.4.6 + PHP 8.1.27 (CentOS EOL)
    ↓ RCE como www-data/apache → reconocimiento interno
    ↓ PrintNightmare (CVE-2021-1675/34527) vía SMB 445 interno
spoolsv.exe comprometido → app106
    ↓ Propagación lateral SMB (SID 432099)
14 máquinas cifradas → CONTENIDO por aislamiento
```

---

## 🖥️ Hosts Analizados

| IP | OS | Hostname | Puertos | CVEs | Estado |
|---|---|---|---|---|---|
| 190.60.215.92 | CentOS | — | 80, 7007 | 149 | ⚠️ EOL — **Vector principal** |
| 190.60.215.91 | CentOS | disenos.sutex.com | 80, 443 | 148 | ⚠️ Crítico |
| 190.60.215.93 | Ubuntu | sai.sutex.com | 80, 443 | 2 | EOL |
| 190.60.215.90 | Windows | appe105.sutex.com | 444, 9002 | 1 | — |
| 190.60.215.82 | Windows | — | 88 | 1 | — |
| 190.60.215.83 | Windows | — | 80 | 0 | — |
| 190.60.215.89 | N/A | — | — | — | OFFLINE |

> **Ninguna IP expone el puerto 445 (SMB) a internet.** La entrada fue por los servidores web.

---

## 🚨 Vulnerabilidades Críticas (Top por EPSS)

| CVE | IP Afectada | CVSS | EPSS | Descripción |
|---|---|---|---|---|
| CVE-2021-40438 | .91, .92 | 9.0 | **99.985%** | Apache mod_proxy SSRF — acceso a hosts internos |
| CVE-2024-4577 | .92 | 9.8 | **99.96%** | PHP CGI RCE sin autenticación (**vector de entrada más probable**) |
| CVE-2023-44487 | .93 | 7.5 | **99.97%** | nginx HTTP/2 Rapid Reset — DDoS masivo |
| CVE-2024-38475 | .91, .92 | 9.1 | 99.81% | Apache mod_rewrite — mapeo de URLs a archivos arbitrarios |
| CVE-2021-44790 | .91, .92 | 9.8 | 99.43% | Apache mod_lua buffer overflow — RCE potencial |
| CVE-2024-1874 | .92 | 9.4 | 98.38% | PHP proc_open() command injection — RCE |
| CVE-2023-25690 | .91, .92 | 9.8 | 98.57% | HTTP Request Smuggling vía mod_proxy |
| CVE-2014-4078 | .82, .90 | 5.1 | 94.10% | IIS 8.5 — bypass de whitelist IP |

---

## 🔧 Remediaciones Prioritarias

### 🔴 Crítico — Acción Inmediata
- Actualizar **PHP a 8.1.31+** en `.92` (corrige CVE-2024-4577 y CVE-2024-1874)
- Actualizar **Apache a 2.4.62+** en `.91` y `.92` (corrige SSRF y request smuggling)
- Deshabilitar **PHP-CGI** y migrar a PHP-FPM
- Eliminar páginas de bienvenida por defecto de Apache
- **Migrar CentOS** a AlmaLinux o Rocky Linux (CentOS EOL desde diciembre 2024)

### 🟠 Alta
- Actualizar **nginx a 1.25.4+** en `.93`
- Aplicar parche **MS14-076** (CVE-2014-4078) en IIS 8.5 (`.82` y `.90`)
- Cerrar puertos no estándar: **7007** (.92), **9002** (.90), **88** (.82)
- Implementar **WAF** (ModSecurity o similar) frente a Apache/nginx
- Aplicar parche **PrintNightmare (KB5004945)** en todos los hosts Windows

### 🟡 Media
- Implementar **segmentación de red** entre servidores web y hosts Windows internos
- Deshabilitar **spoolsv.exe** en hosts Windows que no lo requieran
- Implementar **SIEM** con correlación de eventos SMB 445
- Auditar y rotar credenciales del **SID 432099** comprometido
- Actualizar **OpenSSL 1.0.2k** a versión 3.x en servidores CentOS

---

## ⚠️ Factores de Riesgo Adicionales Identificados

- Versiones de software **indexadas públicamente** en motores de búsqueda (fingerprinting trivial)
- Headers de servidor revelan versiones exactas (`Apache/2.4.6`, `PHP/8.1.27`)
- Páginas por defecto de Apache activas → **ausencia total de hardening**
- Sistemas marcados como **EOL** en bases de datos públicas de seguridad
- Puerto 7007 en `.92` menos monitoreado por firewalls y sistemas de detección

---

## 📋 Próximo Paso Recomendado

Analizar logs de acceso Apache en `.91` y `.92` para confirmar el vector de entrada:

```bash
/var/log/httpd/access_log  # Buscar patrones de explotación CVE-2024-4577
```

---

*Informe basado en OSINT — para atribución definitiva se requiere análisis forense de logs de acceso, eventos Windows y capturas de tráfico.*