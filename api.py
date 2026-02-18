import asyncio
import threading
import time
import os
import random
import socket
from flask import Flask, request, jsonify
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
ASCII_ART = r"""
    ┌──────────────────────────────────────────────────────────────────────────┐
    │   _______   _______   ___   _______   __   __   _______   __    _        │
    │  |       | |       | |   | |       | |  | |  | |       | |  |  | |       │
    │   >> HYDRA PROTOCOL v9.1 | TOR AUTO-DETECT | PROXY TUNNEL <<             │
    └──────────────────────────────────────────────────────────────────────────┘
"""
app = Flask(__name__)
API_KEY_GATEWAY = "UnHackerEnCapital"
TARGET_URL = "https://flowgpt.com/chat/wormgpt-6"

# Variable global para guardar el puerto detectado
TOR_PORT = None 

BROWSER_INSTANCE = {
    "playwright": None,
    "browser": None,
    "loop": None
}

IGNORE_PHRASES = ["Never need pay", "start with your fist", "You are using"]

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# --- DETECTOR DE PUERTO TOR ---
def encontrar_puerto_tor():
    """Busca si Tor está corriendo en el puerto 9150 (Browser) o 9050 (Servicio)"""
    for puerto in [9150, 9050]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex(('127.0.0.1', puerto)) == 0:
                return puerto
    return None

# --- STEALTH JS (Anti-Fingerprint) ---
STEALTH_JS = """
(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Google Inc. (Intel)'; 
        if (parameter === 37446) return 'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)'; 
        return getParameter(parameter);
    };
})();
"""

# --- MOTOR ---
async def iniciar_motor_base():
    p = await async_playwright().start()
    
    # Argumentos para evitar detección básica
    args = [
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-infobars'
    ]
    
    # Lanzamos el navegador SIN proxy global (se configura por contexto)
    browser = await p.chromium.launch(headless=False, args=args)
    BROWSER_INSTANCE["playwright"] = p
    BROWSER_INSTANCE["browser"] = browser
    print(f"[*] Motor Base Listo. Esperando inyección de tráfico por puerto {TOR_PORT}...")

async def procesar_mensaje_hydra(mensaje_usuario):
    browser = BROWSER_INSTANCE["browser"]
    if not browser: return "Error: Motor no iniciado."

    # Configurar el túnel TOR
    proxy_settings = {"server": f"socks5://127.0.0.1:{TOR_PORT}"}
    
    # Identidad Aleatoria
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ]
    
    context = await browser.new_context(
        proxy=proxy_settings,  # <--- AQUÍ SE FUERZA EL USO DE TOR
        user_agent=random.choice(ua_list),
        viewport={'width': 1280 + random.randint(0, 50), 'height': 720 + random.randint(0, 50)},
        locale="en-US",
        timezone_id="America/New_York"
    )
    
    await context.add_init_script(STEALTH_JS)
    page = await context.new_page()

    try:
        # Navegar
        # print(f"[*] Conectando vía Tor (Puerto {TOR_PORT})...")
        await page.goto(TARGET_URL, timeout=120000) # Timeout largo para Tor
        
        try:
            await page.wait_for_selector("textarea", timeout=60000)
        except:
            await context.close()
            return "Error: Timeout. La red Tor está muy lenta o desconectada."

        count_inicial = await page.locator(".flowgpt-markdown").count()

        # Enviar
        await page.click("textarea")
        await asyncio.sleep(1)
        await page.fill("textarea", mensaje_usuario)
        await page.keyboard.press("Enter")

        # Esperar respuesta
        print("... Hydra esperando respuesta (vía Tor) ...")
        respuesta = ""
        
        # Bucle de espera (hasta 60s)
        for _ in range(60):
            await asyncio.sleep(1)
            
            # Verificar si nos bloquearon la IP
            if await page.locator("text=Out of free credits").is_visible():
                print("[!] IP QUEMADA. Pide nueva identidad en Tor Browser.")
                await context.close()
                return "Error: IP Baneada. Cambia identidad en Tor."

            count_actual = await page.locator(".flowgpt-markdown").count()
            
            if count_actual > count_inicial:
                await asyncio.sleep(3) # Dejar que termine de escribir
                ultimo = page.locator(".flowgpt-markdown").nth(count_actual - 1)
                texto = await ultimo.inner_text()
                
                # Verificar filtro
                es_valido = True
                for f in IGNORE_PHRASES:
                    if f in texto: es_valido = False
                
                if es_valido and len(texto) > 1:
                    respuesta = texto
                    break
        
        await context.close()
        return respuesta if respuesta else "Error: Sin respuesta (Timeout)"

    except Exception as e:
        await context.close()
        return f"Error Técnico: {str(e)}"

# --- ARRANQUE ---
def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def ejecutar_request(txt):
    future = asyncio.run_coroutine_threadsafe(procesar_mensaje_hydra(txt), BROWSER_INSTANCE["loop"])
    try: return future.result(timeout=180)
    except: return "Timeout General"

@app.route('/v1/chat/completions', methods=['POST'])
def api():
    txt = request.json.get("messages", [{}])[-1].get("content", "")
    return jsonify({"choices": [{"message": {"role": "assistant", "content": ejecutar_request(txt)}}]})

def shell():
    print(f"\n[+] SISTEMA ONLINE usando TOR en puerto {TOR_PORT}.")
    print("[*] Chromium se abrirá, pero su tráfico viaja oculto por Tor.")
    while True:
        u = input("\n👤 Tú: ")
        if u == 'exit': break
        resp = ejecutar_request(u)
        print(f"\r🤖 WormGPT: {resp}")

def main():
    global TOR_PORT
    clear_screen()
    print(ASCII_ART)
    
    print("[*] Buscando Tor Browser...")
    TOR_PORT = encontrar_puerto_tor()
    
    if TOR_PORT is None:
        print("\n[!!!] ERROR CRÍTICO: NO SE ENCUENTRA TOR [!!!]")
        print("1. Abre 'Tor Browser' en tu PC.")
        print("2. Espera a que se conecte (página violeta).")
        print("3. Vuelve a ejecutar este script.")
        print("------------------------------------------------")
        input("Presiona Enter para salir...")
        return

    print(f"[OK] Tor detectado en puerto {TOR_PORT}.")
    
    loop = asyncio.new_event_loop()
    BROWSER_INSTANCE["loop"] = loop
    threading.Thread(target=start_loop, args=(loop,), daemon=True).start()
    asyncio.run_coroutine_threadsafe(iniciar_motor_base(), loop)
    time.sleep(3)
    
    shell()

if __name__ == "__main__":
    try: main()
    except: pass