import asyncio
import threading
import time
import os
import random
import json
from flask import Flask, request, jsonify
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
ASCII_ART = r"""
    ┌──────────────────────────────────────────────────────────────────────────┐
    │   _______   _______   ___   _______   __   __   _______   __    _        │
    │  |       | |       | |   | |       | |  | |  | |       | |  |  | |       │
    │   >> FLOWGPT BYPASS | HYDRA PROTOCOL v9.0 | TOR + FINGERPRINT SPOOF <<   │
    └──────────────────────────────────────────────────────────────────────────┘
"""
app = Flask(__name__)
API_KEY_GATEWAY = "UnHackerEnCapital"
TARGET_URL = "https://flowgpt.com/chat/wormgpt-6"

# PUERTOS DE TOR (Generalmente 9150 para Tor Browser, 9050 para servicio Tor)
PROXY_TOR = "socks5://127.0.0.1:9150" 

BROWSER_INSTANCE = {
    "playwright": None,
    "browser": None,
    "loop": None
}

# Lista de frases para ignorar (Bienvenida)
IGNORE_PHRASES = ["Never need pay", "start with your fist", "You are using"]

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# --- INYECCIÓN DE STEALTH (SPOOFING DE HARDWARE) ---
# Este script JS se inyecta en el navegador para mentir sobre qué PC eres.
STEALTH_JS = """
(() => {
    // 1. Eliminar rastro de automatización
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    
    // 2. Falsificar Plugins (Para parecer humano)
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    
    // 3. Falsificar Hardware (WebGL Fingerprint)
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // Spoof Vendor
        if (parameter === 37445) return 'Intel Inc.'; 
        // Spoof Renderer (Randomizado ligeramente por sesión)
        if (parameter === 37446) return 'Intel Iris OpenGL Engine'; 
        return getParameter(parameter);
    };
    
    // 4. Falsificar Idiomas
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
})();
"""

# --- MOTOR DE NAVEGACIÓN ---
async def iniciar_motor_base():
    """Inicia el navegador SIN contexto. El contexto se crea por petición."""
    p = await async_playwright().start()
    
    # Lanzamos el navegador en modo Headless (Oculto) o Visible.
    # Usamos argumentos para deshabilitar características de bot.
    args = [
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-infobars',
        '--disable-dev-shm-usage',
        '--disable-browser-side-navigation',
        '--disable-gpu'
    ]
    
    browser = await p.chromium.launch(headless=False, args=args)
    BROWSER_INSTANCE["playwright"] = p
    BROWSER_INSTANCE["browser"] = browser
    print(f"[*] Hydra Motor listo. Conectado a TOR: {PROXY_TOR}")

async def obtener_ip_actual(page):
    """Verifica si estamos saliendo por Tor."""
    try:
        await page.goto("http://checkip.amazonaws.com", timeout=10000)
        ip = await page.inner_text("body")
        return ip.strip()
    except:
        return "Desconocida (Error Check)"

