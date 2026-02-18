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
    │   >> UNHACKERENCAPITAL | FLOWGPT BYPASS | GHOST PROTOCOL v7.0 <<         │
    └──────────────────────────────────────────────────────────────────────────┘
"""
app = Flask(__name__)
API_KEY_GATEWAY = "UnHackerEnCapital"
TARGET_URL = "https://flowgpt.com/chat/wormgpt-6"
CHAT_MEMORY = [] 

# --- CONFIGURACIÓN DE RED (CAMBIO DE IP) ---
# Si tienes Tor Browser abierto, usa: "socks5://127.0.0.1:9150"
# Si no usas proxy, déjalo en None (pero te detectarán la IP si abusas)
PROXY_CONFIG = None 
# PROXY_CONFIG = {"server": "socks5://127.0.0.1:9150"} # Descomentar para usar TOR

# Lista de User-Agents para rotar identidad
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

IGNORE_PHRASES = ["Never need pay", "start with your fist need", "You are using"]

BROWSER_INSTANCE = {
    "playwright": None,
    "browser": None, # Navegador base
    "loop": None,
    "lock": threading.Lock()
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# --- MOTOR DE NAVEGACIÓN ---
async def iniciar_motor_base():
    p = await async_playwright().start()
    
    # Lanzamos el navegador base.
    # Si usamos Proxy, lo configuramos aquí.
    launch_args = ["--disable-blink-features=AutomationControlled"]
    
    browser = await p.chromium.launch(
        headless=False, 
        proxy=PROXY_CONFIG, # Aquí se inyecta el cambio de IP
        args=launch_args
    ) 
    
    BROWSER_INSTANCE["playwright"] = p
    BROWSER_INSTANCE["browser"] = browser
    print(f"[*] Motor Ghost listo. Proxy activo: {PROXY_CONFIG if PROXY_CONFIG else 'NO (Usando IP real)'}")

async def procesar_mensaje_con_bypass(mensaje_usuario):
    browser = BROWSER_INSTANCE["browser"]
    if not browser: return "Error: Motor no iniciado."

    # 1. GENERAR IDENTIDAD FALSA (Randomizar Fingerprint)
    ua_random = random.choice(USER_AGENTS)
    viewport_random = {'width': 1280 + random.randint(0, 100), 'height': 720 + random.randint(0, 100)}
    
    context = await browser.new_context(
        viewport=viewport_random,
        user_agent=ua_random,
        locale="en-US",
        timezone_id="America/New_York" # Disfrazar zona horaria
    )
    
    # 2. INYECTAR STEALTH (Ocultar que somos un bot)
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page = await context.new_page()

    try:
        # 3. NAVEGAR (Con IP cambiada si se configuró Proxy)
        # print(f"[*] Identidad: {ua_random[:30]}...")
        await page.goto(TARGET_URL, timeout=90000) # Timeout largo por si usas Tor
        
        # Espera de seguridad
        await page.wait_for_selector("textarea", timeout=40000)
        await asyncio.sleep(2)

        # 4. PREPARAR MEMORIA
        prompt_final = ""
        if len(CHAT_MEMORY) > 0:
            historial_txt = "\n".join([f"U: {m['user']}\nB: {m['bot']}" for m in CHAT_MEMORY[-2:]]) 
            prompt_final = f"(SYSTEM: PREVIOUS CONTEXT:\n{historial_txt})\n\nUSER QUERY: {mensaje_usuario}"
        else:
            prompt_final = mensaje_usuario

        # 5. ENVIAR
        await page.click("textarea")
        await page.fill("textarea", prompt_final)
        await page.keyboard.press("Enter")

        # 6. ESPERA INTELIGENTE
        print("... Ghost esperando respuesta ...")
        
        max_retries = 60
        respuesta_final = ""
        
        for _ in range(max_retries):
            await asyncio.sleep(1)
            
            # Verificación de baneo visual
            if await page.locator("text=Out of free credits").is_visible():
                print("[!] ALERTA: IP Quemada. Reinicia tu router o cambia de nodo Tor.")
                await context.close()
                return "Error: IP BANEADA. Cambia tu IP."

            msgs = page.locator(".flowgpt-markdown")
            count = await msgs.count()
            
            if count > 0:
                ultimo = msgs.nth(count - 1)
                texto = await ultimo.inner_text()
                
                # Filtro de bienvenida
                es_basura = False
                for f in IGNORE_PHRASES:
                    if f in texto: es_basura = True; break
                
                if not es_basura and texto.strip():
                    await asyncio.sleep(2)
                    respuesta_final = await ultimo.inner_text()
                    break
        
        if respuesta_final:
            CHAT_MEMORY.append({"user": mensaje_usuario, "bot": respuesta_final})
            await context.close()
            return respuesta_final
        else:
            await context.close()
            return "Error: Timeout o Bloqueo silencioso."

    except Exception as e:
        await context.close()
        return f"Error Ghost: {str(e)}"

# --- ARRANQUE ---
def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def ejecutar_request(txt):
    future = asyncio.run_coroutine_threadsafe(procesar_mensaje_con_bypass(txt), BROWSER_INSTANCE["loop"])
    try: return future.result(timeout=120)
    except: return "Timeout crítico"

@app.route('/v1/chat/completions', methods=['POST'])
def api():
    txt = request.json.get("messages", [{}])[-1].get("content", "")
    return jsonify({"choices": [{"message": {"role": "assistant", "content": ejecutar_request(txt)}}]})

def shell():
    print("\n[+] MODO GHOST v7.0 (Anti-Fingerprint).")
    while True:
        u = input("\n👤 Tú: ")
        if u == 'exit': break
        print(f"\r🤖 WormGPT: {ejecutar_request(u)}")

def main():
    clear_screen()
    print(ASCII_ART)
    
    # --- INSTRUCCIONES DE IP ---
    print("┌────────────────────────────────────────────────────────┐")
    print("│ PARA QUE ESTO FUNCIONE SIN LÍMITES, NECESITAS TOR:     │")
    print("│ 1. Descarga e instala Tor Browser.                     │")
    print("│ 2. Ábrelo y déjalo conectado en el fondo.              │")
    print("│ 3. Descomenta la línea 'PROXY_CONFIG' en el script.    │")
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