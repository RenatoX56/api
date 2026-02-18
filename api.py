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
    │  |    _  | |    _  | |   | |    _  | |  |_|  | |    _  | |   |_| |       │
    │   >> UNHACKERENCAPITAL | FLOWGPT BYPASS | GUEST LOOP v6.0 <<             │
    └──────────────────────────────────────────────────────────────────────────┘
"""
app = Flask(__name__)
API_KEY_GATEWAY = "UnHackerEnCapital"

# URL DEL BOT (WormGPT v6)
TARGET_URL = "https://flowgpt.com/chat/wormgpt-6"

# Memoria de conversación (para inyectar contexto y que el bot no olvide)
CHAT_MEMORY = [] 

# Variables globales del navegador
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

# --- MOTOR DE NAVEGACIÓN EFÍMERA ---
async def iniciar_motor_base():
    """Arranca el navegador base, pero NO abre página todavía."""
    p = await async_playwright().start()
    # headless=False para que veas si Cloudflare pide click, puedes cambiarlo a True luego
    browser = await p.chromium.launch(headless=False) 
    BROWSER_INSTANCE["playwright"] = p
    BROWSER_INSTANCE["browser"] = browser
    print("[*] Motor Chromium listo. Esperando peticiones...")

async def procesar_mensaje_con_bypass(mensaje_usuario):
    """
    Estrategia: Abre un contexto NUEVO para cada mensaje (Bypass de créditos).
    Inyecta el historial anterior para no perder el hilo.
    """
    browser = BROWSER_INSTANCE["browser"]
    if not browser: return "Error: Motor no iniciado."

    # 1. Crear contexto VIRGEN (Incognito total)
    # Esto borra cookies y localStorage, FlowGPT piensa que eres un usuario nuevo = Créditos Gratis.
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()

    try:
        # 2. Navegar
        # print(f"[*] Conectando como nuevo invitado...")
        await page.goto(TARGET_URL, timeout=60000)
        
        # 3. Esperar carga e ignorar modales de bienvenida
        await page.wait_for_selector("textarea", timeout=30000)
        
        # 4. PREPARAR EL PROMPT CON MEMORIA INYECTADA
        # Como es una sesión nueva, el bot no sabe qué dijiste antes. Se lo recordamos.
        prompt_final = ""
        if len(CHAT_MEMORY) > 0:
            historial_txt = "\n".join([f"User: {m['user']}\nYou: {m['bot']}" for m in CHAT_MEMORY[-3:]]) # Solo los ultimos 3 para no saturar
            prompt_final = f"(System Note: This is a continuing conversation. Previous context:\n{historial_txt})\n\nUser: {mensaje_usuario}"
        else:
            prompt_final = mensaje_usuario

        # 5. Escribir y Enviar
        await page.click("textarea")
        await page.fill("textarea", prompt_final)
        await page.keyboard.press("Enter")

        # 6. Esperar Respuesta
        # print("... Esperando generación ...")
        # Esperamos a que aparezca al menos un markdown de respuesta
        # Nota: En sesión nueva, suele haber un mensaje de bienvenida del bot, la respuesta real es la 2da o la ultima.
        
        # Damos tiempo al stream
        await asyncio.sleep(4) 
        
        # Buscamos el último mensaje generado
        respuestas = page.locator(".flowgpt-markdown")
        count = await respuestas.count()
        
        # Reintentar si no ha respondido (lag)
        if count == 0:
            await asyncio.sleep(3)
            respuestas = page.locator(".flowgpt-markdown")
            count = await respuestas.count()

        if count > 0:
            texto_respuesta = await respuestas.nth(count - 1).inner_text()
            
            # Limpieza: A veces el bot repite el contexto, lo limpiamos si es necesario.
            # Guardamos en memoria RAM para la proxima vuelta
            CHAT_MEMORY.append({"user": mensaje_usuario, "bot": texto_respuesta})
            
            # CERRAR CONTEXTO INMEDIATAMENTE PARA MATAR LA SESIÓN
            await context.close()
            return texto_respuesta
        else:
            await context.close()
            return "Error: El bot no generó texto (Posible bloqueo de IP o Cloudflare)."

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
        "model": "flowgpt-bypass-v6"
    })

# --- INTERFAZ DE CONSOLA ---
def run_interactive_shell():
    print("\n[+] MODO CHAT BYPASS ACTIVADO (Sin Login).")
    print("[!] Nota: Cada mensaje abre una sesión nueva. Puede ser un poco más lento.")
    while True:
        user_input = input("\n👤 Tú: ")
        if user_input.lower() in ['salir', 'exit']: break
        print("⏳ Reencarnando sesión y enviando contexto...", end="", flush=True)
        resp = ejecutar_request(user_input)
        print(f"\r🤖 WormGPT: {resp}")

# --- MAIN ---
def main():
    clear_screen()
    print(ASCII_ART)
    
    # Iniciar Loop Asíncrono
    new_loop = asyncio.new_event_loop()
    BROWSER_INSTANCE["loop"] = new_loop
    t = threading.Thread(target=start_background_loop, args=(new_loop,), daemon=True)
    t.start()
    
    # Arrancar navegador base
    asyncio.run_coroutine_threadsafe(iniciar_motor_base(), new_loop)
    time.sleep(3) # Esperar a que chrome arranque

    print("\n[ Seleccione Entorno ]")
    print("1. Modo API (Para conectar con otros soft)")
    print("2. Chat Consola")
    
    op = input("\n> Opción: ")
    if op == "1":
        host = "0.0.0.0" 
        print(f"[*] API corriendo en puerto 5000.")
        app.run(host=host, port=5000, debug=False, use_reloader=False)
    else:
        run_interactive_shell()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Fin.")