async def procesar_mensaje_hydra(mensaje_usuario):
    browser = BROWSER_INSTANCE["browser"]
    if not browser: return "Error: Motor no iniciado."

    # 1. GENERACIÓN DE IDENTIDAD ÚNICA
    # Cada petición tendrá una resolución, UA y zona horaria distinta.
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/110.0"
    ]
    ua_random = random.choice(ua_list)
    
    # Configuración del Proxy (TOR) para este contexto específico
    # Esto asegura que la IP se enmascare.
    context = await browser.new_context(
        proxy={"server": PROXY_TOR}, 
        user_agent=ua_random,
        viewport={'width': 1366 + random.randint(-50, 50), 'height': 768 + random.randint(-50, 50)},
        locale="en-US",
        timezone_id="America/New_York",
        java_script_enabled=True
    )
    
    # Inyectar script anti-huella
    await context.add_init_script(STEALTH_JS)

    page = await context.new_page()

    try:
        # 2. VALIDACIÓN DE SEGURIDAD (Opcional, para debug)
        # print(f"[*] Identidad Nueva. UA: {ua_random[:20]}...")
        
        # 3. NAVEGACIÓN AL OBJETIVO
        # Timeout alto porque Tor es lento
        await page.goto(TARGET_URL, timeout=90000, wait_until="domcontentloaded")
        
        # Esperar textarea
        try:
            await page.wait_for_selector("textarea", timeout=45000)
        except Exception:
            await context.close()
            return "Error: Timeout cargando FlowGPT (Tor puede estar muy lento)."

        # Contar mensajes previos (Bienvenida)
        count_inicial = await page.locator(".flowgpt-markdown").count()

        # 4. ENVIAR MENSAJE
        await page.click("textarea")
        # Pequeña pausa humana
        await asyncio.sleep(random.uniform(0.5, 1.5)) 
        await page.fill("textarea", mensaje_usuario)
        await page.keyboard.press("Enter")

        print("... Hydra esperando respuesta a través de Tor ...")

        # 5. ESPERA Y DETECCIÓN DE ERRORES
        respuesta_final = ""
        max_retries = 60 # Tor es lento, damos 60s
        
        for _ in range(max_retries):
            await asyncio.sleep(1)
            
            # Verificar Bloqueo
            if await page.locator("text=Out of free credits").is_visible():
                print("[!] IP DE TOR QUEMADA. Reinicia identidad en Tor Browser (Ctrl+Shift+L).")
                await context.close()
                return "Error: IP Bloqueada por FlowGPT. Solicita 'New Identity' en Tor Browser."

            # Verificar Respuesta
            count_actual = await page.locator(".flowgpt-markdown").count()
            
            if count_actual > count_inicial:
                # Esperar renderizado
                await asyncio.sleep(3)
                
                ultimo = page.locator(".flowgpt-markdown").nth(count_actual - 1)
                texto = await ultimo.inner_text()
                
                # Filtro de bienvenida (Por si acaso)
                es_valido = True
                for f in IGNORE_PHRASES:
                    if f in texto: es_valido = False
                
                if es_valido and len(texto) > 1:
                    respuesta_final = texto
                    break
        
        await context.close()
        
        if respuesta_final:
            return respuesta_final
        else:
            return "Error: Timeout (Sin respuesta)."

    except Exception as e:
        await context.close()
        return f"Error Hydra: {str(e)}"

# --- ARRANQUE ---
def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def ejecutar_request(txt):
    future = asyncio.run_coroutine_threadsafe(procesar_mensaje_hydra(txt), BROWSER_INSTANCE["loop"])
    try: return future.result(timeout=150) # Timeout largo para Tor
    except: return "Timeout General"

@app.route('/v1/chat/completions', methods=['POST'])
def api():
    txt = request.json.get("messages", [{}])[-1].get("content", "")
    return jsonify({"choices": [{"message": {"role": "assistant", "content": ejecutar_request(txt)}}]})

def shell():
    print("\n[+] MODO HYDRA (TOR ACTIVO).")
    print("[-] Si falla, presiona 'New Identity' en tu Tor Browser.")
    while True:
        u = input("\n👤 Tú: ")
        if u == 'exit': break
        resp = ejecutar_request(u)
        print(f"\r🤖 WormGPT: {resp}")

def main():
    clear_screen()
    print(ASCII_ART)
    print("┌────────────────────────────────────────────────────────┐")
    print("│ ¡ATENCIÓN! ESTE SCRIPT REQUIERE TOR BROWSER ABIERTO    │")
    print("│ Puerto esperado: 9150 (Default de Tor Browser)         │")
    print("└────────────────────────────────────────────────────────┘")
    
    loop = asyncio.new_event_loop()
    BROWSER_INSTANCE["loop"] = loop
    threading.Thread(target=start_loop, args=(loop,), daemon=True).start()
    asyncio.run_coroutine_threadsafe(iniciar_motor_base(), loop)
    time.sleep(3)
    
    shell()

if __name__ == "__main__":
    try: main()
    except: pass