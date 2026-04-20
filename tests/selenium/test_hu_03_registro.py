import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from docker_utils import run_in_backend

def test_registrar_paciente(logged_in_driver):
    driver = logged_in_driver
    wait = WebDriverWait(driver, 20)

    # Setup: Ejecutar script de relleno de tutores
    run_in_backend("rellenar_bd/script_rellena_ERTPPt.py")

    # 1. Navegar directamente al registro de paciente
    driver.get("http://localhost:3007/registro-paciente")
    
    # Esperar a que el spinner desaparezca si aparece
    try:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "ion-spinner")))
        WebDriverWait(driver, 15).until_not(EC.presence_of_element_located((By.TAG_NAME, "ion-spinner")))
    except:
        pass
        
    time.sleep(2)

    # 3. Ingresar datos usando JavaScript para mayor confiabilidad con Ionic
    def set_ion_input(name, value):
        driver.execute_script(f"""
            const el = document.querySelector('ion-input[name="{name}"]');
            if (el) {{
                el.value = "{value}";
                el.dispatchEvent(new CustomEvent('ionInput', {{ detail: {{ value: "{value}" }} }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)

    # Nombre
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ion-input[name='nombre']")))
    set_ion_input("nombre", "Mary")

    # Especie (SelectorEspecie)
    especie_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ion-input[label='Especie'] input")))
    especie_input.send_keys("Gato")
    gato_item = wait.until(EC.element_to_be_clickable((By.XPATH, "//ion-item[contains(., 'Gato')]")))
    driver.execute_script("arguments[0].click();", gato_item)

    # Raza (SelectorRaza)
    raza_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ion-input[label='Raza'] input")))
    raza_input.send_keys("DPC")
    raza_item = wait.until(EC.element_to_be_clickable((By.XPATH, "//ion-item[contains(., 'DPC')]")))
    driver.execute_script("arguments[0].click();", raza_item)

    # Color
    set_ion_input("color", "Blanco y Gris")

    # Sexo (Hembra)
    sex_radio = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "ion-radio[value='H']")))
    driver.execute_script("arguments[0].click();", sex_radio)

    # Fecha de nacimiento (Usamos JS para el type='date')
    set_ion_input("fechaNacimiento", "2022-01-01")

    # 4. Buscar Tutor
    buscar_tutor_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//ion-button[contains(., 'Buscar Tutor')]")))
    driver.execute_script("arguments[0].click();", buscar_tutor_btn)

    # En el modal de búsqueda, seleccionar el primero que aparezca
    time.sleep(2)
    tutor_items = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//ion-item[.//ion-label[contains(., 'RUT')]]")))
    driver.execute_script("arguments[0].click();", tutor_items[0])
    time.sleep(1)

    # Confirmar selección del tutor
    confirm_tutor_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//ion-button[contains(., 'Confirmar Selección')]")))
    driver.execute_script("arguments[0].click();", confirm_tutor_btn)
    time.sleep(1)

    # 5. Confirmar Registro del Paciente
    registrar_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//ion-button[contains(., 'Registrar paciente')]")))
    driver.execute_script("arguments[0].scrollIntoView();", registrar_btn)
    time.sleep(1)
    
    # Verificar si el botón está habilitado
    is_disabled = driver.execute_script("return arguments[0].disabled", registrar_btn)
    if is_disabled:
        print("Boton deshabilitado! Tomando screenshot extra.")
        driver.save_screenshot("/home/niik/Documents/Study/MyM/GoVet/tests/selenium/screenshots/debug_disabled_btn.png")
    
    driver.execute_script("arguments[0].click();", registrar_btn)

    # Resultado esperado: Mensaje de confirmación
    def find_success_toast(d):
        # Primero buscamos elementos ion-toast
        ts = d.find_elements(By.CSS_SELECTOR, "ion-toast")
        for t in ts:
            # Obtenemos el texto del mensaje
            try:
                msg = d.execute_script("return arguments[0].message || arguments[0].innerText || ''", t)
                if msg and ("exitosamente" in msg.lower() or "ingresada" in msg.lower()):
                    return t
            except:
                continue
        return False

    toast = WebDriverWait(driver, 30).until(find_success_toast)
    # Una vez encontrado, esperamos un poco para asegurar que el mensaje esté disponible
    time.sleep(1)
    
    # Teardown: Limpiar base de datos
    success, output = run_in_backend("rellenar_bd/script_limpia_rellena_ERTPPt.py")
    assert success, f"Error en teardown: {output}"
