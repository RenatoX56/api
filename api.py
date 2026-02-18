import asyncio
import threading
import time
import os
import socket
import platform
from flask import Flask, request, jsonify
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN E IDENTIDAD ---
ASCII_ART = r"""
    ┌──────────────────────────────────────────────────────────────────────────┐
    │   _______   _______   ___   _______   __   __   _______   __    _        │
    │  |       | |       | |   | |       | |  | |  | |       | |  |  | |       │
    │  |    _  | |    _  | |   | |    _  | |  |_|  | |    _  | |   |_| |       │
    │  |   |_| | |   |_| | |   | |   | | | |       | |   | | | |       |       │
    │  |    ___| |    ___| |   | |   | | | |       | |   |_| | |  _    |       │
    │  |   |     |   |     |   | |   | | | |   _   | |       | | | |   |       │
    │  |___|     |___|     |___| |___| |_| |__| |__| |_______| |_|  |__|       │
    │                                                                          │
    │   >> UNHACKERENCAPITAL | FLOWGPT ADAPTER | UI AUTOMATION v4.0 <<         │
    └──────────────────────────────────────────────────────────────────────────┘
"""
app = Flask(__name__)
API_KEY_GATEWAY = "UnHackerEnCapital"

# Variables globales para mantener el estado del navegador
BROWSER_CONTEXT = {
    "page": None,
    "browser": None,
    "playwright": None,
    "loop": None,
    "lock": threading.Lock()
}

