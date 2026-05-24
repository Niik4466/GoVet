#!/usr/bin/env bash

# ==============================================================================
# SCRIPT DE PRUEBAS AUTOMATIZADAS (ci/test.sh)
# ==============================================================================
# Cumple con las buenas prácticas Bash (set -euo pipefail).
# Levanta el entorno de desarrollo en Docker, espera a que esté saludable,
# ejecuta la suite de pruebas (pytest y Cypress), y apaga los contenedores.

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
check_dep "docker" "Docker CLI"

# Determinar comando de python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    log_error "Python no está instalado o no se encuentra en el PATH."
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

# Validar plugin docker compose o binario clásico docker-compose
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
    log_info "  - [OK] Docker Compose v2 plugin detectado: $(docker compose version | head -n 1)"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    log_info "  - [OK] docker-compose v1 binario clásico detectado: $(docker-compose --version | head -n 1)"
else
    log_error "Docker Compose no está disponible."
    exit 1
fi

# ------------------------------------------------------------------------------
# 2. Configurar Archivo .env Temporal para Pruebas (si no existe)
# ------------------------------------------------------------------------------
# En CI (GitHub Actions), no hay archivo .env. Lo creamos con valores de prueba
# para que los contenedores docker compose se inicien correctamente.
if [ ! -f "${ROOT_DIR}/.env" ]; then
    log_info "No se detectó archivo .env local. Generando un .env de prueba..."
    cat <<EOF > "${ROOT_DIR}/.env"
# Configuración generada automáticamente para pruebas
POSTGRES_USER=pawsolutions
POSTGRES_PASSWORD=garrita
POSTGRES_DB=govet
DATABASE_URL=postgresql://pawsolutions:garrita@db:5432/govet
BACKEND_PORT=4007
FRONTEND_PORT=3007
ALLOWED_ORIGINS=*
VITE_API_URL=/api
BYPASS_TOKEN=test-bypass-sub
EOF
else
    # Si ya existe, aseguramos que contenga un BYPASS_TOKEN (si no, agregamos el default)
    if ! grep -q "BYPASS_TOKEN" "${ROOT_DIR}/.env"; then
        log_info "Agregando BYPASS_TOKEN por defecto al .env existente para pruebas..."
        echo "BYPASS_TOKEN=test-bypass-sub" >> "${ROOT_DIR}/.env"
    fi
fi

# ------------------------------------------------------------------------------
# 3. Orquestar Contenedores para Pruebas (Docker Compose)
# ------------------------------------------------------------------------------
log_info "Iniciando contenedores de desarrollo en segundo plano para ejecutar pruebas..."
cd "$ROOT_DIR"

# Definimos una función de limpieza para apagar los contenedores al salir (éxito o fallo)
cleanup() {
    log_info "Limpiando entorno: Apagando contenedores de prueba..."
    # Usamos el proyecto '-p govet' para mantener consistencia
    $COMPOSE_CMD -p govet down -v || true
}
# La señal EXIT se ejecutará al terminar el script bajo cualquier circunstancia
trap cleanup EXIT

# Levantamos el entorno usando el docker-compose.yml de desarrollo
# Forzamos el proyecto '-p govet' para asegurar que el contenedor backend se llame exactamente 'govet-backend-1'
log_info "Ejecutando: $COMPOSE_CMD -p govet up -d --build..."
$COMPOSE_CMD -p govet up -d --build

# ------------------------------------------------------------------------------
# 4. Esperar que los servicios estén listos y saludables (Polling)
# ------------------------------------------------------------------------------
log_info "Esperando a que los servicios estén en línea..."
TIMEOUT=60
ELAPSED=0

# Esperar por el Backend (puerto 4007)
log_info "Esperando a que el Backend (puerto 4007) responda..."
until curl -s http://localhost:4007/health &>/dev/null || curl -s http://localhost:4007/ &>/dev/null; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [ $ELAPSED -ge $TIMEOUT ]; then
        log_error "Timeout: El Backend no respondió en el puerto 4007 después de $TIMEOUT segundos."
        $COMPOSE_CMD -p govet logs backend
        exit 1
    fi
done
log_info "[OK] Backend listo."

# Esperar por el Frontend (puerto 3007)
log_info "Esperando a que el Frontend (puerto 3007) responda..."
ELAPSED=0
until curl -s http://localhost:3007/ &>/dev/null; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [ $ELAPSED -ge $TIMEOUT ]; then
        log_error "Timeout: El Frontend no respondió en el puerto 3007 después de $TIMEOUT segundos."
        $COMPOSE_CMD -p govet logs frontend
        exit 1
    fi
done
log_info "[OK] Frontend listo."

# ------------------------------------------------------------------------------
# 5. Instalar dependencias de testing y validar PyTest en el host/runner
# ------------------------------------------------------------------------------
log_info "Instalando dependencias de testing de Python en el host..."
if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
    if [ -f "${ROOT_DIR}/tests/selenium/requirements.txt" ]; then
        $PIP_CMD install -r "${ROOT_DIR}/tests/selenium/requirements.txt" || \
        $PIP_CMD install -r "${ROOT_DIR}/tests/selenium/requirements.txt" --break-system-packages
    fi
fi

# Determinar comando de ejecución de pytest
if command -v pytest &> /dev/null; then
    PYTEST_CMD="pytest"
    log_info "  - [OK] pytest encontrado: $($PYTEST_CMD --version | head -n 1)"
elif $PYTHON_CMD -m pytest --version &> /dev/null; then
    PYTEST_CMD="$PYTHON_CMD -m pytest"
    log_info "  - [OK] pytest encontrado como módulo de Python."
else
    log_info "pytest no encontrado globalmente, intentando instalación..."
    if [ -f "${ROOT_DIR}/tests/selenium/requirements.txt" ]; then
        $PIP_CMD install -r "${ROOT_DIR}/tests/selenium/requirements.txt" || true
    fi
    
    if command -v pytest &> /dev/null; then
        PYTEST_CMD="pytest"
    elif $PYTHON_CMD -m pytest --version &> /dev/null; then
        PYTEST_CMD="$PYTHON_CMD -m pytest"
    else
        log_error "No se pudo preparar pytest en el host."
        exit 1
    fi
fi

# ------------------------------------------------------------------------------
# 6. Ejecutar Suite de PyTest (Selenium)
# ------------------------------------------------------------------------------
log_info "Ejecutando suite de pruebas PyTest (Selenium)..."
cd "${ROOT_DIR}/tests/selenium"

# Configuramos la variable de entorno HEADLESS=true para que corra sin interfaz gráfica en CI/local por defecto
export HEADLESS=true

if $PYTEST_CMD; then
    log_info "[OK] Pruebas de PyTest pasadas con éxito."
else
    log_error "Fallo detectado en las pruebas de PyTest."
    exit 1
fi

# ------------------------------------------------------------------------------
# 7. Ejecutar Suite de Cypress (Frontend E2E)
# ------------------------------------------------------------------------------
log_info "Ejecutando pruebas de Cypress..."
cd "${ROOT_DIR}/Frontend"

# Ejecuta cypress run
if npm run test.e2e; then
    log_info "[OK] Pruebas de Cypress pasadas con éxito."
else
    log_error "Fallo detectado en las pruebas de Cypress."
    exit 1
fi

# El bloque de limpieza trap 'cleanup' se encargará de hacer "docker compose down" automáticamente.
log_info "¡Todas las pruebas pasaron con éxito!"
exit 0
