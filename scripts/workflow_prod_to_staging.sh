#!/bin/bash

# ============================================
# WORKFLOW COMPLET : PRODUCTION → STAGING
# ============================================
#
# 📋 DESCRIPTION :
# Script interactif pour copier la production vers le staging
#
# 🚀 USAGE :
# ./scripts/workflow_prod_to_staging.sh
#
# ============================================

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════╗"
echo "║   WORKFLOW : COPIE PRODUCTION VERS STAGING       ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Vérifier que les conteneurs existent
info "🔍 Vérification des conteneurs..."

if ! docker ps -q -f name="^odoo-prod$" | grep -q .; then
    error "❌ Le conteneur 'odoo-prod' n'est pas actif"
fi

if ! docker ps -q -f name="^odoo-staging$" | grep -q .; then
    error "❌ Le conteneur 'odoo-staging' n'est pas actif"
fi

log "✅ Conteneurs trouvés"

# Options du workflow
echo ""
echo -e "${YELLOW}Que voulez-vous faire ?${NC}"
echo ""
echo "  1️⃣  Copie simple (sauvegarde prod → restauration staging)"
echo "  2️⃣  Copie avec nettoyage complet (volumes staging vierges)"
echo "  3️⃣  Voir les commandes manuelles"
echo ""
read -p "Votre choix (1/2/3) : " choice

case "$choice" in
    1)
        # Copie simple
        echo ""
        echo -e "${BLUE}═══ COPIE SIMPLE ═══${NC}"
        echo ""
        
        # Nom de la base
        read -p "Nom de la base de données [multibikes] : " db_name
        db_name=${db_name:-multibikes}
        
        # Répertoire de sauvegarde
        backup_dir="./backup_prod_$(date +%Y%m%d_%H%M%S)"
        
        # Étape 1 : Sauvegarde
        echo ""
        info "📦 Étape 1/2 : Sauvegarde de la production..."
        ./scripts/transfer_db.sh backup prod "$db_name" "$backup_dir"
        
        # Trouver le fichier de sauvegarde
        backup_file=$(ls -t "$backup_dir"/*.tar.gz 2>/dev/null | head -1)
        
        if [ -z "$backup_file" ]; then
            error "❌ Aucun fichier de sauvegarde trouvé"
        fi
        
        # Étape 2 : Restauration
        echo ""
        info "🔄 Étape 2/2 : Restauration sur staging..."
        ./scripts/transfer_db.sh restore staging "$db_name" "$backup_file"
        
        echo ""
        echo -e "${GREEN}✅ COPIE TERMINÉE !${NC}"
        ;;
        
    2)
        # Copie avec nettoyage
        echo ""
        echo -e "${BLUE}═══ COPIE AVEC NETTOYAGE COMPLET ═══${NC}"
        echo ""
        
        warning "⚠️ Cette option va SUPPRIMER toutes les données du staging !"
        read -p "Continuer ? (tapez 'OUI') : " confirm
        
        if [[ "$confirm" != "OUI" ]]; then
            log "Opération annulée"
            exit 0
        fi
        
        # Nom de la base
        read -p "Nom de la base de données [multibikes] : " db_name
        db_name=${db_name:-multibikes}
        
        # Répertoire de sauvegarde
        backup_dir="./backup_prod_$(date +%Y%m%d_%H%M%S)"
        
        # Étape 1 : Sauvegarde
        echo ""
        info "📦 Étape 1/3 : Sauvegarde de la production..."
        ./scripts/transfer_db.sh backup prod "$db_name" "$backup_dir"
        
        # Trouver le fichier de sauvegarde
        backup_file=$(ls -t "$backup_dir"/*.tar.gz 2>/dev/null | head -1)
        
        if [ -z "$backup_file" ]; then
            error "❌ Aucun fichier de sauvegarde trouvé"
        fi
        
        # Étape 2 : Nettoyage
        echo ""
        info "🧹 Étape 2/3 : Nettoyage des volumes staging..."
        ./scripts/clean_odoo_volumes.sh staging
        
        # Étape 3 : Restauration
        echo ""
        info "🔄 Étape 3/3 : Restauration sur staging..."
        ./scripts/transfer_db.sh restore staging "$db_name" "$backup_file"
        
        # Si erreur d'initialisation, corriger
        echo ""
        info "🔧 Vérification de l'initialisation..."
        if ! docker exec odoo-staging python3 -c "import psycopg2; conn=psycopg2.connect(host='db-staging',user='odoo',password='odoo',database='$db_name'); cur=conn.cursor(); cur.execute('SELECT 1 FROM ir_module_module LIMIT 1'); cur.close(); conn.close()" 2>/dev/null; then
            warning "⚠️ Base non initialisée, correction en cours..."
            ./scripts/fix_odoo_init.sh staging "$db_name"
        else
            log "✅ Base correctement initialisée"
        fi
        
        echo ""
        echo -e "${GREEN}✅ COPIE AVEC NETTOYAGE TERMINÉE !${NC}"
        ;;
        
    3)
        # Afficher les commandes
        echo ""
        echo -e "${BLUE}═══ COMMANDES MANUELLES ═══${NC}"
        echo ""
        
        echo -e "${YELLOW}🔸 Pour une copie simple :${NC}"
        echo ""
        echo "  # 1. Sauvegarder la production"
        echo "  ./scripts/transfer_db.sh backup prod multibikes ~/backup-prod"
        echo ""
        echo "  # 2. Restaurer sur staging"
        echo "  ./scripts/transfer_db.sh restore staging multibikes ~/backup-prod/multibikes_backup_XXXXX.tar.gz"
        echo ""
        
        echo -e "${YELLOW}🔸 Pour une copie avec nettoyage :${NC}"
        echo ""
        echo "  # 1. Sauvegarder la production"
        echo "  ./scripts/transfer_db.sh backup prod multibikes ~/backup-prod"
        echo ""
        echo "  # 2. Nettoyer staging (EFFACE TOUT !)"
        echo "  ./scripts/clean_odoo_volumes.sh staging"
        echo ""
        echo "  # 3. Restaurer sur staging"
        echo "  ./scripts/transfer_db.sh restore staging multibikes ~/backup-prod/multibikes_backup_XXXXX.tar.gz"
        echo ""
        echo "  # 4. Si erreur 'Database not initialized'"
        echo "  ./scripts/fix_odoo_init.sh staging multibikes"
        echo ""
        
        echo -e "${YELLOW}🔸 Commandes utiles :${NC}"
        echo ""
        echo "  # Voir les logs"
        echo "  docker logs -f odoo-staging"
        echo ""
        echo "  # Redémarrer Odoo"
        echo "  docker restart odoo-staging"
        echo ""
        echo "  # Mettre à jour tous les modules"
        echo "  docker exec odoo-staging /usr/bin/odoo -d multibikes -u all --stop-after-init"
        echo "  docker restart odoo-staging"
        ;;
        
    *)
        error "❌ Choix invalide"
        ;;
esac

# Commandes finales
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📋 COMMANDES UTILES :${NC}"
echo ""
echo -e "${YELLOW}  # Accéder au staging :${NC}"
echo "  https://staging.mcommemedoc.fr"
echo ""
echo -e "${YELLOW}  # Voir les logs :${NC}"
echo "  docker logs -f odoo-staging"
echo ""
echo -e "${YELLOW}  # En cas de problème :${NC}"
echo "  ./scripts/fix_odoo_init.sh staging multibikes"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" 