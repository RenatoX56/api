import asyncio
import threading
import time
import os
import socket
import platform
from flask import Flask, request, jsonify
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
ASCII_ART = r"""
    ┌──────────────────────────────────────────────────────────────────────────┐
    │   _______   _______   ___   _______   __   __   _______   __    _        │
    │  |       | |       | |   | |       | |  | |  | |       | |  |  | |       │
    │   >> UNHACKERENCAPITAL | FLOWGPT BYPASS | STRICT FILTER v6.2 <<          │
    └──────────────────────────────────────────────────────────────────────────┘
"""
app = Flask(__name__)
API_KEY_GATEWAY = "UnHackerEnCapital"

TARGET_URL = "https://flowgpt.com/chat/wormgpt-6"
CHAT_MEMORY = [] 

# --- LISTA NEGRA DE FRASES (Mensaje de Bienvenida) ---
# Si el script lee esto, sabrá que aún NO ha respondido la IA.
IGNORE_PHRASES = [
    "You are using the WormGPT",
    "Never need pay for WormGPT",
    "start with your fist need",
    "fully uncensored",
    "digital landscape"
]

BROWSER_INSTANCE = {
    "browser": None,
    "playwright": None,
    "loop": None,
    "lock": threading.Lock()
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# --- MOTOR DE NAVEGACIÓN ---
async def iniciar_motor_base():
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False) 
    BROWSER_INSTANCE["playwright"] = p
    BROWSER_INSTANCE["browser"] = browser
    print("[*] Motor Chromium listo. Esperando peticiones...")

async def procesar_mensaje_con_bypass(mensaje_usuario):
    browser = BROWSER_INSTANCE["browser"]
    if not browser: return "Error: Motor no iniciado."

    context = await browser.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()

    try:
        # 1. Navegar
        await page.goto(TARGET_URL, timeout=60000)
        
        # 2. Esperar carga inicial y "asegurar" que el mensaje de bienvenida ya esté ahí
        await page.wait_for_selector("textarea", timeout=30000)
        # Pequeña pausa para asegurar que el DOM del mensaje de bienvenida terminó de pintarse
        await asyncio.sleep(2) 

        # 3. Preparar Prompt con Memoria
        prompt_final = ""
        if len(CHAT_MEMORY) > 0:
            historial_txt = "\n".join([f"User: {m['user']}\nYou: {m['bot']}" for m in CHAT_MEMORY[-2:]]) 
            prompt_final = f"(System: Continue conversation. Context:\n{historial_txt})\n\nUser: {mensaje_usuario}"
        else:
            prompt_final = mensaje_usuario

        # 4. Enviar Mensaje
        await page.click("textarea")
        await page.fill("textarea", prompt_final)
        await page.keyboard.press("Enter")

        # 5. ESPERA INTELIGENTE CON FILTRO DE CONTENIDO
        print("... Esperando respuesta válida ...")
        
        max_retries = 40 
        respuesta_final = ""
        
        for _ in range(max_retries):
            await asyncio.sleep(1)
            
            # Buscamos TODOS los mensajes markdown
            elementos = page.locator(".flowgpt-markdown")
            count = await elementos.count()
            
            if count > 0:
                # Tomamos siempre el ÚLTIMO mensaje visible
                ultimo_elemento = elementos.nth(count - 1)
                texto_actual = await ultimo_elemento.inner_text()
                
                # --- FILTRO ESTRICTO ---
                # Verificamos si el texto actual contiene alguna frase prohibida (la bienvenida)
                es_bienvenida = False
                for frase in IGNORE_PHRASES:
                    if frase in texto_actual:
                        es_bienvenida = True
                        break
                
                if es_bienvenida:
                    # Es el mensaje de bienvenida, seguimos esperando
                    # print("Ignorando mensaje de bienvenida...")
                    continue
                
                if not texto_actual.strip():
                    # Está vacío (cargando), seguimos esperando
                    continue

                # Si llegamos aquí, NO es bienvenida y NO está vacío -> ES LA RESPUESTA
                # Esperamos un poco más por si está escribiendo (streaming)
                await asyncio.sleep(2)
                
                # Volvemos a leer por si cambió durante los 2 segundos
                respuesta_final = await ultimo_elemento.inner_text()
                break
        
        if respuesta_final:
            CHAT_MEMORY.append({"user": mensaje_usuario, "bot": respuesta_final})
            await context.close()
            return respuesta_final
        else:
            await context.close()
            return "Error: Timeout (Solo se encontró el mensaje de bienvenida o nada)."

    except Exception as e:
        await context.close()
        return f"Error en bypass: {str(e)}"

# --- GESTOR DE HILOS ---
def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def ejecutar_request(user_query):
    future = asyncio.run_coroutine_threadsafe(procesar_mensaje_con_bypass(user_query), BROWSER_INSTANCE["loop"])
    try:
        return future.result(timeout=120)
    except Exception as e:
        return f"Timeout: {e}"

@app.route('/v1/chat/completions', methods=['POST'])
def apithon_gateway():
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {API_KEY_GATEWAY}":
        return jsonify({"error": "Unauthorized"}), 401
    user_input = request.json.get("messages", [{}])[-1].get("content", "")
    output_text = ejecutar_request(user_input)
    return jsonify({"choices": [{"message": {"role": "assistant", "content": output_text}}], "model": "flowgpt-bypass-v6.2"})

def run_interactive_shell():
    print("\n[+] MODO CHAT v6.2 (Filtro Anti-Bienvenida).")
    while True:
        user_input = input("\n👤 Tú: ")
        if user_input.lower() in ['salir', 'exit']: break
        print("⏳ Enviando...", end="", flush=True)
        resp = ejecutar_request(user_input)
        print(f"\r🤖 WormGPT: {resp}")

def main():
    clear_screen()
    print(ASCII_ART)
    new_loop = asyncio.new_event_loop()
    BROWSER_INSTANCE["loop"] = new_loop
    t = threading.Thread(target=start_background_loop, args=(new_loop,), daemon=True)
    t.start()
    asyncio.run_coroutine_threadsafe(iniciar_motor_base(), new_loop)
    time.sleep(3) 

    print("\n[ Seleccione Entorno ]")
    print("1. Modo API")
    print("2. Chat Consola")
    op = input("\n> Opción: ")
    if op == "1": app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    else: run_interactive_shell()

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n[!] Fin.")