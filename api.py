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
    │   >> UNHACKERENCAPITAL | FLOWGPT BYPASS | SMART WAITER v6.1 <<           │
    └──────────────────────────────────────────────────────────────────────────┘
"""
app = Flask(__name__)
API_KEY_GATEWAY = "UnHackerEnCapital"

# URL DEL BOT
TARGET_URL = "https://flowgpt.com/chat/wormgpt-6"

# Memoria de conversación
CHAT_MEMORY = [] 

# Variables globales
BROWSER_INSTANCE = {
    "browser": None,
    "playwright": None,
    "loop": None,
    "lock": threading.Lock()
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# --- MOTOR DE NAVEGACIÓN ---
async def iniciar_motor_base():
    p = await async_playwright().start()
    # Mantenemos headless=False para evadir mejor las detecciones
    browser = await p.chromium.launch(headless=False) 
    BROWSER_INSTANCE["playwright"] = p
    BROWSER_INSTANCE["browser"] = browser
    print("[*] Motor Chromium listo. Esperando peticiones...")

async def procesar_mensaje_con_bypass(mensaje_usuario):
    browser = BROWSER_INSTANCE["browser"]
    if not browser: return "Error: Motor no iniciado."

    # 1. Crear contexto VIRGEN (Incognito)
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()

    try:
        # 2. Navegar
        await page.goto(TARGET_URL, timeout=60000)
        
        # 3. Esperar carga inicial
        await page.wait_for_selector("textarea", timeout=30000)
        
        # --- CORRECCIÓN CLAVE: CONTAR MENSAJES INICIALES ---
        # Contamos cuántas burbujas de texto hay ANTES de hablar (generalmente 1: la bienvenida)
        msgs_iniciales = await page.locator(".flowgpt-markdown").count()
        # ---------------------------------------------------

        # 4. Inyectar Contexto (Memoria)
        prompt_final = ""
        if len(CHAT_MEMORY) > 0:
            historial_txt = "\n".join([f"User: {m['user']}\nYou: {m['bot']}" for m in CHAT_MEMORY[-2:]]) 
            prompt_final = f"(Context: {historial_txt})\n\nUser: {mensaje_usuario}"
        else:
            prompt_final = mensaje_usuario

        # 5. Escribir y Enviar
        await page.click("textarea")
        await page.fill("textarea", prompt_final)
        await page.keyboard.press("Enter")

        # 6. ESPERA INTELIGENTE (Bucle de detección)
        # Esperamos hasta que haya MÁS mensajes que al principio
        print("... Esperando generación de respuesta ...")
        
        max_retries = 30 # 30 segundos máx
        respuesta_final = ""
        
        for _ in range(max_retries):
            await asyncio.sleep(1)
            msgs_actuales = await page.locator(".flowgpt-markdown").count()
            
            if msgs_actuales > msgs_iniciales:
                # ¡Detectamos un mensaje nuevo!
                
                # Esperamos 2 segundos extra para que termine de escribirse el texto (streaming)
                await asyncio.sleep(2)
                
                # Obtenemos el texto del ÚLTIMO mensaje
                ultimo_elemento = page.locator(".flowgpt-markdown").nth(msgs_actuales - 1)
                texto = await ultimo_elemento.inner_text()
                
                # VALIDACIÓN EXTRA: Si el texto sigue siendo la bienvenida (por error), ignoramos
                if "Never need pay for WormGPT" in texto or "start with your fist need" in texto:
                    continue # Sigue esperando
                
                respuesta_final = texto
                break
        
        if respuesta_final:
            # Guardamos en memoria
            CHAT_MEMORY.append({"user": mensaje_usuario, "bot": respuesta_final})
            await context.close()
            return respuesta_final
        else:
            await context.close()
            return "Error: El bot no generó una respuesta nueva (Timeout)."

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

# --- API FLASK ---
@app.route('/v1/chat/completions', methods=['POST'])
def apithon_gateway():
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {API_KEY_GATEWAY}":
        return jsonify({"error": "Unauthorized"}), 401
    
    user_input = request.json.get("messages", [{}])[-1].get("content", "")
    output_text = ejecutar_request(user_input)
    
    return jsonify({
        "choices": [{"message": {"role": "assistant", "content": output_text}}], 
        "model": "flowgpt-bypass-v6.1"
    })

# --- CONSOLA ---
def run_interactive_shell():
    print("\n[+] MODO CHAT BYPASS v6.1 (Ignora Bienvenida).")
    while True:
        user_input = input("\n👤 Tú: ")
        if user_input.lower() in ['salir', 'exit']: break
        print("⏳ Enviando (Nueva Sesión)...", end="", flush=True)
        resp = ejecutar_request(user_input)
        # Limpiamos caracteres raros si los hay
        print(f"\r🤖 WormGPT: {resp}")

# --- MAIN ---
def main():
    clear_screen()
    print(ASCII_ART)
    
    new_loop = asyncio.new_event_loop()
    BROWSER_INSTANCE["loop"] = new_loop
    t = threading.Thread(target=start_background_loop, args=(new_loop,), daemon=True)
    t.start()
    
    print("[*] Arrancando Chrome (NO LO CIERRES)...")
    asyncio.run_coroutine_threadsafe(iniciar_motor_base(), new_loop)
    time.sleep(3) 

    print("\n[ Seleccione Entorno ]")
    print("1. Modo API")
    print("2. Chat Consola")
    
    op = input("\n> Opción: ")
    if op == "1":
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    else:
        run_interactive_shell()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Fin.")