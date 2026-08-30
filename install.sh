#!/usr/bin/env bash
#
# Install Flugema into a uv-managed virtualenv under /opt/flugema,
# with persistent data in /var/lib/flugema.
#
# Usage:
#   sudo ./install.sh                 # install from the project directory (parent of deploy/)
#   sudo ./install.sh flugema         # install from PyPI
#   sudo ./install.sh ./dist/flugema-1.0-py3-none-any.whl
#
# Environment variables:
#   PYTHON_VERSION=3.12   Python version requested from uv (default: 3.12)
#   UV_BIN=/usr/local/bin/uv
#
set -euo pipefail

APP_NAME="flugema"
APP_USER="flugema"
APP_GROUP="flugema"
INSTALL_DIR="/opt/${APP_NAME}"
VENV_DIR="${INSTALL_DIR}/venv"
DATA_DIR="/var/lib/${APP_NAME}"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
ENV_FILE="/etc/default/${APP_NAME}"
PYTHON_VERSION="${PYTHON_VERSION:-3.14}"
UV_BIN="${UV_BIN:-/usr/local/bin/uv}"

# --- uv configuration --------------------------------------------------------
# Keep uv-managed interpreters under /opt so the service still works with
# ProtectHome=yes (they must not live in /root/.local/share/uv/python).
export UV_PYTHON_INSTALL_DIR="${INSTALL_DIR}/python"
# Install cache outside of /root, safe to purge.
export UV_CACHE_DIR="/var/cache/uv"
# Copy instead of hardlink: self-contained venv, no cross-device warning.
export UV_LINK_MODE=copy
export UV_NO_MODIFY_PATH=1

# Install source: first argument, or the project directory (parent of deploy/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
SOURCE="${1:-${PROJECT_DIR}}"

log() { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "This script must be run as root (sudo)."
command -v systemctl >/dev/null || die "systemd is required."

# --- uv ----------------------------------------------------------------------
if command -v uv >/dev/null 2>&1; then
    UV="$(command -v uv)"
elif [[ -x "$UV_BIN" ]]; then
    UV="$UV_BIN"
else
    command -v curl >/dev/null || die "curl is required to install uv (or install uv manually)."
    log "Installing uv into $(dirname "$UV_BIN")"
    curl -LsSf https://astral.sh/uv/install.sh \
        | env UV_INSTALL_DIR="$(dirname "$UV_BIN")" UV_NO_MODIFY_PATH=1 sh
    UV="$UV_BIN"
fi
log "Using uv: $("$UV" --version)"

# --- System user -------------------------------------------------------------
if ! getent group "$APP_GROUP" >/dev/null; then
    log "Creating group ${APP_GROUP}"
    groupadd --system "$APP_GROUP"
fi
if ! getent passwd "$APP_USER" >/dev/null; then
    log "Creating system user ${APP_USER}"
    useradd --system --gid "$APP_GROUP" \
            --home-dir "$DATA_DIR" --no-create-home \
            --shell /usr/sbin/nologin \
            --comment "${APP_NAME} service account" "$APP_USER"
fi

# --- Stop the service if already running (upgrade path) ----------------------
if systemctl is-active --quiet "${APP_NAME}.service"; then
    log "Stopping running service"
    systemctl stop "${APP_NAME}.service"
fi

# --- Directories -------------------------------------------------------------
log "Preparing ${INSTALL_DIR} and ${DATA_DIR}"
install -d -o root -g root -m 0755 "$INSTALL_DIR"
install -d -o root -g root -m 0755 "$UV_CACHE_DIR"
install -d -o "$APP_USER" -g "$APP_GROUP" -m 0700 "$DATA_DIR"

# --- Virtualenv (uv) ---------------------------------------------------------
log "Creating/updating virtualenv ${VENV_DIR} (Python ${PYTHON_VERSION})"
"$UV" venv --python "$PYTHON_VERSION" --allow-existing "$VENV_DIR"

log "Installing application from: ${SOURCE}"
VIRTUAL_ENV="$VENV_DIR" "$UV" pip install --upgrade "$SOURCE"

[[ -x "${VENV_DIR}/bin/${APP_NAME}" ]] \
    || die "Command ${APP_NAME} not found in ${VENV_DIR}/bin (check the package entry point)."

# World-readable code, not writable by the service account.
chown -R root:root "$INSTALL_DIR"
chmod -R go-w "$INSTALL_DIR"

# --- Environment file (created only once) ------------------------------------
if [[ ! -f "$ENV_FILE" ]]; then
    log "Creating ${ENV_FILE}"
    cat > "$ENV_FILE" <<EOF
# Environment overrides for ${APP_NAME} (systemd EnvironmentFile)
NICEGUI_STORAGE_PATH=${DATA_DIR}
#FLUGEMA_HOST=127.0.0.1
#FLUGEMA_PORT=8080
#FLUGEMA_SECRET_KEY=change-me
EOF
    chown root:"$APP_GROUP" "$ENV_FILE"
    chmod 0640 "$ENV_FILE"
fi

# --- systemd unit ------------------------------------------------------------
log "Installing ${SERVICE_FILE}"
install -o root -g root -m 0644 "${SCRIPT_DIR}/${APP_NAME}.service" "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable --now "${APP_NAME}.service"

sleep 1
systemctl --no-pager --full status "${APP_NAME}.service" || true

cat <<EOF

$(log "Installation complete")
  Venv    : ${VENV_DIR}
  Data    : ${DATA_DIR}
  Config  : ${ENV_FILE}
  Logs    : journalctl -u ${APP_NAME} -f
  Control : systemctl {status,restart,stop} ${APP_NAME}
EOF