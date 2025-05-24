#!/bin/bash

# ============================================
# SCRIPT DE CORRECTION D'INITIALISATION ODOO v2
# ============================================
#
# 📋 DESCRIPTION :
# Corrige les problèmes d'initialisation après une restauration
#
# 🚀 USAGE :
# ./scripts/fix_odoo_init.sh <env> <database_name>
#
# 📋 EXEMPLE :
# ./scripts/fix_odoo_init.sh staging multibikes
#
# ============================================

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

# Fonction pour obtenir le nom du conteneur
get_container_name() {
    local env=$1
    case "$env" in
        prod)
            echo "odoo-prod"
            ;;
        staging)
            echo "odoo-staging"
            ;;
        *)
            error "❌ Environnement invalide : $env. Utilisez 'prod' ou 'staging'"
            ;;
    esac
}

# Fonction pour afficher les prochaines commandes
show_next_commands() {
    local env=$1
    local database_name=$2
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}📋 PROCHAINES COMMANDES UTILES :${NC}"
    echo ""
    
    echo -e "${YELLOW}  # Pour voir les logs :${NC}"
    echo "  docker logs -f odoo-$env"
    echo ""
    echo -e "${YELLOW}  # Pour mettre à jour tous les modules :${NC}"
    echo "  docker exec odoo-$env /usr/bin/odoo -d $database_name -u all --stop-after-init"
    echo "  docker restart odoo-$env"
    echo ""
    echo -e "${YELLOW}  # Pour accéder à l'interface :${NC}"
    if [[ "$env" == "staging" ]]; then
        echo "  https://staging.mcommemedoc.fr"
    else
        echo "  https://mcommemedoc.fr"
    fi
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Vérification des paramètres
if [ $# -lt 2 ]; then
    echo -e "${RED}❌ Erreur : Paramètres manquants${NC}"
    echo ""
    echo "Usage: $0 <env> <database_name>"
    echo ""
    echo "Environnements disponibles : prod, staging"
    echo ""
    echo "Exemple:"
    echo "  $0 staging multibikes"
    exit 1
fi

env=$1
database_name=$2
container=$(get_container_name "$env")

echo -e "${BLUE}"
echo "============================================"
echo "🔧 CORRECTION D'INITIALISATION ODOO"
echo "============================================"
echo -e "${NC}"

log "📋 Configuration :"
log "   Environnement : $env"
log "   Conteneur : $container"
log "   Base de données : $database_name"

# Vérifier que le conteneur existe
if ! docker ps -q -f name="^${container}$" | grep -q .; then
    error "❌ Le conteneur '$container' n'existe pas ou n'est pas démarré"
fi

# Arrêter Odoo temporairement
log "🛑 Arrêt temporaire d'Odoo..."
docker stop "$container" || error "Impossible d'arrêter le conteneur"

# Forcer l'initialisation avec le module base
log "🔄 Initialisation forcée de la base avec le module 'base'..."
if docker run --rm \
    --network="$(docker inspect "$container" -f '{{range $key, $value := .NetworkSettings.Networks}}{{$key}}{{end}}' | head -1)" \
    --env-file <(docker inspect "$container" --format='{{range .Config.Env}}{{println .}}{{end}}') \
    -v "$(docker inspect "$container" --format='{{range .Mounts}}{{if eq .Destination "/var/lib/odoo"}}{{.Source}}{{end}}{{end}}'):/var/lib/odoo" \
    -v "$(docker inspect "$container" --format='{{range .Mounts}}{{if eq .Destination "/mnt/extra-addons"}}{{.Source}}{{end}}{{end}}'):/mnt/extra-addons" \
    "$(docker inspect "$container" --format='{{.Config.Image}}')" \
    /usr/bin/odoo -d \"$database_name\" -i base --stop-after-init --no-http; then
    
    log "✅ Initialisation terminée avec succès"
else
    error "❌ Échec de l'initialisation"
fi

# Redémarrer Odoo
log "🚀 Redémarrage d'Odoo..."
docker start "$container" || error "Impossible de redémarrer le conteneur"

# Attendre le démarrage
log "⏳ Attente du démarrage complet (20 secondes)..."
sleep 20

# Obtenir les paramètres de connexion à la base
db_host=$(docker exec "$container" grep -E "^db_host\s*=" /etc/odoo/odoo.conf 2>/dev/null | cut -d'=' -f2 | tr -d ' ' | tr -d '\r' | tr -d '\n' || echo "db")
db_port=$(docker exec "$container" grep -E "^db_port\s*=" /etc/odoo/odoo.conf 2>/dev/null | cut -d'=' -f2 | tr -d ' ' | tr -d '\r' | tr -d '\n' || echo "5432")
db_user=$(docker exec "$container" grep -E "^db_user\s*=" /etc/odoo/odoo.conf 2>/dev/null | cut -d'=' -f2 | tr -d ' ' | tr -d '\r' | tr -d '\n' || echo "odoo")
db_password=$(docker exec "$container" grep -E "^db_password\s*=" /etc/odoo/odoo.conf 2>/dev/null | cut -d'=' -f2 | tr -d ' ' | tr -d '\r' | tr -d '\n' || echo "odoo")

# Vérifier l'état
log "🔍 Vérification de l'état..."
docker exec "$container" python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(host='$db_host', port=$db_port, user='$db_user', password='$db_password', database=\"$database_name\")
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM ir_module_module WHERE state = %s', ('installed',))
    count = cur.fetchone()[0]
    print(f'✅ {count} modules installés')
    cur.close()
    conn.close()
except Exception as e:
    print(f'❌ Erreur: {e}')
"

echo ""
echo -e "${GREEN}🎉 CORRECTION TERMINÉE !${NC}"
echo -e "${BLUE}============================================${NC}"

show_next_commands "$env" "$database_name" 