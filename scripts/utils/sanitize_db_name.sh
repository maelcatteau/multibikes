#!/bin/bash

# ============================================
# UTILITAIRE DE NORMALISATION DES NOMS DE DB
# ============================================
#
# 📋 DESCRIPTION :
# Normalise les noms de bases de données pour PostgreSQL
# Remplace les caractères problématiques par des underscores
#
# 🚀 USAGE :
# source ./scripts/utils/sanitize_db_name.sh
# sanitized_name=$(sanitize_db_name "my-database-name")
#
# ============================================

# Fonction pour normaliser un nom de base de données
sanitize_db_name() {
    local name=$1
    # Remplacer les tirets et autres caractères spéciaux par des underscores
    # Garder seulement lettres, chiffres et underscores
    echo "$name" | sed 's/[^a-zA-Z0-9_]/_/g' | tr '[:upper:]' '[:lower:]'
}

# Si le script est exécuté directement (pas sourcé)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [ $# -lt 1 ]; then
        echo "Usage: $0 <database_name>"
        echo "Exemple: $0 multibikes-test"
        exit 1
    fi
    
    original=$1
    sanitized=$(sanitize_db_name "$original")
    
    if [ "$original" != "$sanitized" ]; then
        echo "⚠️  Nom original : $original"
        echo "✅ Nom normalisé : $sanitized"
        echo ""
        echo "Le nom contient des caractères spéciaux qui peuvent causer des problèmes."
        echo "Il est recommandé d'utiliser : $sanitized"
    else
        echo "✅ Le nom '$original' est déjà valide"
    fi
fi 