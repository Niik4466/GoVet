import os
import pytest
import requests
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.chrome.service import Service

# Cargar variables de entorno desde el .env del proyecto
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(env_path)

BASE_URL = "http://localhost:3007"
BACKEND_URL = "http://localhost:4007"
BYPASS_TOKEN = os.getenv("BYPASS_TOKEN")

@pytest.fixture(scope="session")
def driver():
    options = Options()
    
    # Intentar detectar Chromium si Chrome no está presente
    chromium_path = "/usr/bin/chromium"
    chromedriver_path = "/usr/bin/chromedriver"
    
    if os.path.exists(chromium_path):
        options.binary_location = chromium_path
    
    # Configuración de modo headless desde .env o variable de entorno
    headless_mode = os.getenv("HEADLESS", "true").lower() == "true"
    if headless_mode:
        options.add_argument("--headless")
        print("\n🚀 Ejecutando en modo HEADLESS (puedes cambiarlo con HEADLESS=false)")
    else:
        print("\n🖥️  Ejecutando en modo VISUAL (abriendo navegador)")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1024")
    
    if os.path.exists(chromedriver_path):
        service = Service(executable_path=chromedriver_path)
    else:
        # Fallback a webdriver-manager si no existe el del sistema
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.core.os_manager import ChromeType
        chrome_type = ChromeType.CHROMIUM if os.path.exists(chromium_path) else ChromeType.GOOGLE
        service = Service(ChromeDriverManager(chrome_type=chrome_type).install())
        
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # check if a test failed
    if rep.when == "call" and rep.failed:
        try:
            if "driver" in item.fixturenames:
                driver = item.funcargs["driver"]
            elif "logged_in_driver" in item.fixturenames:
                driver = item.funcargs["logged_in_driver"]
            else:
                return
            
            # Crear directorio de screenshots si no existe
            screenshot_dir = "/home/niik/Documents/Study/MyM/GoVet/tests/selenium/screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
            
            file_name = f"{item.name}_{int(time.time())}.png"
            path = os.path.join(screenshot_dir, file_name)
            driver.save_screenshot(path)
            print(f"\nScreenshot guardado en: {path}")
        except Exception as e:
            print(f"\nError al guardar screenshot: {e}")

@pytest.fixture(scope="function")
def logged_in_driver(driver):
    """
    Realiza el bypass de autenticación inyectando un token de sesión en localStorage.
    """
    # 1. Obtener token de bypass del backend
    try:
        response = requests.post(f"{BACKEND_URL}/login", json={"idToken": BYPASS_TOKEN})
        response.raise_for_status()
        token = response.json()["sessionToken"]
    except Exception as e:
        pytest.fail(f"No se pudo obtener el token de bypass: {e}")

    # 2. Navegar a la app para establecer el dominio en localStorage
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    
    # 3. Inyectar el token
    driver.execute_script(f"localStorage.setItem('govet_session_token', '{token}');")
    
    # 4. Forzar navegación al inicio para aplicar el token
    driver.get(f"{BASE_URL}/inicio")
    time.sleep(3)  # Esperar a que React cargue el estado de auth
    
    # Verificar si seguimos en login (si falló el bypass)
    if "/login" in driver.current_url or "google" in driver.page_source.lower():
        print("Bypass falló en primer intento, reintentando...")
        driver.execute_script(f"localStorage.setItem('govet_session_token', '{token}');")
        driver.refresh()
        time.sleep(2)

    # Inyectar CSS para ocultar toasts de actualización de PWA que interfieren con las pruebas
    driver.execute_script("""
        const style = document.createElement('style');
        style.innerHTML = 'ion-toast { --background: transparent !important; }';
        // O mejor, removerlos si contienen cierto texto
        setInterval(() => {
            const toasts = document.querySelectorAll('ion-toast');
            toasts.forEach(t => {
                if (t.message && t.message.toLowerCase().includes('versión')) {
                    t.remove();
                }
            });
        }, 1000);
    """)

    return driver
