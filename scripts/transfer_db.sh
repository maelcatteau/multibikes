#!/bin/bash

# ============================================
# SCRIPT DE SAUVEGARDE/RESTAURATION ODOO v4.0
# ============================================
#
# 📋 DESCRIPTION :
# Version améliorée qui gère correctement la restauration sur volumes vierges
# en utilisant les outils CLI d'Odoo directement.
#
# ✨ NOUVEAUTÉS v4.0 :
# - Restauration directe via CLI Odoo (plus fiable)
# - Gestion automatique des volumes vierges
# - Noms de conteneurs simplifiés (odoo-prod, odoo-staging)
# - Commandes suivantes toujours affichées
#
# 🚀 EXEMPLES D'USAGE :
#
# 1️⃣ SAUVEGARDE :
# ./scripts/transfer_db.sh backup prod multibikes
# ./scripts/transfer_db.sh backup staging multibikes ~/backups
#
# 2️⃣ RESTAURATION :
# ./scripts/transfer_db.sh restore staging multibikes ~/backups/multibikes_backup_20250124.zip
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

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Fonction d'aide
show_help() {
    echo -e "${BLUE}============================================"
    echo "🔧 SCRIPT DE SAUVEGARDE/RESTAURATION ODOO v4.0"
    echo -e "============================================${NC}"
    echo ""
    echo "Usage:"
    echo "  $0 backup <env> <database_name> [backup_dir]"
    echo "  $0 restore <env> <database_name> <backup_file>"
    echo ""
    echo -e "${GREEN}Environnements disponibles :${NC}"
    echo "  prod     : Production (conteneur: odoo-prod)"
    echo "  staging  : Staging (conteneur: odoo-staging)"
    echo ""
    echo -e "${GREEN}📋 Exemples :${NC}"
    echo ""
    echo -e "${YELLOW}  # Sauvegarde production${NC}"
    echo "  $0 backup prod multibikes"
    echo ""
    echo -e "${YELLOW}  # Restauration staging${NC}"
    echo "  $0 restore staging multibikes ~/backups/multibikes_backup_20250124.tar.gz"
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

# Fonction pour obtenir les infos de connexion DB
get_db_info() {
    local container=$1
    local info_type=$2
    
    case "$info_type" in
        host)
            docker exec "$container" grep -E "^db_host\s*=" /etc/odoo/odoo.conf 2>/dev/null | cut -d'=' -f2 | tr -d ' ' | tr -d '\r' | tr -d '\n' || echo "db"
            ;;
        port)
            docker exec "$container" grep -E "^db_port\s*=" /etc/odoo/odoo.conf 2>/dev/null | cut -d'=' -f2 | tr -d ' ' | tr -d '\r' | tr -d '\n' || echo "5432"
            ;;
        user)
            docker exec "$container" grep -E "^db_user\s*=" /etc/odoo/odoo.conf 2>/dev/null | cut -d'=' -f2 | tr -d ' ' | tr -d '\r' | tr -d '\n' || echo "odoo"
            ;;
        password)
            docker exec "$container" grep -E "^db_password\s*=" /etc/odoo/odoo.conf 2>/dev/null | cut -d'=' -f2 | tr -d ' ' | tr -d '\r' | tr -d '\n' || echo "odoo"
            ;;
    esac
}

