#!/usr/bin/env bash

# ==============================================================================
# SCRIPT DE PUBLICACIÓN DE IMÁGENES DOCKER (ci/publish.sh)
# ==============================================================================
# Cumple con las buenas prácticas Bash (set -euo pipefail).
# Inicia sesión en Docker Hub u otro registro y sube las imágenes construidas.

set -euo pipefail

# Obtener ruta absoluta del directorio raíz del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Función para registrar logs consistentes
log_info() {
    echo -e "\e[33m[PUBLISH] [INFO]\e[0m $1"
}

log_error() {
    echo -e "\e[31m[PUBLISH] [ERROR]\e[0m $1" >&2
}

# ------------------------------------------------------------------------------
# 1. Validación de dependencias
# ------------------------------------------------------------------------------
log_info "Verificando dependencias necesarias para publicar imágenes..."

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

if [ -f "$ENV_FILE" ]; then
    log_info "Cargando variables de entorno desde .env..."
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    log_info "No se detectó el archivo .env. Se conservarán las variables de entorno del sistema."
fi

# Definir variables por defecto si no fueron definidas
BACKEND_IMAGE="${BACKEND_IMAGE:-govet-backend}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-govet-frontend}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"

# ------------------------------------------------------------------------------
# 3. Validar credenciales de publicación
# ------------------------------------------------------------------------------
# Si no están presentes DOCKER_USERNAME o DOCKER_PASSWORD, asumimos que es una ejecución local
# y nos saltamos este paso de manera elegante sin detener abruptamente con error.
if [ -z "${DOCKER_USERNAME:-}" ] || [ -z "${DOCKER_PASSWORD:-}" ]; then
    log_info "ADVERTENCIA: DOCKER_USERNAME o DOCKER_PASSWORD no están configurados."
    log_info "Se omitirá la fase de inicio de sesión y subida de imágenes (Publish)."
    log_info "Esto es correcto cuando se ejecuta de forma local."
    exit 0
fi

# ------------------------------------------------------------------------------
# 4. Login en Registro Docker
# ------------------------------------------------------------------------------
log_info "Autenticando en el registro Docker..."

if [ -n "$DOCKER_REGISTRY" ]; then
    log_info "Iniciando sesión en registro privado: $DOCKER_REGISTRY..."
    echo "$DOCKER_PASSWORD" | docker login "$DOCKER_REGISTRY" --username "$DOCKER_USERNAME" --password-stdin
else
    log_info "Iniciando sesión en Docker Hub..."
    echo "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USERNAME" --password-stdin
fi

# ------------------------------------------------------------------------------
# 5. Push de Imágenes a la Registry
# ------------------------------------------------------------------------------
log_info "Subiendo imágenes construidas al registro..."

log_info "Subiendo Backend: docker push $BACKEND_IMAGE:$IMAGE_TAG..."
docker push "$BACKEND_IMAGE:$IMAGE_TAG"

log_info "Subiendo Frontend: docker push $FRONTEND_IMAGE:$IMAGE_TAG..."
docker push "$FRONTEND_IMAGE:$IMAGE_TAG"

log_info "[OK] ¡Todas las imágenes se subieron correctamente al registro!"
log_info "¡Fase de publicación completada exitosamente!"
exit 0
