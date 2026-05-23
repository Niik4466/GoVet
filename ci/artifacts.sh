#!/usr/bin/env bash

# ==============================================================================
# SCRIPT DE EXTRACCIÓN DE ARTEFACTOS (ci/artifacts.sh)
# ==============================================================================
# Cumple con las buenas prácticas Bash (set -euo pipefail).
# Exporta las imágenes a formato .tar y extrae la carpeta de compilación estática del Frontend.

set -euo pipefail

# Obtener ruta absoluta del directorio raíz del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Función para registrar logs consistentes
log_info() {
    echo -e "\e[35m[ARTIFACTS] [INFO]\e[0m $1"
}

log_error() {
    echo -e "\e[31m[ARTIFACTS] [ERROR]\e[0m $1" >&2
}

# ------------------------------------------------------------------------------
# 1. Validación de dependencias
# ------------------------------------------------------------------------------
log_info "Verificando dependencias necesarias para exportar artefactos..."

check_dep() {
    local cmd="$1"
    local name="$2"
    if ! command -v "$cmd" &> /dev/null; then
        log_error "La herramienta requerida '$name' ($cmd) no está instalada o no está en el PATH."
        exit 1
    fi
    log_info "  - [OK] $name encontrado."
}

check_dep "docker" "Docker CLI"

# ------------------------------------------------------------------------------
# 2. Cargar variables de entorno (.env)
# ------------------------------------------------------------------------------
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE="${ROOT_DIR}/.env.example"

if [ -f "$ENV_FILE" ]; then
    log_info "Cargando variables de entorno desde .env..."
    export $(grep -v '^#' "$ENV_FILE" | xargs)
elif [ -f "$ENV_EXAMPLE" ]; then
    log_info "No se encontró .env. Cargando variables por defecto desde .env.example..."
    export $(grep -v '^#' "$ENV_EXAMPLE" | xargs)
else
    log_info "No se encontró ningún archivo de entorno. Se usarán valores predefinidos."
fi

# Definir variables por defecto si no fueron definidas
BACKEND_IMAGE="${BACKEND_IMAGE:-govet-backend}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-govet-frontend}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# ------------------------------------------------------------------------------
# 3. Crear Carpeta de Artefactos (Idempotente)
# ------------------------------------------------------------------------------
ARTIFACTS_DIR="${ROOT_DIR}/artifacts"
log_info "Preparando carpeta de artefactos en: $ARTIFACTS_DIR..."
mkdir -p "$ARTIFACTS_DIR"

# ------------------------------------------------------------------------------
# 4. Exportar Imágenes Docker (.tar)
# ------------------------------------------------------------------------------
log_info "Exportando imágenes Docker usando: docker save..."

log_info "Guardando imagen Backend ($BACKEND_IMAGE:$IMAGE_TAG) -> artifacts/govet-backend.tar..."
docker save -o "$ARTIFACTS_DIR/govet-backend.tar" "$BACKEND_IMAGE:$IMAGE_TAG"

log_info "Guardando imagen Frontend ($FRONTEND_IMAGE:$IMAGE_TAG) -> artifacts/govet-frontend.tar..."
docker save -o "$ARTIFACTS_DIR/govet-frontend.tar" "$FRONTEND_IMAGE:$IMAGE_TAG"

# ------------------------------------------------------------------------------
# 5. Extraer Compilación del Frontend (HTML/JS estático)
# ------------------------------------------------------------------------------
log_info "Extrayendo carpeta de distribución compilada (build) del Frontend..."

# 1. Crear un contenedor temporal a partir de la imagen compilada de producción
log_info "Creando contenedor temporal a partir de la imagen $FRONTEND_IMAGE:$IMAGE_TAG..."
TEMP_CONTAINER=$(docker create "$FRONTEND_IMAGE:$IMAGE_TAG")

# Asegurar que se limpie el contenedor al salir (incluso en caso de error)
cleanup() {
    log_info "Limpiando contenedor temporal..."
    docker rm -f "$TEMP_CONTAINER" &>/dev/null || true
}
trap cleanup EXIT

# 2. Copiar el directorio /usr/share/nginx/html (donde Nginx sirve los estáticos compilados) al host
log_info "Copiando carpeta /usr/share/nginx/html desde el contenedor a artifacts/frontend-build/..."
# Eliminar contenido previo si existe para que sea totalmente idempotente
rm -rf "$ARTIFACTS_DIR/frontend-build"
docker cp "$TEMP_CONTAINER:/usr/share/nginx/html" "$ARTIFACTS_DIR/frontend-build"

log_info "[OK] Compilación estática copiada exitosamente a artifacts/frontend-build/"
log_info "¡Fase de extracción de artefactos completada exitosamente!"
exit 0
