import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from docker_utils import run_in_backend

def test_modificar_paciente(logged_in_driver):
    driver = logged_in_driver
    wait = WebDriverWait(driver, 15)

    # Setup: Meter datos de prueba
    run_in_backend("rellenar_bd/script_rellena_ERTPPt.py")
    success, output = run_in_backend("rellenar_bd/script_meter_datos_prueba.py")
    assert success, f"Error en setup: {output}"

    # 1. Ir a /ver
    driver.get("http://localhost:3007/ver")
    
    # 2. Seleccionar sección de pacientes
    pacientes_segment = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ion-segment-button[value='pacientes']")))
    driver.execute_script("arguments[0].click();", pacientes_segment)
    time.sleep(1)

    # 3. Colocar Juan en la barra de búsqueda
    search_bar = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ion-searchbar input")))
    driver.execute_script("arguments[0].value = 'Juan'; arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", search_bar)
    time.sleep(2)

    # 4. Seleccionar a Juan y presionar editar
    try:
        juan_item = wait.until(EC.presence_of_element_located((By.XPATH, "//h2[contains(@class, 'paciente-nombre') and (contains(text(), 'Juan') or contains(text(), 'JUAN'))]")))
    except:
        driver.save_screenshot("/home/niik/Documents/Study/MyM/GoVet/tests/selenium/screenshots/error_search_juan.png")
        raise

    edit_btn = juan_item.find_element(By.XPATH, "./ancestor::ion-item//ion-button[@title='Editar' or @id='editar-paciente' or .//ion-icon]")
    driver.execute_script("arguments[0].click();", edit_btn)

    # 5. Cambiar el nombre de Juan a otro distinto
    nombre_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ion-input[name='nombre'] input")))
    driver.execute_script("arguments[0].value = '';", nombre_input)
    nombre_input.send_keys("Juan Modificado")

    # 6. Presionar confirmar
    confirm_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//ion-button[contains(., 'Guardar')]")))
    driver.execute_script("arguments[0].scrollIntoView();", confirm_btn)
    time.sleep(1)
    driver.execute_script("arguments[0].click();", confirm_btn)

    # Resultado esperado: Mensaje de confirmación
    def find_success_toast(d):
        ts = d.find_elements(By.CSS_SELECTOR, "ion-toast")
        for t in ts:
            msg = d.execute_script("return arguments[0].message", t)
            if msg and ("exitosamente" in msg.lower() or "ingresada" in msg.lower()):
                return t
        return False

    toast = WebDriverWait(driver, 15).until(find_success_toast)
    message = driver.execute_script("return arguments[0].message", toast)
    assert "exitosamente" in message.lower()

    # Verificar que "Juan" (el nombre viejo) ya no existe en la búsqueda
    driver.execute_script("arguments[0].value = 'Juan'; arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", search_bar)
    time.sleep(2)
    
    results = driver.find_elements(By.XPATH, "//h2[@class='paciente-nombre' and text()='Juan']")
    assert len(results) == 0, "El nombre antiguo 'Juan' todavía existe en la lista"

    # Teardown: Eliminar datos de prueba
    success, output = run_in_backend("rellenar_bd/script_eliminar_datos_prueba.py")
    assert success, f"Error en teardown: {output}"
