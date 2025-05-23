#!/bin/bash
set -e # Arrête le script si une commande échoue

# Utiliser les valeurs par défaut si les variables d'environnement ne sont pas définies
ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin}
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-odoo}
DB_PASSWORD=${DB_PASSWORD:-odoo}
ODOO_CONF=${ODOO_RC:-/etc/odoo/odoo.conf}

# Vérifier si odoo.conf existe, sinon le créer basiquement
if [ ! -f "$ODOO_CONF" ]; then
    echo "Fichier de configuration $ODOO_CONF non trouvé. Tentative de création d'un fichier basique."
    mkdir -p /etc/odoo
    touch "$ODOO_CONF"
    echo "[options]" > "$ODOO_CONF"
    echo "admin_passwd = $ADMIN_PASSWORD" >> "$ODOO_CONF"
    echo "db_host = $DB_HOST" >> "$ODOO_CONF"
    echo "db_port = $DB_PORT" >> "$ODOO_CONF"
    echo "db_user = $DB_USER" >> "$ODOO_CONF"
    echo "db_password = $DB_PASSWORD" >> "$ODOO_CONF"
    echo "addons_path = /mnt/extra-addons,/opt/odoo/odoo/addons,/opt/odoo/addons" # Adaptez aux chemins réels
    echo "data_dir = /var/lib/odoo" >> "$ODOO_CONF"
    # Vous pouvez ajouter d'autres options par défaut ici
fi

# Gérer les flags de développement
if [ -n "$ODOO_DEV_FEATURES" ]; then
    echo "Activation des fonctionnalités de dev Odoo: $ODOO_DEV_FEATURES"
    # Sépare les features si elles sont séparées par des virgules
    IFS=',' read -ra DEV_OPTS <<< "$ODOO_DEV_FEATURES"
    for opt in "${DEV_OPTS[@]}"; do
        # S'assurer de ne pas ajouter 'dev=' si opt est vide (au cas où la variable se termine par une virgule)
        if [ -n "$opt" ]; then
          odoo_params+=("--dev=$opt")
        fi
    done
fi

# Construire les arguments pour Odoo
declare -a odoo_params
odoo_params=("$@") # Prend les arguments passés à ce script (ex: ["--config=/etc/odoo/odoo.conf"])

# Ajouter le fichier de configuration s'il n'est pas déjà dans les arguments
config_found=false
for param in "${odoo_params[@]}"; do
    if [[ "$param" == *"--config"* ]] || [[ "$param" == *"-c"* ]]; then
        config_found=true
        break
    fi
done
if ! $config_found && [ -f "$ODOO_CONF" ]; then
    odoo_params+=("--config=$ODOO_CONF")
fi

# Afficher les informations de configuration (sans les mots de passe)
echo "Configuration Odoo (via entrypoint.sh):"
echo "- DB_HOST: $DB_HOST"
echo "- DB_PORT: $DB_PORT"
echo "- DB_USER: $DB_USER"
echo "- ODOO_CONF: $ODOO_CONF"
echo "Commande Odoo finale: odoo ${odoo_params[*]}"

# Exécuter Odoo avec les paramètres construits
# Le binaire 'odoo' est supposé être dans le PATH (généralement /usr/bin/odoo)
exec odoo "${odoo_params[@]}"