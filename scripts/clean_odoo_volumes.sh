#!/bin/bash

# ============================================
# SCRIPT DE NETTOYAGE DES VOLUMES ODOO v2
# ============================================
#
# 📋 DESCRIPTION :
# Nettoie complètement les volumes d'une instance Odoo
#
# ⚠️ ATTENTION : CE SCRIPT SUPPRIME TOUTES LES DONNÉES !
#
# 🚀 USAGE :
# ./scripts/clean_odoo_volumes.sh <env>
#
# 📋 EXEMPLE :
# ./scripts/clean_odoo_volumes.sh staging
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

# Fonction pour afficher les prochaines commandes
show_next_commands() {
    local env=$1
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}📋 PROCHAINES COMMANDES UTILES :${NC}"
    echo ""
    
    echo -e "${YELLOW}  # Pour restaurer une sauvegarde :${NC}"
    echo "  ./scripts/transfer_db.sh restore $env multibikes /path/to/backup.tar.gz"
    echo ""
    echo -e "${YELLOW}  # Pour créer une nouvelle base via l'interface web :${NC}"
    if [[ "$env" == "staging" ]]; then
        echo "  https://staging.mcommemedoc.fr/web/database/manager"
    else
        echo "  https://mcommemedoc.fr/web/database/manager"
    fi
    echo ""
    echo -e "${YELLOW}  # Pour voir les logs :${NC}"
    echo "  docker logs -f odoo-$env"
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Vérification des paramètres
if [ $# -lt 1 ]; then
    echo -e "${RED}❌ Erreur : Paramètres manquants${NC}"
    echo ""
    echo "Usage: $0 <env>"
    echo ""
    echo "Environnements disponibles :"
    echo "  - staging"
    echo "  - prod (⚠️ DANGER !)"
    echo ""
    echo "Exemple:"
    echo "  $0 staging"
    exit 1
fi

env=$1

# Vérifier que c'est un nom d'env valide
if [[ "$env" != "staging" && "$env" != "prod" ]]; then
    error "❌ Environnement invalide : $env. Utilisez 'staging' ou 'prod'"
fi

echo -e "${BLUE}"
echo "============================================"
echo "🧹 NETTOYAGE DES VOLUMES ODOO"
echo "============================================"
echo -e "${NC}"

log "📋 Configuration :"
log "   Environnement : $env"

# Double confirmation pour la production
if [[ "$env" == "prod" ]]; then
    echo -e "${RED}⚠️ ⚠️ ⚠️  ATTENTION CRITIQUE  ⚠️ ⚠️ ⚠️${NC}"
    echo -e "${RED}VOUS ALLEZ SUPPRIMER TOUTES LES DONNÉES DE PRODUCTION !${NC}"
    echo ""
    echo -e "${YELLOW}Tapez exactement : 'JE VEUX SUPPRIMER LA PRODUCTION'${NC}"
    read -r confirm
    if [[ "$confirm" != "JE VEUX SUPPRIMER LA PRODUCTION" ]]; then
        log "🛑 Opération annulée"
        exit 0
    fi
fi

# Confirmation finale
echo -e "${RED}⚠️ ⚠️ ⚠️  ATTENTION  ⚠️ ⚠️ ⚠️${NC}"
echo -e "${YELLOW}Cette opération va :${NC}"
echo "   🗑️  SUPPRIMER tous les volumes de l'environnement '$env'"
echo "   📦 EFFACER toutes les bases de données"
echo "   🖼️  SUPPRIMER tous les fichiers (images, documents...)"
echo ""
echo -e "${YELLOW}Voulez-vous continuer ? (tapez 'OUI' en majuscules)${NC}"
read -r confirm
if [[ "$confirm" != "OUI" ]]; then
    log "🛑 Nettoyage annulé"
    exit 0
fi

# Définir le fichier docker-compose
if [[ "$env" == "staging" ]]; then
    compose_file="docker-compose_staging.yaml"
else
    compose_file="docker-compose_prod.yaml"
fi

# Arrêter la stack
log "🛑 Arrêt de la stack $env..."
docker compose -f "$compose_file" down || true

# Identifier les volumes
log "🔍 Identification des volumes..."
volumes=$(docker compose -f "$compose_file" config --volumes 2>/dev/null | grep -E "^\s" | tr -d ' :' || true)

if [ -z "$volumes" ]; then
    warning "⚠️ Aucun volume trouvé pour l'environnement $env"
else
    echo "📋 Volumes trouvés :"
    for vol in $volumes; do
        echo "   - $vol"
    done
fi

# Supprimer les volumes
log "🗑️ Suppression des volumes..."
for vol in $volumes; do
    full_vol_name="odoo-deployment_${vol}"
    if docker volume ls -q | grep -q "^${full_vol_name}$"; then
        log "   Suppression de $full_vol_name..."
        docker volume rm "$full_vol_name" || warning "Impossible de supprimer $full_vol_name"
    else
        warning "   Volume $full_vol_name introuvable"
    fi
done

# Nettoyer aussi les volumes orphelins possibles
log "🧹 Recherche de volumes orphelins..."
orphan_volumes=$(docker volume ls -q | grep "odoo-deployment.*$env" || true)
if [ -n "$orphan_volumes" ]; then
    for vol in $orphan_volumes; do
        log "   Suppression du volume orphelin $vol..."
        docker volume rm "$vol" || true
    done
fi

# Redémarrer la stack
log "🚀 Redémarrage de la stack $env..."
docker compose -f "$compose_file" up -d

# Attendre le démarrage
log "⏳ Attente du démarrage (30 secondes)..."
sleep 30

echo ""
echo -e "${GREEN}🎉 NETTOYAGE TERMINÉ !${NC}"
echo -e "${BLUE}============================================${NC}"
log "✅ Les volumes ont été nettoyés"
log "✅ La stack $env a été redémarrée"
echo ""
warning "⚠️ L'instance est maintenant VIDE, vous devez restaurer des données !"

show_next_commands "$env" 