import os
import subprocess
import sys

# Carpeta donde quedará tu sesión lista para siempre
CARPETA_SESION = os.path.abspath("./perfil_navegador")
os.makedirs(CARPETA_SESION, exist_ok=True)

# Buscar el ejecutable de Google Chrome en tu PC
rutas_chrome = [
    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
]

chrome_exe = None
for ruta in rutas_chrome:
    if os.path.exists(ruta):
        chrome_exe = ruta
        break

if not chrome_exe:
    print("No se encontró Google Chrome instalado en tu equipo.")
    sys.exit(1)

print("="*65)
print("ABRIENDO CHROME OFICIAL (SIN BLOQUEOS DE GOOGLE)")
print("="*65)
print("1. En la primera pestaña: Iniciá sesión en tu cuenta de Google.")
print("2. En la segunda pestaña (TikTok): Tocá 'Continuar con Google'.")
print("   -> Va a entrar solo porque ya vas a estar conectado a Google.")
print("3. Cuando veas que TikTok ya tiene tu foto de perfil:")
print("   -> SIMPLEMENTE CERRÁ LA VENTANA DE CHROME CON LA CRUZ.")
print("="*65 + "\n")

# Abre Chrome nativo con Google y TikTok en pestañas separadas
proceso = subprocess.Popen([
    chrome_exe,
    f"--user-data-dir={CARPETA_SESION}",
    "--no-first-run",
    "--no-default-browser-check",
    "https://accounts.google.com",
    "https://www.tiktok.com/login"
])

# Espera a que cierres la ventana manualmente para confirmar que se guardó
proceso.wait()

print("\n-> ¡Excelente! La sesión de Google y TikTok quedó grabada en 'perfil_navegador'.")
print("-> Ahora ya podés correr el script de descarga.")