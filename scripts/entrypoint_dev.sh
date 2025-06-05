#!/bin/bash
set -e

# Vérifier et corriger les permissions si nécessaire
if [ ! -w "/var/lib/odoo" ]; then
    echo "Correction des permissions pour /var/lib/odoo"
    sudo chown -R odoo:odoo /var/lib/odoo
    sudo chmod -R 755 /var/lib/odoo
fi

# Créer les répertoires nécessaires
mkdir -p /var/lib/odoo/sessions /var/lib/odoo/filestore

# Configuration par défaut
TMP_CONF=${TMP_CONF:-/tmp/odoo_dev.conf}
ODOO_CONF=${ODOO_CONF:-/etc/odoo/odoo.conf}

# Variables de base de données
DB_HOST=${PGHOST:-db-dev}
DB_PORT=${PGPORT:-5432}
DB_USER=${PGUSER:-odoo}
DB_PASSWORD=${PGPASSWORD:-odoo}

# Variables de configuration Odoo
ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin}
ADDONS_PATH=${ADDONS_PATH:-/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons}
DATA_DIR=${DATA_DIR:-/var/lib/odoo}
PROXY_MODE=${PROXY_MODE:-False}
WEBSITE_SERVER_URL=${WEBSITE_SERVER_URL:-""}
ODOO_WORKERS=${ODOO_WORKERS:-0}

# Variables de développement et débogage (valeurs par défaut pour dev)
DEV_MODE=${DEV_MODE:-true}
DEBUG_MODE=${DEBUG_MODE:-true}
TEST_ENABLE=${TEST_ENABLE:-true}
LOG_LEVEL=${LOG_LEVEL:-debug}

# Variables de performances (réduites pour le dev)
LIMIT_MEMORY_HARD=${LIMIT_MEMORY_HARD:-1073741824}  # 1GB pour dev
LIMIT_MEMORY_SOFT=${LIMIT_MEMORY_SOFT:-805306368}   # 768MB pour dev

# Variables de sécurité (plus permissives pour le dev)
DISABLE_DATABASE_MANAGER=${DISABLE_DATABASE_MANAGER:-false}

# Variables WebSockets
GEVENT_PORT=${GEVENT_PORT:-8072}
WEBSOCKET_RATE_LIMIT_BURST=${WEBSOCKET_RATE_LIMIT_BURST:-10}
WEBSOCKET_RATE_LIMIT_DELAY=${WEBSOCKET_RATE_LIMIT_DELAY:-0.2}

# Variables de cron pour dev
MAX_CRON_THREADS=${MAX_CRON_THREADS:-1}

# Fonction pour convertir les valeurs booléennes
convert_bool() {
    local value="$1"
    if [ "$value" = "true" ] || [ "$value" = "True" ] || [ "$value" = "1" ]; then
        echo "True"
    else
        echo "False"
    fi
}

# Créer le fichier de configuration temporaire
echo "Création du fichier de configuration temporaire: $TMP_CONF"
cat > "$TMP_CONF" << EOF
[options]
; Base de données
db_host = db-dev
db_port = 5432
db_user = odoo
db_password = odoo
admin_passwd = odoo-multibikes-dev

; Configuration de base
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
data_dir = /var/lib/odoo
proxy_mode = True
workers = 0

; Mode développement Odoo 18
dev_mode = reload,qweb,werkzeug,xml
without_demo = False
test_enable = False

; Performances
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
max_cron_threads = 1

; WebSockets
gevent_port = 8072

; Logging
log_level = debug
log_handler = :DEBUG

; Sécurité
list_db = True
EOF

# Website server URL si défini
if [ -n "$WEBSITE_SERVER_URL" ]; then
    echo "proxy_prefetch = True" >> "$TMP_CONF"
fi

# Configuration spécifique pour forcer le mode développement
if [ "$DEV_MODE" = "true" ] || [ "$DEV_MODE" = "True" ]; then
    cat >> "$TMP_CONF" << EOF

; Configuration supplémentaire pour le mode développement
server_wide_modules = base,web
EOF
fi

# Assurer que le répertoire de destination existe
mkdir -p "$(dirname "$ODOO_CONF")"

# Déplacer le fichier de configuration vers /etc/odoo
echo "Déplacement du fichier de configuration vers: $ODOO_CONF"
cp "$TMP_CONF" "$ODOO_CONF"
chmod 644 "$ODOO_CONF"

# Afficher la configuration
echo "======== Configuration Odoo Dev ========"
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

# Attendre que la base de données soit prête
echo "Vérification de la disponibilité de la base de données..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" 2>/dev/null; do
    echo "En attente de la base de données..."
    sleep 2
done
echo "Base de données disponible!"

# Exécuter Odoo avec le fichier de configuration
echo "Démarrage d'Odoo Dev avec le fichier de configuration $ODOO_CONF"

# Filtrer les arguments pour éviter la duplication
args=()
for arg in "$@"; do
    case "$arg" in
        "odoo"|"--config="*|"-c="*)
            # Ignorer ces arguments pour éviter les doublons
            ;;
        *)
            args+=("$arg")
            ;;
    esac
done

echo "🚀 Démarrage Odoo 18 en mode développement complet..."

if [ ${#args[@]} -eq 0 ]; then
    # CONFIGURATION CORRECTE pour Odoo 18
    exec odoo -c "$ODOO_CONF" \
        --dev=reload,qweb,werkzeug,xml \
        --log-level=debug \
        --limit-time-cpu=3600 \
        --limit-time-real=7200 \
        --load=base,web
else
    exec odoo -c "$ODOO_CONF" \
        --dev=reload,qweb,werkzeug,xml \
        "${args[@]}"
fi
