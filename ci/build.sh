#!/usr/bin/env bash

# ==============================================================================
# SCRIPT DE COMPILACIÓN Y VALIDACIÓN (ci/build.sh)
# ==============================================================================
# Cumple con las buenas prácticas Bash (set -euo pipefail).
# Compila el Frontend y valida la sintaxis del Backend (Python).

set -euo pipefail

# Obtener ruta absoluta del directorio raíz del proyecto (un nivel arriba de ci/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Función para registrar logs consistentes
log_info() {
    echo -e "\e[32m[BUILD] [INFO]\e[0m $1"
}

log_error() {
    echo -e "\e[31m[BUILD] [ERROR]\e[0m $1" >&2
}

# ------------------------------------------------------------------------------
# 1. Validación de dependencias
# ------------------------------------------------------------------------------
log_info "Verificando dependencias necesarias para la fase de compilación..."

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

# Verificar python y buscar pip
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    log_error "Python 3 no está instalado o no se encuentra en el PATH."
    exit 1
fi
log_info "  - [OK] Python encontrado: $($PYTHON_CMD --version)"

# Determinar comando de pip
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    PIP_CMD="$PYTHON_CMD -m pip"
fi

# ------------------------------------------------------------------------------
# 2. Compilación del Frontend
# ------------------------------------------------------------------------------
log_info "Iniciando compilación del Frontend..."
cd "${ROOT_DIR}/Frontend"

log_info "Ejecutando: npm ci..."
npm ci

log_info "Ejecutando: npm run build..."
npm run build

log_info "[OK] Frontend compilado con éxito."

# ------------------------------------------------------------------------------
# 3. Preparación y Validación del Backend
# ------------------------------------------------------------------------------
log_info "Iniciando preparación y validación del Backend..."
cd "${ROOT_DIR}/Backend"

# Instalar requerimientos de Python
if [ -f "requirements.txt" ]; then
    log_info "Instalando dependencias de Python desde requirements.txt..."
    # Si se ejecuta localmente y no en CI, sugerimos usar --user o un venv si falla la instalación global
    if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
        $PIP_CMD install -r requirements.txt
    else
        log_info "Ejecución local detectada. Intentando instalación de dependencias..."
        # Intentar instalar (si falla por break-system-packages, usar flag correspondiente)
        $PIP_CMD install -r requirements.txt || \
        $PIP_CMD install -r requirements.txt --break-system-packages || \
        log_info "Advertencia: No se pudieron instalar las dependencias directamente. Si estás usando un entorno virtual, actívalo antes de correr el script."
    fi
else
    log_info "No se encontró requirements.txt en el Backend, omitiendo instalación."
fi

# Validar sintaxis del código Python
log_info "Validando la sintaxis de los archivos Python..."
# Buscamos todos los archivos .py excluyendo carpetas de entornos virtuales o node_modules
find . -type d \( -name ".venv" -o -name "venv" -o -name "node_modules" \) -prune -o -name "*.py" -print0 | \
    xargs -0 -I {} $PYTHON_CMD -m py_compile {}

log_info "[OK] Validación de sintaxis Python completada sin errores."

# Retornar éxito
log_info "¡Fase de compilación y validación completada con éxito!"
exit 0
