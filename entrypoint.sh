#!/bin/bash

# Utiliser les valeurs par défaut si les variables d'environnement ne sont pas définies
ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin}
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-odoo}
DB_PASSWORD=${DB_PASSWORD:-odoo}

# Afficher les informations de configuration (sans les mots de passe)
echo "Configuration Odoo:"
echo "- DB_HOST: $DB_HOST"
echo "- DB_PORT: $DB_PORT"
echo "- DB_USER: $DB_USER"

# Exécuter la commande passée en argument, généralement "odoo"
exec "$@" 