#!/bin/bash

# Script de sauvegarde/restauration complète Odoo
# Usage: ./odoo_backup_restore.sh [backup|restore] [options...]

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction d'aide
show_help() {
    echo "Usage:"
    echo "  $0 backup <source_db_container> <source_odoo_container> <database_name> [backup_dir]"
    echo "  $0 restore <target_db_container> <target_odoo_container> <database_name> <backup_dir>"
    echo ""
    echo "Exemples:"
    echo "  # Sauvegarde"
    echo "  $0 backup odoo-db-1 odoo-web-1 multibikes /tmp/backup"
    echo ""
    echo "  # Restauration"
    echo "  $0 restore new-odoo-db-1 new-odoo-web-1 multibikes /tmp/backup"
    echo ""
    echo "Paramètres:"
    echo "  source_db_container   : Nom du conteneur PostgreSQL source"
    echo "  source_odoo_container : Nom du conteneur Odoo source"
    echo "  target_db_container   : Nom du conteneur PostgreSQL cible"
    echo "  target_odoo_container : Nom du conteneur Odoo cible"
    echo "  database_name         : Nom de la base de données"
    echo "  backup_dir           : Répertoire de sauvegarde (défaut: ./odoo_backup_TIMESTAMP)"
}

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

# Vérification des paramètres
check_container() {
    local container=$1
    if ! docker ps -q -f name="$container" | grep -q .; then
        error "Le conteneur '$container' n'existe pas ou n'est pas démarré"
    fi
}

# Fonction de sauvegarde
backup_odoo() {
    local db_container=$1
    local odoo_container=$2
    local database_name=$3
    local backup_dir=${4:-"./odoo_backup_$(date +%Y%m%d_%H%M%S)"}

    log "Début de la sauvegarde de '$database_name'"
    log "Conteneur DB: $db_container"
    log "Conteneur Odoo: $odoo_container"
    log "Répertoire de sauvegarde: $backup_dir"

    # Vérification des conteneurs
    check_container "$db_container"
    check_container "$odoo_container"

    # Création du répertoire de sauvegarde
    mkdir -p "$backup_dir"

    # 1. Sauvegarde de la base de données
    log "Sauvegarde de la base de données..."
    docker exec "$db_container" pg_dump -U odoo -d "$database_name" --no-owner --no-privileges > "$backup_dir/database.sql"
    if [ $? -eq 0 ]; then
        log "✅ Base de données sauvegardée: $backup_dir/database.sql"
    else
        error "❌ Échec de la sauvegarde de la base de données"
    fi

    # 2. Sauvegarde du filestore
    log "Sauvegarde du filestore..."
    docker exec "$odoo_container" test -d "/var/lib/odoo/filestore/$database_name"
    if [ $? -eq 0 ]; then
        docker exec "$odoo_container" tar -czf "/tmp/filestore_$database_name.tar.gz" -C "/var/lib/odoo/filestore" "$database_name"
        docker cp "$odoo_container:/tmp/filestore_$database_name.tar.gz" "$backup_dir/"
        docker exec "$odoo_container" rm "/tmp/filestore_$database_name.tar.gz"
        log "✅ Filestore sauvegardé: $backup_dir/filestore_$database_name.tar.gz"
    else
        warning "⚠️ Aucun filestore trouvé pour la base '$database_name'"
    fi

    # 3. Sauvegarde des métadonnées
    cat > "$backup_dir/backup_info.txt" << EOF
Sauvegarde Odoo - $(date)
================================
Base de données: $database_name
Conteneur DB source: $db_container
Conteneur Odoo source: $odoo_container
Date de sauvegarde: $(date)

Instructions de restauration:
$0 restore <target_db_container> <target_odoo_container> $database_name $backup_dir
EOF

    log "✅ Sauvegarde complète terminée dans: $backup_dir"
    log "📁 Fichiers créés:"
    ls -lh "$backup_dir"
}

# Fonction de restauration
restore_odoo() {
    local db_container=$1
    local odoo_container=$2
    local database_name=$3
    local backup_dir=$4

    if [ -z "$backup_dir" ]; then
        error "Le répertoire de sauvegarde est requis pour la restauration"
    fi

    log "Début de la restauration de '$database_name'"
    log "Conteneur DB cible: $db_container"
    log "Conteneur Odoo cible: $odoo_container"
    log "Répertoire de sauvegarde: $backup_dir"

    # Vérifications
    check_container "$db_container"
    check_container "$odoo_container"

    if [ ! -f "$backup_dir/database.sql" ]; then
        error "Fichier de sauvegarde manquant: $backup_dir/database.sql"
    fi

    # Confirmation
    echo -e "${YELLOW}⚠️ ATTENTION: Cette opération va:"
    echo "   - Supprimer la base '$database_name' si elle existe"
    echo "   - Restaurer les données depuis $backup_dir"
    echo -e "Voulez-vous continuer? (y/N)${NC}"
    read -r confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log "Restauration annulée"
        exit 0
    fi

    # 1. Suppression de l'ancienne base si elle existe
    log "Vérification de l'existence de la base..."
    if docker exec "$db_container" psql -U odoo -lqt | cut -d \| -f 1 | grep -qw "$database_name"; then
        log "Suppression de l'ancienne base '$database_name'..."
        docker exec "$db_container" psql -U odoo -c "DROP DATABASE IF EXISTS \"$database_name\";"
    fi

    # 2. Création de la nouvelle base
    log "Création de la nouvelle base '$database_name'..."
    docker exec "$db_container" psql -U odoo -c "CREATE DATABASE \"$database_name\" OWNER odoo;"

    # 3. Restauration de la base
    log "Restauration de la base de données..."
    docker exec -i "$db_container" psql -U odoo -d "$database_name" < "$backup_dir/database.sql"
    if [ $? -eq 0 ]; then
        log "✅ Base de données restaurée"
    else
        error "❌ Échec de la restauration de la base de données"
    fi

    # 4. Restauration du filestore
    if [ -f "$backup_dir/filestore_$database_name.tar.gz" ]; then
        log "Restauration du filestore..."
        
        # Copie de l'archive dans le conteneur
        docker cp "$backup_dir/filestore_$database_name.tar.gz" "$odoo_container:/tmp/"
        
        # Création du répertoire et extraction
        docker exec "$odoo_container" mkdir -p "/var/lib/odoo/filestore"
        docker exec "$odoo_container" tar -xzf "/tmp/filestore_$database_name.tar.gz" -C "/var/lib/odoo/filestore"
        docker exec "$odoo_container" chown -R odoo:odoo "/var/lib/odoo/filestore/$database_name"
        docker exec "$odoo_container" rm "/tmp/filestore_$database_name.tar.gz"
        
        log "✅ Filestore restauré"
    else
        warning "⚠️ Aucun filestore à restaurer"
    fi

    log "✅ Restauration complète terminée!"
    log "🚀 Vous pouvez maintenant redémarrer vos conteneurs Odoo"
    log "   docker-compose restart"
}

# Script principal
case "$1" in
    backup)
        if [ $# -lt 4 ]; then
            echo "Erreur: Paramètres manquants pour la sauvegarde"
            show_help
            exit 1
        fi
        backup_odoo "$2" "$3" "$4" "$5"
        ;;
    restore)
        if [ $# -lt 5 ]; then
            echo "Erreur: Paramètres manquants pour la restauration"
            show_help
            exit 1
        fi
        restore_odoo "$2" "$3" "$4" "$5"
        ;;
    *)
        show_help
        exit 1
        ;;
esac