SESS = {
    "target_url": "https://flowgpt.com/chat/wormgpt-6",
    "status_ready": False
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

# --- MOTOR DE NAVEGACIÓN PERSISTENTE ---
async def iniciar_navegador():
    """Inicia el navegador y lo mantiene abierto para recibir comandos."""
    p = await async_playwright().start()
    # Usamos headless=False para que puedas resolver captchas de Cloudflare si aparecen
    browser = await p.chromium.launch(headless=False) 
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    print(f"\n[*] Navegando a: {SESS['target_url']}")
    await page.goto(SESS['target_url'], timeout=60000)
    
    print("[*] Esperando carga de interfaz FlowGPT...")
    
    # Selector basado en el HTML proporcionado: textarea con placeholder
    try:
        # Esperamos al textarea o a un chequeo de Cloudflare
        await page.wait_for_selector("textarea", timeout=30000)
        print("[+] Interfaz de chat detectada correctamente.")
        
        # Guardamos referencias globales
        BROWSER_CONTEXT["playwright"] = p
        BROWSER_CONTEXT["browser"] = browser
        BROWSER_CONTEXT["page"] = page
        SESS["status_ready"] = True
        
    except Exception as e:
        print(f"[!] Error cargando la página (Posible Cloudflare): {e}")
        print("[!] Por favor, interactúa con la ventana del navegador manualmente si hay un Captcha.")

def start_background_loop(loop):
    """Ejecuta el bucle de eventos asyncio en un hilo separado."""
    asyncio.set_event_loop(loop)
    loop.run_forever()

# --- LÓGICA DE INTERACCIÓN (UI AUTOMATION) ---
async def interactuar_con_chat(mensaje):
    page = BROWSER_CONTEXT["page"]
    if not page:
        return "Error: Navegador no inicializado."

    try:
        # 1. Detectar cuántas respuestas hay antes de enviar
        mensajes_previos = await page.locator(".flowgpt-markdown").count()
        
        # 2. Escribir mensaje
        # Selector específico basado en tu HTML (textarea dentro del div main)
        await page.click("textarea")
        await page.fill("textarea", mensaje)
        
        # 3. Enviar (Enter suele funcionar en FlowGPT)
        await page.keyboard.press("Enter")
        
        # 4. Esperar a que aparezca una NUEVA respuesta
        # Esperamos hasta que el conteo de mensajes sea mayor al previo
        print("... Esperando respuesta del modelo ...")
        
        # Espera dinámica: verificamos cada 500ms si hay un nuevo mensaje
        max_retries = 60 # 30 segundos máximo
        nuevo_conteo = mensajes_previos
        
        for _ in range(max_retries):
            await asyncio.sleep(0.5)
            nuevo_conteo = await page.locator(".flowgpt-markdown").count()
            if nuevo_conteo > mensajes_previos:
                break
        
        if nuevo_conteo <= mensajes_previos:
            return "Error: Tiempo de espera agotado o el modelo no respondió."

        # 5. Esperar a que el texto termine de generarse
        # FlowGPT suele streamear. Esperamos un poco de inactividad en el texto o que el botón de 'Stop' desaparezca.
        # Simplificación: Esperamos 2 segundos extra para asegurar completitud.
        await asyncio.sleep(2) 
        
        # 6. Extraer el texto del último elemento
        respuestas = page.locator(".flowgpt-markdown")
        ultimo_mensaje = await respuestas.nth(nuevo_conteo - 1).inner_text()
        
        return ultimo_mensaje

    except Exception as e:
        return f"Error durante la interacción UI: {str(e)}"

def ejecutar_request_protocolo(user_query):
    if not SESS["status_ready"]:
        return "El sistema no está listo. Revise la ventana del navegador."
        
    # Comunicar hilo de Flask con hilo de Playwright
    future = asyncio.run_coroutine_threadsafe(interactuar_con_chat(user_query), BROWSER_CONTEXT["loop"])
    try:
        return future.result(timeout=60) # Timeout de 60s para la respuesta
    except Exception as e:
        return f"Timeout o error interno: {e}"

# --- MODO 1: GATEWAY & TUTORIAL ---
@app.route('/v1/chat/completions', methods=['POST'])
def apithon_gateway():
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {API_KEY_GATEWAY}":
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    messages = data.get("messages", [])
    if not messages:
        return jsonify({"error": "No messages provided"}), 400
        
    user_input = messages[-1].get("content", "")
    output_text = ejecutar_request_protocolo(user_input)
    
    return jsonify({
        "choices": [{"message": {"role": "assistant", "content": output_text}}], 
        "model": "flowgpt-worm-v6"
    })

def mostrar_tutorial(host_ip):
    es_windows = platform.system() == "Windows"
    print("\n" + "="*65)
    print("     📖 GUÍA DE USO - MODO PASARELA (GATEWAY FLOWGPT)")
    print("="*65)
    print(f"[*] API KEY: {API_KEY_GATEWAY}")
    print(f"[*] ENDPOINT: http://{host_ip}:5000/v1/chat/completions")
    
    payload = '{"messages": [{"role": "user", "content": "Hola WormGPT, como estas?"}]}'
    
    if es_windows:
        print("\n[>] EJEMPLO CURL (CMD):")
        print(f'curl http://{host_ip}:5000/v1/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer {API_KEY_GATEWAY}" -d "{payload.replace(chr(34), chr(92)+chr(34))}"')
    else:
        print("\n[>] EJEMPLO CURL (BASH):")
        print(f"curl http://{host_ip}:5000/v1/chat/completions \\")
        print(f"  -H 'Content-Type: application/json' \\")
        print(f"  -H 'Authorization: Bearer {API_KEY_GATEWAY}' \\")
        print(f"  -d '{payload}'")
    print("="*65)

def run_gateway_service(bind_all=False):
    host = "0.0.0.0" if bind_all else "127.0.0.1"
    display_ip = get_lan_ip() if bind_all else "127.0.0.1"
    mostrar_tutorial(display_ip)
    app.run(host=host, port=5000, debug=False, use_reloader=False)

# --- MODO 2: ANALIZADOR DIRECTO ---
def run_interactive_shell():
    print("\n[+] MODO CHAT DIRECTO ACTIVADO. Escriba 'salir' para finalizar.")
    while True:
        user_input = input("\n👤 Tú: ")
        if user_input.lower() in ['salir', 'exit']: break
        print("🤖 WormGPT: ", end="", flush=True)
        print(ejecutar_request_protocolo(user_input))

# --- FLUJO PRINCIPAL ---
def main():
    clear_screen()
    print(ASCII_ART)
    
    # Configurar el bucle de eventos para Playwright en un hilo separado
    new_loop = asyncio.new_event_loop()
    BROWSER_CONTEXT["loop"] = new_loop
    t = threading.Thread(target=start_background_loop, args=(new_loop,), daemon=True)
    t.start()
    
    # Lanzar navegador en el hilo del loop
    print("[*] Inicializando motor gráfico (No cierres la ventana que se abrirá)...")
    asyncio.run_coroutine_threadsafe(iniciar_navegador(), new_loop)
    
    # Esperar a que el navegador esté listo
    while not SESS["status_ready"]:
        time.sleep(1)
        # Si tarda mucho, el usuario puede ver la ventana y resolver captchas
    
    while True:
        print("\n[ Seleccione Entorno ]")
        print("1. Modo Pasarela (API Server)")
        print("2. Modo Chat Directo (Consola)")
        
        opcion = input("\n> Opción: ")

        if opcion == "1":
            while True:
                print("\n[ Configuración de Red ]")
                print("L. Localhost (Solo este equipo)")
                print("N. LAN (Disponible en toda tu red local)")
                red_opcion = input("> Alcance (L/N): ").upper()
                
                if red_opcion == "L":
                    threading.Thread(target=run_gateway_service, args=(False,), daemon=True).start()
                    break
                elif red_opcion == "N":
                    threading.Thread(target=run_gateway_service, args=(True,), daemon=True).start()
                    break
            
            print("\n[MANTENIENDO PASARELA... Ctrl+C para cerrar]")
            while True: time.sleep(1)
            
        elif opcion == "2":
            run_interactive_shell()
            break
        else:
            print("[!] Opción inválida.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Proceso finalizadoasd.")