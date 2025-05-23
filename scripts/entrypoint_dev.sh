#!/bin/bash
set -e

# Chemin du fichier de configuration Odoo
ODOO_CONF=${ODOO_RC:-/etc/odoo/odoo.conf}
ODOO_CONF_DIR=$(dirname "$ODOO_CONF")
TMP_CONF="/tmp/odoo_temp.conf"

# Variables de base de données
DB_HOST=${PGHOST:-db}
DB_PORT=${PGPORT:-5432}
DB_USER=${PGUSER:-odoo}
DB_PASSWORD=${PGPASSWORD:-odoo}

# Variables de configuration Odoo
ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin}
ADDONS_PATH=${ADDONS_PATH:-/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons}
DATA_DIR=${DATA_DIR:-/var/lib/odoo}
PROXY_MODE=${PROXY_MODE:-false}
WEBSITE_SERVER_URL=${WEBSITE_SERVER_URL:-""}
ODOO_WORKERS=${ODOO_WORKERS:-0}

# Variables de développement et débogage
DEV_MODE=${DEV_MODE:-false}
DEBUG_MODE=${DEBUG_MODE:-false}
TEST_ENABLE=${TEST_ENABLE:-false}
LOG_LEVEL=${LOG_LEVEL:-info}
LOG_HANDLER=${LOG_HANDLER:-":INFO"}

# Variables de performances
LIMIT_MEMORY_HARD=${LIMIT_MEMORY_HARD:-2684354560}
LIMIT_MEMORY_SOFT=${LIMIT_MEMORY_SOFT:-2147483648}

# Variables de sécurité
DISABLE_DATABASE_MANAGER=${DISABLE_DATABASE_MANAGER:-false}

# Créer le fichier de configuration Odoo
# Créer le fichier de configuration temporaire
echo "Création du fichier de configuration temporaire: $TMP_CONF"
cat > "$TMP_CONF" << EOF
[options]
; Base de données
db_host = $DB_HOST
db_port = $DB_PORT
db_user = $DB_USER
db_password = $DB_PASSWORD
admin_passwd = $ADMIN_PASSWORD

; Configuration de base
addons_path = $ADDONS_PATH
data_dir = $DATA_DIR
proxy_mode = $PROXY_MODE
workers = $ODOO_WORKERS

; Performances
limit_memory_hard = $LIMIT_MEMORY_HARD
limit_memory_soft = $LIMIT_MEMORY_SOFT

; Logging
EOF

# Configuration des logs
if [ "$DEBUG_MODE" = true ] || [ "$DEBUG_MODE" = "True" ]; then
    cat >> "$TMP_CONF" << EOF
log_level = debug
log_handler = [':DEBUG']
EOF
else
    cat >> "$TMP_CONF" << EOF
log_level = $LOG_LEVEL
log_handler = ['$LOG_HANDLER']
EOF
fi

# Mode développement
if [ "$DEV_MODE" = true ] || [ "$DEV_MODE" = "True" ]; then
    echo "dev_mode = all" >> "$TMP_CONF"
fi

# Tests
if [ "$TEST_ENABLE" = true ] || [ "$TEST_ENABLE" = "True" ]; then
    echo "test_enable = True" >> "$TMP_CONF"
fi

# Sécurité
if [ "$DISABLE_DATABASE_MANAGER" = true ] || [ "$DISABLE_DATABASE_MANAGER" = "True" ]; then
    echo "list_db = False" >> "$TMP_CONF"
else
    echo "list_db = True" >> "$TMP_CONF"
fi

# Website server URL si défini
if [ -n "$WEBSITE_SERVER_URL" ]; then
    echo "proxy_prefetch = True" >> "$TMP_CONF"
fi

# Déplacer le fichier temporaire vers l'emplacement final
echo "Déplacement du fichier de configuration vers: $ODOO_CONF"
# Si nous sommes root, nous pouvons directement copier
if [ "$(id -u)" = "0" ]; then
    mkdir -p "$ODOO_CONF_DIR" || true
    cp "$TMP_CONF" "$ODOO_CONF"
    chown odoo:odoo "$ODOO_CONF" || true
    chmod 644 "$ODOO_CONF" || true
else
    # Si nous ne sommes pas root, utilisons sudo si disponible
    if command -v sudo > /dev/null; then
        sudo mkdir -p "$ODOO_CONF_DIR" || true
        sudo cp "$TMP_CONF" "$ODOO_CONF"
        sudo chown odoo:odoo "$ODOO_CONF" || true
        sudo chmod 644 "$ODOO_CONF" || true
    else
        # Si sudo n'est pas disponible, utilisons un emplacement alternatif où nous avons les permissions
        ODOO_CONF="/var/lib/odoo/odoo.conf"
        mkdir -p "$(dirname "$ODOO_CONF")" || true
        cp "$TMP_CONF" "$ODOO_CONF"
        echo "Attention: Impossible d'écrire dans $ODOO_RC, utilisation de $ODOO_CONF à la place"
    fi
fi

# Afficher la configuration
echo "======== Configuration Odoo ========"
echo "Fichier de configuration: $ODOO_CONF"
echo ""
echo "Base de données:"
echo "- Host: $DB_HOST:$DB_PORT"
echo "- User: $DB_USER"
echo ""
echo "Odoo:"
echo "- Addons path: $ADDONS_PATH"
echo "- Data directory: $DATA_DIR"
echo "- Workers: $ODOO_WORKERS"
echo "- Proxy mode: $PROXY_MODE"
if [ -n "$WEBSITE_SERVER_URL" ]; then
    echo "- Website URL: $WEBSITE_SERVER_URL"
fi
echo ""
echo "Développement:"
echo "- Dev mode: $DEV_MODE"
echo "- Debug mode: $DEBUG_MODE"
echo "- Test enable: $TEST_ENABLE"
echo "- Log level: $LOG_LEVEL"
echo ""
echo "Performance:"
echo "- Memory limit (hard): $LIMIT_MEMORY_HARD"
echo "- Memory limit (soft): $LIMIT_MEMORY_SOFT"
echo ""
echo "Sécurité:"
echo "- Database manager disabled: $DISABLE_DATABASE_MANAGER"
echo "=================================="
echo "Contenu du fichier de configuration:"
echo "=================================="
cat "$ODOO_CONF"
echo "=================================="

# Exécuter Odoo avec le fichier de configuration
echo "Démarrage d'Odoo avec le fichier de configuration $ODOO_CONF"
exec odoo -c "$ODOO_CONF" "$@"