# Fonction pour afficher les prochaines commandes
show_next_commands() {
    local action=$1
    local env=$2
    local database_name=$3
    local backup_file=$4
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}📋 PROCHAINES COMMANDES UTILES :${NC}"
    echo ""
    
    if [[ "$action" == "backup" ]]; then
        echo -e "${YELLOW}  # Pour restaurer cette sauvegarde :${NC}"
        echo "  ./scripts/transfer_db.sh restore staging $database_name <chemin_vers_backup.tar.gz>"
        echo ""
        echo -e "${YELLOW}  # Pour voir les logs :${NC}"
        echo "  docker logs -f odoo-$env"
        
    elif [[ "$action" == "restore" ]]; then
        echo -e "${YELLOW}  # Si erreur 'Database not initialized' :${NC}"
        echo "  docker exec odoo-$env /usr/bin/odoo -d $database_name -i base --stop-after-init"
        echo "  docker restart odoo-$env"
        echo ""
        echo -e "${YELLOW}  # Pour mettre à jour tous les modules :${NC}"
        echo "  docker exec odoo-$env /usr/bin/odoo -d $database_name -u all --stop-after-init"
        echo "  docker restart odoo-$env"
        echo ""
        echo -e "${YELLOW}  # Pour voir les logs :${NC}"
        echo "  docker logs -f odoo-$env"
        echo ""
        echo -e "${YELLOW}  # Pour nettoyer complètement et recommencer :${NC}"
        echo "  ./scripts/clean_odoo_volumes.sh $env"
    fi
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Fonction de sauvegarde
backup_odoo() {
    local env=$1
    local database_name=$2
    local backup_dir_input=${3:-"./odoo_backup_$(date +%Y%m%d_%H%M%S)"}
    
    local container=$(get_container_name "$env")
    
    echo -e "${BLUE}"
    echo "============================================"
    echo "🚀 SAUVEGARDE ODOO v4.0"
    echo "============================================"
    echo -e "${NC}"
    
    log "📋 Configuration :"
    log "   Environnement   : $env"
    log "   Base de données : $database_name"
    log "   Conteneur       : $container"
    
    # Vérifier le conteneur
    if ! docker ps -q -f name="^${container}$" | grep -q .; then
        error "❌ Le conteneur '$container' n'existe pas ou n'est pas démarré"
    fi
    
    # Créer le répertoire de sauvegarde
    local backup_dir="$backup_dir_input"
    mkdir -p "$backup_dir" || error "Impossible de créer $backup_dir"
    backup_dir=$(cd "$backup_dir" && pwd)
    
    local backup_filename="${database_name}_backup_$(date +%Y%m%d_%H%M%S)"
    local backup_path="$backup_dir/$backup_filename"
    
    # Obtenir les infos DB
    local db_host=$(get_db_info "$container" "host")
    local db_port=$(get_db_info "$container" "port")
    local db_user=$(get_db_info "$container" "user")
    local db_password=$(get_db_info "$container" "password")
    
    log "🔍 Connexion DB : $db_user@$db_host:$db_port"
    
    # Créer un dump PostgreSQL
    log "💾 Création du dump PostgreSQL..."
    docker exec "$container" bash -c "PGPASSWORD='$db_password' pg_dump -h '$db_host' -p '$db_port' -U '$db_user' -d \"$database_name\" -f /tmp/${backup_filename}.sql" || error "Échec du dump PostgreSQL"
    
    # Créer une archive du filestore
    log "📦 Archivage du filestore..."
    docker exec "$container" bash -c "cd /var/lib/odoo && tar -czf /tmp/${backup_filename}_filestore.tar.gz filestore/$database_name 2>/dev/null || true"
    
    # Créer l'archive finale avec tar
    log "🗜️ Création de l'archive complète..."
    docker exec "$container" bash -c "cd /tmp && tar -czf ${backup_filename}.tar.gz ${backup_filename}.sql ${backup_filename}_filestore.tar.gz"
    
    # Copier l'archive
    docker cp "$container:/tmp/${backup_filename}.tar.gz" "$backup_path.tar.gz" || error "Échec de la copie"
    
    # Nettoyer
    docker exec "$container" bash -c "rm -f /tmp/${backup_filename}*" || true
    
    local backup_size=$(du -h "$backup_path.tar.gz" 2>/dev/null | cut -f1 || echo "?")
    
    echo ""
    echo -e "${GREEN}🎉 SAUVEGARDE TERMINÉE !${NC}"
    echo -e "${BLUE}============================================${NC}"
    log "📄 Fichier : $backup_path.tar.gz"
    log "📊 Taille : $backup_size"
    
    show_next_commands "backup" "$env" "$database_name"
}

