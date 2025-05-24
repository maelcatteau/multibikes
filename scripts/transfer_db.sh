#!/bin/bash

# ============================================
# SCRIPT DE SAUVEGARDE/RESTAURATION ODOO
# ============================================
#
# 📋 DESCRIPTION :
# Ce script permet de sauvegarder et restaurer complètement une instance Odoo
# (base de données PostgreSQL + filestore) entre différents environnements.
#
# 🔧 PRÉREQUIS :
# - Docker et Docker Compose installés
# - Accès aux conteneurs Odoo et PostgreSQL
# - Permissions d'écriture dans le répertoire de sauvegarde
# - Utilisateur dans le groupe docker : sudo usermod -aG docker $USER
#
# 📦 CONTENU D'UNE SAUVEGARDE :
# ├── database.sql                    # Dump de la base PostgreSQL
# ├── filestore_DBNAME.tar.gz        # Fichiers uploadés (images, documents...)
# └── backup_info.txt                 # Métadonnées de la sauvegarde
#
# 🚀 EXEMPLES D'USAGE :
#
# 1️⃣ SAUVEGARDE :
# ./transfer_db.sh backup odoo-deployment-db-prod-1 odoo-prod multibikes
# ./transfer_db.sh backup odoo-deployment-db-prod-1 odoo-prod multibikes ~/backups
# ./transfer_db.sh backup my-db-container my-odoo-container ma_base ./sauvegarde
#
# 2️⃣ RESTAURATION :
# ./transfer_db.sh restore new-db-container new-odoo-container multibikes ~/backups/odoo_backup_20250124_101318
# ./transfer_db.sh restore staging-db staging-odoo test_db ./old_backup
#
# 3️⃣ CAS D'USAGE TYPIQUES :
#
# # Migration Prod → Test :
# ./transfer_db.sh backup odoo-prod-db odoo-prod multibikes ~/backup-prod
# ./transfer_db.sh restore odoo-test-db odoo-test multibikes ~/backup-prod/odoo_backup_XXXXX
#
# # Sauvegarde quotidienne :
# ./transfer_db.sh backup odoo-db odoo-web production ~/daily-backups
#
# # Restauration d'urgence :
# ./transfer_db.sh restore odoo-db odoo-web production ~/backups/odoo_backup_20250123_143022
#
# ⚠️ IMPORTANT :
# - Arrêtez Odoo pendant les opérations critiques : docker-compose stop odoo-web
# - Testez d'abord sur un environnement de test
# - Les restaurations EFFACENT la base existante !
#
# 🔍 TROUBLESHOOTING :
# - Permission denied → Vérifiez les droits : ls -la /path/to/backup
# - Container not found → Vérifiez : docker ps --format "table {{.Names}}"
# - Database error → Vérifiez : docker logs nom-conteneur-db
#
# 👤 AUTEUR : Assistant IA
# 📅 VERSION : 2.1 (2025-01-24) - Fix permissions
# ============================================

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'aide
show_help() {
    echo -e "${BLUE}============================================"
    echo "🔧 SCRIPT DE SAUVEGARDE/RESTAURATION ODOO"
    echo -e "============================================${NC}"
    echo ""
    echo "Usage:"
    echo "  $0 backup <source_db_container> <source_odoo_container> <database_name> [backup_dir]"
    echo "  $0 restore <target_db_container> <target_odoo_container> <database_name> <backup_dir>"
    echo ""
    echo -e "${GREEN}📋 Exemples concrets :${NC}"
    echo ""
    echo -e "${YELLOW}  # 1. Sauvegarde simple (répertoire auto-généré)${NC}"
    echo "  $0 backup odoo-deployment-db-prod-1 odoo-prod multibikes"
    echo ""
    echo -e "${YELLOW}  # 2. Sauvegarde dans un répertoire spécifique${NC}"
    echo "  $0 backup odoo-deployment-db-prod-1 odoo-prod multibikes ~/mes-sauvegardes"
    echo ""
    echo -e "${YELLOW}  # 3. Restauration${NC}"
    echo "  $0 restore odoo-test-db odoo-test multibikes ~/mes-sauvegardes/odoo_backup_20250124_101530"
    echo ""
    echo -e "${GREEN}📦 Paramètres :${NC}"
    echo "  source_db_container   : Nom du conteneur PostgreSQL source"
    echo "  source_odoo_container : Nom du conteneur Odoo source"
    echo "  database_name         : Nom de la base de données Odoo"
    echo "  backup_dir           : Répertoire de sauvegarde (optionnel pour backup)"
    echo ""
    echo -e "${BLUE}💡 Astuce : Utilisez 'docker ps' pour voir vos conteneurs${NC}"
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

# Création sécurisée d'un répertoire avec gestion des permissions
create_backup_dir() {
    local dir=$1
    
    # Si c'est un chemin absolu commençant par /, vérifier les permissions
    if [[ "$dir" = /* ]]; then
        local parent_dir=$(dirname "$dir")
        if [ ! -w "$parent_dir" ]; then
            error "❌ Pas de permission d'écriture dans '$parent_dir'. Essayez :\n   - Un répertoire dans votre home : ~/backups\n   - Avec sudo : sudo $0 ...\n   - Créer d'abord : sudo mkdir -p '$dir' && sudo chown $USER:$USER '$dir'"
        fi
    fi
    
    # Tentative de création
    if ! mkdir -p "$dir" 2>/dev/null; then
        # Si échec, essayer dans le répertoire courant
        local fallback_dir="./odoo_backup_$(date +%Y%m%d_%H%M%S)"
        warning "⚠️ Impossible de créer '$dir'"
        log "🔄 Utilisation du répertoire de secours : $fallback_dir"
        if ! mkdir -p "$fallback_dir"; then
            error "❌ Impossible de créer le répertoire de secours"
        fi
        echo "$fallback_dir"
    else
        # Convertir en chemin absolu
        echo "$(cd "$dir" && pwd)"
    fi
}

# Vérification des paramètres
check_container() {
    local container=$1
    log "🔍 Vérification du conteneur '$container'..."
    
    if ! docker ps -q -f name="^${container}$" | grep -q .; then
        error "❌ Le conteneur '$container' n'existe pas ou n'est pas démarré.\n\n💡 Conteneurs disponibles :\n$(docker ps --format 'table {{.Names}}\t{{.Status}}')"
    fi
    log "✅ Conteneur '$container' trouvé et actif"
}

# Vérification de l'existence de la base
check_database() {
    local db_container=$1
    local database_name=$2
    
    log "🔍 Vérification de la base de données '$database_name'..."
    
    if ! docker exec "$db_container" psql -U odoo -lqt | cut -d \| -f 1 | grep -qw "$database_name"; then
        error "❌ La base de données '$database_name' n'existe pas.\n\n💡 Bases disponibles :\n$(docker exec "$db_container" psql -U odoo -l | grep -E '^\s+\w+' | awk '{print $1}')"
    fi
    log "✅ Base de données '$database_name' trouvée"
}

# Fonction pour sauvegarder la base de données
backup_database() {
    local db_container=$1
    local database_name=$2
    local backup_dir=$3
    
    log "💾 Sauvegarde de la base de données..."
    
    # Méthode 1 : Essayer avec docker exec directement dans un fichier
    local temp_file="/tmp/database_backup_$(date +%s).sql"
    
    if docker exec "$db_container" bash -c "pg_dump -U odoo -d '$database_name' --no-owner --no-privileges > '$temp_file'"; then
        # Copier le fichier depuis le conteneur
        if docker cp "$db_container:$temp_file" "$backup_dir/database.sql"; then
            # Nettoyer le fichier temporaire
            docker exec "$db_container" rm -f "$temp_file" 2>/dev/null || true
            local db_size=$(du -h "$backup_dir/database.sql" 2>/dev/null | cut -f1 || echo "?")
            log "✅ Base de données sauvegardée ($db_size) : database.sql"
            return 0
        else
            docker exec "$db_container" rm -f "$temp_file" 2>/dev/null || true
        fi
    fi
    
    # Méthode 2 : Fallback avec redirection et gestion des permissions
    log "🔄 Tentative avec méthode alternative..."
    
    if docker exec "$db_container" pg_dump -U odoo -d "$database_name" --no-owner --no-privileges | tee "$backup_dir/database.sql" > /dev/null; then
        local db_size=$(du -h "$backup_dir/database.sql" 2>/dev/null | cut -f1 || echo "?")
        log "✅ Base de données sauvegardée ($db_size) : database.sql"
        return 0
    fi
    
    error "❌ Échec de la sauvegarde de la base de données"
}

# Fonction de sauvegarde
backup_odoo() {
    local db_container=$1
    local odoo_container=$2
    local database_name=$3
    local backup_dir_input=${4:-"./odoo_backup_$(date +%Y%m%d_%H%M%S)"}

    echo -e "${BLUE}"
    echo "============================================"
    echo "🚀 DÉBUT DE LA SAUVEGARDE ODOO"
    echo "============================================"
    echo -e "${NC}"
    
    log "📋 Configuration :"
    log "   Base de données : $database_name"
    log "   Conteneur DB    : $db_container"
    log "   Conteneur Odoo  : $odoo_container"
    log "   Répertoire      : $backup_dir_input"

    # Vérifications préalables
    check_container "$db_container"
    check_container "$odoo_container"
    check_database "$db_container" "$database_name"

    # Création sécurisée du répertoire
    local backup_dir=$(create_backup_dir "$backup_dir_input")
    log "📁 Répertoire de sauvegarde : $backup_dir"
    
    # Vérifier les permissions sur le répertoire final
    if [ ! -w "$backup_dir" ]; then
        error "❌ Pas de permission d'écriture dans '$backup_dir'"
    fi

    # 1. Sauvegarde de la base de données
    backup_database "$db_container" "$database_name" "$backup_dir"

    # 2. Sauvegarde du filestore
    log "📎 Sauvegarde du filestore..."
    if docker exec "$odoo_container" test -d "/var/lib/odoo/filestore/$database_name" 2>/dev/null; then
        local temp_archive="/tmp/filestore_${database_name}_$(date +%s).tar.gz"
        
        if docker exec "$odoo_container" tar -czf "$temp_archive" -C "/var/lib/odoo/filestore" "$database_name" 2>/dev/null; then
            if docker cp "$odoo_container:$temp_archive" "$backup_dir/filestore_$database_name.tar.gz"; then
                docker exec "$odoo_container" rm -f "$temp_archive" 2>/dev/null || true
                local fs_size=$(du -h "$backup_dir/filestore_$database_name.tar.gz" 2>/dev/null | cut -f1 || echo "?")
                log "✅ Filestore sauvegardé ($fs_size) : filestore_$database_name.tar.gz"
            else
                docker exec "$odoo_container" rm -f "$temp_archive" 2>/dev/null || true
                warning "⚠️ Échec de la copie du filestore"
            fi
        else
            warning "⚠️ Échec de la création de l'archive filestore"
        fi
    else
        warning "⚠️ Aucun filestore trouvé pour la base '$database_name'"
        echo "# Pas de filestore trouvé" > "$backup_dir/no_filestore.txt"
    fi

    # 3. Sauvegarde des métadonnées
    cat > "$backup_dir/backup_info.txt" << EOF
============================================
SAUVEGARDE ODOO - $(date)
============================================
Base de données    : $database_name
Conteneur DB source: $db_container
Conteneur Odoo src : $odoo_container
Date sauvegarde    : $(date)
Utilisateur        : $(whoami)
Serveur            : $(hostname)

CONTENU :
$(ls -lh "$backup_dir" 2>/dev/null | tail -n +2 || echo "Erreur listage")

RESTAURATION :
$0 restore <target_db_container> <target_odoo_container> $database_name $backup_dir

EXEMPLE :
$0 restore new-odoo-db new-odoo-web $database_name $backup_dir
============================================
EOF

    echo ""
    echo -e "${GREEN}🎉 SAUVEGARDE TERMINÉE AVEC SUCCÈS !${NC}"
    echo -e "${BLUE}============================================${NC}"
    log "📁 Répertoire : $backup_dir"
    log "📊 Contenu :"
    ls -lh "$backup_dir" 2>/dev/null | tail -n +2 | while read line; do
        echo "     $line"
    done || echo "     Erreur lors du listage"
    echo ""
    log "💡 Pour restaurer :"
    echo "    $0 restore <target_db> <target_odoo> $database_name $backup_dir"
}

# Fonction de restauration
restore_odoo() {
    local db_container=$1
    local odoo_container=$2
    local database_name=$3
    local backup_dir=$4

    if [ -z "$backup_dir" ]; then
        error "❌ Le répertoire de sauvegarde est requis pour la restauration"
    fi

    echo -e "${BLUE}"
    echo "============================================"
    echo "🔄 DÉBUT DE LA RESTAURATION ODOO"
    echo "============================================"
    echo -e "${NC}"
    
    log "📋 Configuration :"
    log "   Base de données : $database_name"
    log "   Conteneur DB    : $db_container"
    log "   Conteneur Odoo  : $odoo_container"
    log "   Source backup   : $backup_dir"

    # Vérifications
    check_container "$db_container"
    check_container "$odoo_container"

    if [ ! -f "$backup_dir/database.sql" ]; then
        error "❌ Fichier de sauvegarde manquant : $backup_dir/database.sql\n\n💡 Contenu du répertoire :\n$(ls -la "$backup_dir" 2>/dev/null || echo "Répertoire inexistant")"
    fi

    # Affichage des informations de sauvegarde
    if [ -f "$backup_dir/backup_info.txt" ]; then
        echo -e "${BLUE}📋 Informations de la sauvegarde :${NC}"
        head -10 "$backup_dir/backup_info.txt"
        echo ""
    fi

    # Confirmation
    echo -e "${RED}⚠️ ⚠️ ⚠️  ATTENTION  ⚠️ ⚠️ ⚠️${NC}"
    echo -e "${YELLOW}Cette opération va :${NC}"
    echo "   🗑️  SUPPRIMER la base '$database_name' si elle existe"
    echo "   📦 RESTAURER les données depuis $backup_dir"
    echo "   🔄 REMPLACER tout le contenu existant"
    echo ""
    echo -e "${YELLOW}Voulez-vous continuer ? (tapez 'OUI' en majuscules)${NC}"
    read -r confirm
    if [[ "$confirm" != "OUI" ]]; then
        log "🛑 Restauration annulée par l'utilisateur"
        exit 0
    fi

       # 1. Suppression de l'ancienne base si elle existe
    log "🔍 Vérification de l'existence de la base..."
    if docker exec "$db_container" psql -U odoo -lqt | cut -d \| -f 1 | grep -qw "$database_name" 2>/dev/null; then
        log "🛑 Arrêt temporaire d'Odoo pour libérer les connexions..."
        docker stop "$odoo_container" >/dev/null 2>&1 || true
        
        log "🔌 Fermeture des connexions actives vers '$database_name'..."
        docker exec "$db_container" psql -U odoo -d postgres -c "
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '$database_name'
              AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true
        
        log "🗑️ Suppression de l'ancienne base '$database_name'..."
        if docker exec "$db_container" psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS \"$database_name\";" >/dev/null 2>&1; then
            log "✅ Ancienne base supprimée"
        else
            error "❌ Impossible de supprimer la base '$database_name'. Vérifiez qu'aucune connexion n'est active."
        fi
    else
        log "ℹ️ Aucune base existante à supprimer"
        # Arrêter Odoo quand même pour éviter les conflits pendant la restauration
        log "🛑 Arrêt temporaire d'Odoo..."
        docker stop "$odoo_container" >/dev/null 2>&1 || true
    fi


  # 2. Création de la nouvelle base
    log "🔨 Création de la nouvelle base '$database_name'..."
    if docker exec "$db_container" psql -U odoo -d postgres -c "CREATE DATABASE \"$database_name\" OWNER odoo;" >/dev/null 2>&1; then
        log "✅ Nouvelle base créée"
    else
        log "❌ ERREUR: Impossible de créer la base '$database_name'"
        exit 1
    fi

    # 3. Restauration de la base
    log "💾 Restauration de la base de données..."
    
    # Copier le fichier SQL dans le conteneur et l'exécuter
    local temp_sql="/tmp/restore_$(date +%s).sql"
    if docker cp "$backup_dir/database.sql" "$db_container:$temp_sql"; then
        if docker exec "$db_container" psql -U odoo -d "$database_name" -f "$temp_sql" >/dev/null 2>&1; then
            docker exec "$db_container" rm -f "$temp_sql" 2>/dev/null || true
            log "✅ Base de données restaurée"
        else
            docker exec "$db_container" rm -f "$temp_sql" 2>/dev/null || true
            error "❌ Échec de la restauration de la base de données"
        fi
    else
        error "❌ Échec de la copie du fichier SQL vers le conteneur"
    fi

    # Après la restauration de la base, AVANT le filestore :
    log "🔄 Redémarrage d'Odoo..."
    if docker start "$odoo_container" >/dev/null 2>&1; then
        log "⏳ Attente du démarrage complet d'Odoo..."
        sleep 15  # Laissez le temps à Odoo de démarrer
        log "✅ Odoo redémarré"
    else
        log "❌ ERREUR: Impossible de redémarrer Odoo"
        exit 1
    fi

    # 4. Restauration du filestore
    if [ -f "$backup_dir/filestore_$database_name.tar.gz" ]; then
        log "📎 Restauration du filestore..."
        
        local temp_archive="/tmp/restore_filestore_$(date +%s).tar.gz"
        
        # Copie de l'archive dans le conteneur (AVEC debug)
        log "🔄 Copie du filestore vers le conteneur..."
        if docker cp "$backup_dir/filestore_$database_name.tar.gz" "$odoo_container:$temp_archive"; then
            log "✅ Copie réussie"
            
            # Suppression de l'ancien filestore s'il existe
            log "🗑️ Nettoyage de l'ancien filestore..."
            docker exec "$odoo_container" rm -rf "/var/lib/odoo/filestore/$database_name" || true
            
            # Création du répertoire et extraction
            log "📁 Création du répertoire filestore..."
            docker exec "$odoo_container" mkdir -p "/var/lib/odoo/filestore"
            
            log "📦 Extraction du filestore..."
            if docker exec "$odoo_container" tar -xzf "$temp_archive" -C "/var/lib/odoo/filestore"; then
                log "🔐 Application des permissions..."
                docker exec "$odoo_container" chown -R odoo:odoo "/var/lib/odoo/filestore/$database_name" || true
                docker exec "$odoo_container" rm -f "$temp_archive" || true
                log "✅ Filestore restauré"
            else
                log "❌ ERREUR: Échec de l'extraction du filestore"
                docker exec "$odoo_container" rm -f "$temp_archive" || true
                exit 1
            fi
        else
            log "❌ ERREUR: Impossible de copier le filestore vers le conteneur"
            exit 1
        fi
    else
        warning "⚠️ Aucun filestore à restaurer"
    fi

    echo ""
    echo -e "${GREEN}🎉 RESTAURATION TERMINÉE AVEC SUCCÈS !${NC}"
    echo -e "${BLUE}============================================${NC}"
    log "✅ Base '$database_name' restaurée"
    log "🚀 Actions recommandées :"
    echo "    1. Redémarrer Odoo : docker-compose restart"
    echo "    2. Vider le cache navigateur (Ctrl+F5)"
    echo "    3. Vérifier les logs : docker logs $odoo_container"
    echo ""
    log "🌐 Accès : http://votre-domaine ou http://localhost:8069"
    echo ""
}

# Vérification des prérequis
check_prerequisites() {
    if ! command -v docker &> /dev/null; then
        error "❌ Docker n'est pas installé ou pas dans le PATH"
    fi
    
    if ! docker ps &> /dev/null; then
        error "❌ Impossible d'accéder à Docker. Essayez :\n   sudo usermod -aG docker $USER\n   newgrp docker"
    fi
}

# Script principal
main() {
    check_prerequisites
    
    case "$1" in
        backup)
            if [ $# -lt 4 ]; then
                echo -e "${RED}❌ Erreur : Paramètres manquants pour la sauvegarde${NC}"
                echo ""
                show_help
                exit 1
            fi
            backup_odoo "$2" "$3" "$4" "$5"
            ;;
        restore)
            if [ $# -lt 5 ]; then
                echo -e "${RED}❌ Erreur : Paramètres manquants pour la restauration${NC}"
                echo ""
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
}

# Exécution du script
main "$@"
