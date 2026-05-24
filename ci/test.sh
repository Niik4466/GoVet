#!/usr/bin/env bash

# ==============================================================================
# SCRIPT DE PRUEBAS AUTOMATIZADAS (ci/test.sh)
# ==============================================================================
# Cumple con las buenas prácticas Bash (set -euo pipefail).
# Ejecuta la suite de pruebas de backend (pytest) y frontend (Cypress).

set -euo pipefail

# Obtener ruta absoluta del directorio raíz del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Función para registrar logs consistentes
log_info() {
    echo -e "\e[36m[TEST] [INFO]\e[0m $1"
}

log_error() {
    echo -e "\e[31m[TEST] [ERROR]\e[0m $1" >&2
}

# ------------------------------------------------------------------------------
# 1. Validación de dependencias
# ------------------------------------------------------------------------------
log_info "Verificando dependencias necesarias para la fase de pruebas..."

check_dep() {
    local cmd="$1"
    local name="$2"
    if ! command -v "$cmd" &> /dev/null; then
        log_error "La herramienta requerida '$name' ($cmd) no está instalada o no está en el PATH."
        exit 1
    fi
    log_info "  - [OK] $name encontrado: $($cmd --version | head -n 1)"
}

check_dep "node" "Node.js"
check_dep "npm" "npm"

# Determinar comando de python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    log_error "Python no está instalado o no se encuentra en el PATH."
    exit 1
fi

# Determinar comando de pip
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    PIP_CMD="$PYTHON_CMD -m pip"
fi

# Instalamos los requerimientos específicos de testing si estamos en CI o localmente antes del chequeo de pytest
if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
    log_info "Instalando dependencias de testing adicionales (CI)..."
    if [ -f "${ROOT_DIR}/tests/selenium/requirements.txt" ]; then
        $PIP_CMD install -r "${ROOT_DIR}/tests/selenium/requirements.txt"
    fi
fi

# Determinar cómo ejecutar pytest (como comando global o módulo python)
if command -v pytest &> /dev/null; then
    PYTEST_CMD="pytest"
    log_info "  - [OK] pytest encontrado: $($PYTEST_CMD --version | head -n 1)"
elif $PYTHON_CMD -m pytest --version &> /dev/null; then
    PYTEST_CMD="$PYTHON_CMD -m pytest"
    log_info "  - [OK] pytest encontrado como módulo de Python."
else
    log_info "pytest no encontrado de forma global. Intentando instalar requerimientos locales de testing..."
    if [ -f "${ROOT_DIR}/tests/selenium/requirements.txt" ]; then
        $PIP_CMD install -r "${ROOT_DIR}/tests/selenium/requirements.txt" || true
    fi
    
    # Volvemos a chequear tras la instalación
    if command -v pytest &> /dev/null; then
        PYTEST_CMD="pytest"
        log_info "  - [OK] pytest encontrado tras instalación: $($PYTEST_CMD --version | head -n 1)"
    elif $PYTHON_CMD -m pytest --version &> /dev/null; then
        PYTEST_CMD="$PYTHON_CMD -m pytest"
        log_info "  - [OK] pytest encontrado tras instalación como módulo de Python."
    else
        log_error "pytest no está instalado y no pudo ser instalado automáticamente."
        exit 1
    fi
fi

# ------------------------------------------------------------------------------
# 2. Ejecutar PyTest (Backend / Selenium)
# ------------------------------------------------------------------------------
log_info "Iniciando ejecución de pruebas con PyTest..."
cd "${ROOT_DIR}/tests/selenium"

log_info "Ejecutando suite pytest..."
# NOTA: En entornos reales de CI sin interfaz gráfica (headless), pytest con Selenium 
# suele requerir un driver headless o mockeado. Los scripts detendrán el pipeline en caso de fallo.
if $PYTEST_CMD; then
    log_info "[OK] Suite de PyTest completada exitosamente."
else
    log_error "Fallo detectado en las pruebas de PyTest."
    exit 1
fi

# ------------------------------------------------------------------------------
# 3. Ejecutar Cypress (Frontend E2E)
# ------------------------------------------------------------------------------
log_info "Iniciando ejecución de pruebas de Cypress..."
cd "${ROOT_DIR}/Frontend"

# Si es en CI (GitHub Actions), Cypress requiere dependencias del sistema operativo que ya deben estar instaladas.
# Ejecutamos las pruebas E2E configuradas en package.json (npm run test.e2e que corre cypress run)
log_info "Ejecutando suite Cypress (npm run test.e2e)..."

if npm run test.e2e; then
    log_info "[OK] Suite de Cypress completada exitosamente."
else
    log_error "Fallo detectado en las pruebas de Cypress."
    exit 1
fi

log_info "¡Todas las pruebas pasaron con éxito! Deteniendo pipeline de forma limpia."
exit 0
