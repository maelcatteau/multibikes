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
TMP_CONF=${TMP_CONF:-/tmp/odoo_prod.conf}
ODOO_CONF=${ODOO_CONF:-/etc/odoo/odoo.conf}

# Variables de base de données
DB_HOST=${PGHOST:-db-prod}
DB_PORT=${PGPORT:-5432}
DB_USER=${PGUSER:-odoo}
DB_PASSWORD=${PGPASSWORD:-odoo}
DB_MAXCONN=${DB_MAXCONN:-64}

# Variables de configuration Odoo
ADMIN_PASSWORD=${ADMIN_PASSWORD:-$(openssl rand -base64 32)}
ADDONS_PATH=${ADDONS_PATH:-/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons}
DATA_DIR=${DATA_DIR:-/var/lib/odoo}
PROXY_MODE=${PROXY_MODE:-true}
WEBSITE_SERVER_URL=${WEBSITE_SERVER_URL:-""}
ODOO_WORKERS=${ODOO_WORKERS:-4}

# Variables de développement et débogage (valeurs pour production)
DEV_MODE=${DEV_MODE:-false}
DEBUG_MODE=${DEBUG_MODE:-false}
TEST_ENABLE=${TEST_ENABLE:-false}
LOG_LEVEL=${LOG_LEVEL:-warn}
LOG_HANDLER=${LOG_HANDLER:-":WARN"}

# Variables de performances (optimisées pour production)
LIMIT_MEMORY_HARD=${LIMIT_MEMORY_HARD:-2684354560}  # 2.5GB
LIMIT_MEMORY_SOFT=${LIMIT_MEMORY_SOFT:-2147483648}   # 2GB

# Variables de sécurité (strictes pour production)
DISABLE_DATABASE_MANAGER=${DISABLE_DATABASE_MANAGER:-true}

# Variables WebSockets (optimisées pour production)
GEVENT_PORT=${GEVENT_PORT:-8072}
WEBSOCKET_RATE_LIMIT_BURST=${WEBSOCKET_RATE_LIMIT_BURST:-5}
WEBSOCKET_RATE_LIMIT_DELAY=${WEBSOCKET_RATE_LIMIT_DELAY:-0.5}

# Variables de cron pour production
MAX_CRON_THREADS=${MAX_CRON_THREADS:-2}

# Créer le fichier de configuration temporaire
echo "Création du fichier de configuration de production: $TMP_CONF"
cat > "$TMP_CONF" << EOF
[options]
; Base de données
db_host = $DB_HOST
db_port = $DB_PORT
db_user = $DB_USER
db_password = $DB_PASSWORD
db_maxconn = $DB_MAXCONN
admin_passwd = $ADMIN_PASSWORD

; Configuration de base
addons_path = $ADDONS_PATH
data_dir = $DATA_DIR
proxy_mode = $PROXY_MODE
workers = $ODOO_WORKERS

; Performances
limit_memory_hard = $LIMIT_MEMORY_HARD
limit_memory_soft = $LIMIT_MEMORY_SOFT
max_cron_threads = $MAX_CRON_THREADS

; WebSockets
gevent_port = $GEVENT_PORT
websocket_rate_limit_burst = $WEBSOCKET_RATE_LIMIT_BURST
websocket_rate_limit_delay = $WEBSOCKET_RATE_LIMIT_DELAY

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

# Mode développement (désactivé en prod)
if [ "$DEV_MODE" = true ] || [ "$DEV_MODE" = "True" ]; then
    echo "dev_mode = all" >> "$TMP_CONF"
fi

# Tests (désactivés en prod)
if [ "$TEST_ENABLE" = true ] || [ "$TEST_ENABLE" = "True" ]; then
    echo "test_enable = True" >> "$TMP_CONF"
fi

# Sécurité (strict en prod)
if [ "$DISABLE_DATABASE_MANAGER" = true ] || [ "$DISABLE_DATABASE_MANAGER" = "True" ]; then
    echo "list_db = False" >> "$TMP_CONF"
else
    echo "list_db = True" >> "$TMP_CONF"
fi

# Website server URL si défini
if [ -n "$WEBSITE_SERVER_URL" ]; then
    echo "proxy_prefetch = True" >> "$TMP_CONF"
fi

# Configuration spécifique à la production
echo "auto_reload = False" >> "$TMP_CONF"
echo "without_demo = True" >> "$TMP_CONF"

# Déplacer le fichier de configuration vers /etc/odoo
echo "Déplacement du fichier de configuration vers: $ODOO_CONF"
cp "$TMP_CONF" "$ODOO_CONF"
chmod 644 "$ODOO_CONF"

# Afficher la configuration
echo "======== Configuration Odoo Production ========"
echo "Fichier de configuration: $ODOO_CONF"
echo ""
echo "Base de données:"
echo "- Host: $DB_HOST:$DB_PORT"
echo "- User: $DB_USER"
echo "- Max connections: $DB_MAXCONN"
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
echo "Production:"
echo "- Dev mode: $DEV_MODE"
echo "- Debug mode: $DEBUG_MODE"
echo "- Test enable: $TEST_ENABLE"
echo "- Log level: $LOG_LEVEL"
echo "- Demo data: disabled"
echo ""
echo "Performance:"
echo "- Memory limit (hard): $LIMIT_MEMORY_HARD"
echo "- Memory limit (soft): $LIMIT_MEMORY_SOFT"
echo "- Cron threads: $MAX_CRON_THREADS"
echo ""
echo "Sécurité:"
echo "- Disable Database Manager: $DISABLE_DATABASE_MANAGER"
echo ""
echo "WebSockets:"
echo "- Port: $GEVENT_PORT"
echo "- Rate limit burst: $WEBSOCKET_RATE_LIMIT_BURST"
echo "- Rate limit delay: $WEBSOCKET_RATE_LIMIT_DELAY"
echo "=================================="
echo "Contenu du fichier de configuration:"
echo "=================================="
cat "$ODOO_CONF"
echo "=================================="

# Exécuter Odoo avec le fichier de configuration
echo "Démarrage d'Odoo Production avec le fichier de configuration $ODOO_CONF"

# Filtrer les arguments pour éviter la duplication
args=()
for arg in "$@"; do
    if [ "$arg" != "odoo" ] && [ "$arg" != "--config=/etc/odoo/odoo.conf" ]; then
        args+=("$arg")
    fi
done

# Si aucun argument spécifique n'est fourni, utiliser la configuration par défaut
if [ ${#args[@]} -eq 0 ]; then
    exec odoo -c "$ODOO_CONF"
else
    exec odoo -c "$ODOO_CONF" "${args[@]}"
fi