# Fonction de restauration
restore_odoo() {
    local env=$1
    local database_name=$2
    local backup_file=$3
    
    local container=$(get_container_name "$env")
    
    echo -e "${BLUE}"
    echo "============================================"
    echo "🔄 RESTAURATION ODOO v4.0"
    echo "============================================"
    echo -e "${NC}"
    
    log "📋 Configuration :"
    log "   Environnement   : $env"
    log "   Base de données : $database_name"
    log "   Conteneur       : $container"
    log "   Backup          : $(basename "$backup_file")"
    
    # Vérifications
    if ! docker ps -q -f name="^${container}$" | grep -q .; then
        error "❌ Le conteneur '$container' n'existe pas ou n'est pas démarré"
    fi
    
    if [ ! -f "$backup_file" ]; then
        error "❌ Fichier de sauvegarde introuvable : $backup_file"
    fi
    
    # Confirmation
    echo -e "${RED}⚠️  ATTENTION ⚠️${NC}"
    echo -e "${YELLOW}Cette opération va :${NC}"
    echo "   🗑️  SUPPRIMER la base '$database_name' si elle existe"
    echo "   📦 RESTAURER depuis $(basename "$backup_file")"
    echo ""
    echo -e "${YELLOW}Continuer ? (tapez 'OUI')${NC}"
    read -r confirm
    if [[ "$confirm" != "OUI" ]]; then
        log "🛑 Restauration annulée"
        exit 0
    fi
    
    # Obtenir les infos DB
    local db_host=$(get_db_info "$container" "host")
    local db_port=$(get_db_info "$container" "port")
    local db_user=$(get_db_info "$container" "user")
    local db_password=$(get_db_info "$container" "password")
    
    # Arrêter Odoo
    log "🛑 Arrêt d'Odoo..."
    docker stop "$container" || error "Impossible d'arrêter le conteneur"
    
    # Copier le backup
    local temp_backup="/tmp/restore_$(date +%s).tar.gz"
    docker cp "$backup_file" "$container:$temp_backup" || error "Échec de la copie"
    
    # Démarrer temporairement le conteneur
    docker start "$container"
    sleep 5
    
    # Extraire l'archive
    log "📦 Extraction de l'archive..."
    docker exec "$container" bash -c "cd /tmp && tar -xzf $temp_backup" || error "Échec de l'extraction"
    
    # Identifier les fichiers
    local sql_file=$(docker exec "$container" bash -c "ls /tmp/*_backup_*.sql 2>/dev/null | head -1")
    local filestore_archive=$(docker exec "$container" bash -c "ls /tmp/*_filestore.tar.gz 2>/dev/null | head -1")
    
    if [ -z "$sql_file" ]; then
        error "❌ Fichier SQL introuvable dans l'archive"
    fi
    
        # Supprimer la base existante
    log "🗑️ Suppression de la base existante..."
    docker exec "$container" bash -c "PGPASSWORD='$db_password' psql -h '$db_host' -p '$db_port' -U '$db_user' -d postgres -c \"DROP DATABASE IF EXISTS \\\"$database_name\\\"\"" || true
    
    # Créer la nouvelle base
    log "🆕 Création de la nouvelle base..."
    docker exec "$container" bash -c "PGPASSWORD='$db_password' psql -h '$db_host' -p '$db_port' -U '$db_user' -d postgres -c \"CREATE DATABASE \\\"$database_name\\\" WITH OWNER \\\"$db_user\\\" ENCODING 'UTF8'\"" 
    
    # Restaurer le dump SQL
    log "💾 Restauration du dump SQL..."
    docker exec "$container" bash -c "PGPASSWORD='$db_password' psql -h '$db_host' -p '$db_port' -U '$db_user' -d \"$database_name\" -f $sql_file" || error "Échec de la restauration SQL"
    
    # Restaurer le filestore
    if [ -n "$filestore_archive" ]; then
        log "📁 Restauration du filestore..."
        docker exec "$container" bash -c "cd /var/lib/odoo && rm -rf filestore/$database_name && tar -xzf $filestore_archive"
    fi
    
    # Nettoyer
    docker exec "$container" bash -c "rm -f /tmp/*_backup_* /tmp/*_filestore.tar.gz $temp_backup" || true
    
    # Redémarrer Odoo
    log "🚀 Redémarrage d'Odoo..."
    docker restart "$container"
    
    log "⏳ Attente du démarrage (30 secondes)..."
    sleep 30
    
    echo ""
    echo -e "${GREEN}🎉 RESTAURATION TERMINÉE !${NC}"
    echo -e "${BLUE}============================================${NC}"
    log "✅ Base '$database_name' restaurée"
    
    show_next_commands "restore" "$env" "$database_name"
}

# Script principal
main() {
    case "$1" in
        backup)
            if [ $# -lt 3 ]; then
                error "❌ Paramètres manquants"
            fi
            backup_odoo "$2" "$3" "$4"
            ;;
        restore)
            if [ $# -lt 4 ]; then
                error "❌ Paramètres manquants"
            fi
            restore_odoo "$2" "$3" "$4"
            ;;
        *)
            show_help
            exit 1
            ;;
    esac
}

main "$@" 