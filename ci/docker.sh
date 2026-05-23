#!/usr/bin/env bash

# ==============================================================================
# SCRIPT DE CONSTRUCCIÓN DOCKER (ci/docker.sh)
# ==============================================================================
# Cumple con las buenas prácticas Bash (set -euo pipefail).
# Construye imágenes usando docker-compose.prod.yml y las etiqueta.

set -euo pipefail

# Obtener ruta absoluta del directorio raíz del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Función para registrar logs consistentes
log_info() {
    echo -e "\e[34m[DOCKER] [INFO]\e[0m $1"
}

log_error() {
    echo -e "\e[31m[DOCKER] [ERROR]\e[0m $1" >&2
}

# ------------------------------------------------------------------------------
# 1. Validación de dependencias
# ------------------------------------------------------------------------------
log_info "Verificando dependencias de Docker..."

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

# Validar plugin docker compose o binario clásico docker-compose
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
    log_info "  - [OK] Docker Compose v2 plugin detectado."
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    log_info "  - [OK] docker-compose v1 binario clásico detectado."
else
    log_error "Docker Compose (docker compose o docker-compose) no está instalado."
    exit 1
fi

# ------------------------------------------------------------------------------
# 2. Cargar variables de entorno (.env)
# ------------------------------------------------------------------------------
# Se prioriza .env, y si no existe se buscan valores en .env.example o variables cargadas
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE="${ROOT_DIR}/.env.example"

if [ -f "$ENV_FILE" ]; then
    log_info "Cargando variables de entorno desde .env..."
    # Filtra líneas vacías y comentarios antes de exportar
    export $(grep -v '^#' "$ENV_FILE" | xargs)
elif [ -f "$ENV_EXAMPLE" ]; then
    log_info "No se encontró .env. Cargando variables por defecto desde .env.example..."
    export $(grep -v '^#' "$ENV_EXAMPLE" | xargs)
else
    log_info "No se encontró ningún archivo de entorno (.env / .env.example). Se usarán valores predefinidos."
fi

# Definir variables por defecto si no fueron definidas
BACKEND_IMAGE="${BACKEND_IMAGE:-govet-backend}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-govet-frontend}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

log_info "Configuración de imágenes:"
log_info "  - Backend Image: $BACKEND_IMAGE"
log_info "  - Frontend Image: $FRONTEND_IMAGE"
log_info "  - Tag objetivo: $IMAGE_TAG"

# ------------------------------------------------------------------------------
# 3. Construir Imágenes Docker con Compose
# ------------------------------------------------------------------------------
log_info "Construyendo imágenes de producción con docker-compose.prod.yml..."
cd "$ROOT_DIR"

# Asegurar que existan variables básicas requeridas por el docker-compose.prod.yml para evitar advertencias de Compose
export VITE_GOOGLE_CLIENT_ID="${VITE_GOOGLE_CLIENT_ID:-mock_google_id}"
export VITE_API_URL="${VITE_API_URL:-http://localhost:4007}"

# Construimos backend y frontend utilizando un nombre de proyecto explícito 'govet'
log_info "Ejecutando: $COMPOSE_CMD -f docker-compose.prod.yml -p govet build backend frontend..."
$COMPOSE_CMD -f docker-compose.prod.yml -p govet build backend frontend

# ------------------------------------------------------------------------------
# 4. Etiquetar (Taggear) imágenes
# ------------------------------------------------------------------------------
log_info "Etiquetando imágenes construidas..."

# Docker compose -p govet genera imágenes nombradas govet-backend y govet-frontend
# Si por alguna razón la convención de nombres difiere, buscamos el ID construido de la imagen
BACKEND_LOCAL="govet-backend"
FRONTEND_LOCAL="govet-frontend"

# Validamos que las imágenes locales existan y las etiquetamos
log_info "Etiquetando $BACKEND_LOCAL:latest como $BACKEND_IMAGE:$IMAGE_TAG..."
docker tag "$BACKEND_LOCAL:latest" "$BACKEND_IMAGE:$IMAGE_TAG"

log_info "Etiquetando $FRONTEND_LOCAL:latest como $FRONTEND_IMAGE:$IMAGE_TAG..."
docker tag "$FRONTEND_LOCAL:latest" "$FRONTEND_IMAGE:$IMAGE_TAG"

log_info "[OK] Imágenes construidas y etiquetadas con éxito."
exit 0
