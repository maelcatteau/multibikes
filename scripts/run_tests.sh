#!/bin/bash
set -e # Arrête le script immédiatement si une commande échoue

# Information sur la version d'Odoo
echo "=== VERSION D'ODOO ==="
odoo --version

# Variables pour les tests
DB_NAME=${TEST_DB_NAME:-test_multibikes_ci}
MODULES_TO_TEST=${TEST_MODULES:-multibikes_base,multibikes_website}
REPORTS_DIR=/test-reports
USE_TEST_TAGS=${USE_TEST_TAGS:-false}

# Chemin des add-ons valide
VALID_ADDONS_PATH="/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"

echo "--- Configuration des tests Odoo ---"
echo "Base de données de test: ${DB_NAME}"
echo "Modules à tester: ${MODULES_TO_TEST}"
echo "Chemin des addons: ${VALID_ADDONS_PATH}"
echo "Répertoire des rapports: ${REPORTS_DIR}"
echo "Utilisation des tags de test: ${USE_TEST_TAGS}"
echo "------------------------------------"

# Créer un répertoire temporaire pour les logs
TEMP_LOG=$(mktemp)

# Vérifier la connexion à la base de données
echo "En attente de la base de données sur ${PGHOST:-db-test}:${PGPORT:-5432}..."
until pg_isready -h "${PGHOST:-db-test}" -p "${PGPORT:-5432}" -U "${PGUSER:-odoo}"; do
  sleep 1
done
echo "Base de données prête."

# Vérifier si la base de données existe déjà
DB_EXISTS=$(PGDATABASE=test_postgres psql -h ${PGHOST:-db-test} -p ${PGPORT:-5432} -U ${PGUSER:-odoo} -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" || echo "0")
if [ "$DB_EXISTS" = "1" ]; then
    echo "Suppression de la base de données existante ${DB_NAME}..."
    PGDATABASE=test_postgres dropdb -h ${PGHOST:-db-test} -p ${PGPORT:-5432} -U ${PGUSER:-odoo} ${DB_NAME} || echo "Échec de la suppression de la base de données, on continue..."
fi

# Exécution des tests Odoo uniquement pour les modules MultiBikes
echo "Lancement des tests Odoo..."

# Préparation de la commande de base
BASE_CMD="/usr/bin/odoo \
    --no-http \
    --log-level=${LOG_LEVEL} \
    -d ${DB_NAME} \
    --addons-path=${VALID_ADDONS_PATH} \
    -i ${MODULES_TO_TEST} \
    --test-enable"

# Ajouter l'option --test-tags uniquement si USE_TEST_TAGS est true
if [ "${USE_TEST_TAGS}" = "true" ]; then
    echo "Filtrage des tests avec les tags: ${TEST_MODULES:-multibikes_base,multibikes_website}"
    ${BASE_CMD} --test-tags=${TEST_MODULES:-multibikes_base,multibikes_website} --stop-after-init 2>&1 | tee ${TEMP_LOG}
else
    echo "Exécution de tous les tests sans filtrage par tags"
    ${BASE_CMD} --stop-after-init 2>&1 | tee ${TEMP_LOG}
fi

# Essayer de copier le log dans le répertoire de rapports
cp ${TEMP_LOG} "${REPORTS_DIR}/test_results.log" 2>/dev/null || echo "Avertissement: Impossible de copier le log dans ${REPORTS_DIR}"

# Analyse des résultats pour Odoo 18
echo "--- Résumé des tests ---"

# Vérifier s'il y a des messages d'erreur ou d'échec spécifiques
if grep -q "FAIL:" "${TEMP_LOG}" || grep -q "ERROR:" "${TEMP_LOG}"; then
    echo "❌ Des tests ont échoué ou des erreurs ont été détectées:"
    grep -B 5 -A 5 -E "(FAIL:|ERROR:)" "${TEMP_LOG}" || true
    exit 1
fi

# Analyser la ligne de résumé des tests : "X failed, Y error(s) of Z tests"
RESULT_LINE=$(grep -o "[0-9]* failed, [0-9]* error(s) of [0-9]* tests" "${TEMP_LOG}" | tail -1)

if [ -n "${RESULT_LINE}" ]; then
    # Extraire les valeurs
    FAILED_COUNT=$(echo "${RESULT_LINE}" | grep -o "^[0-9]*")
    ERROR_COUNT=$(echo "${RESULT_LINE}" | grep -o "[0-9]* error" | grep -o "^[0-9]*")
    TOTAL_COUNT=$(echo "${RESULT_LINE}" | grep -o "of [0-9]* tests" | grep -o "[0-9]*")

    echo "📊 Résultats: ${FAILED_COUNT} échecs, ${ERROR_COUNT} erreurs sur ${TOTAL_COUNT} tests"

    # Vérifier s'il y a des tests exécutés
    if [ "${TOTAL_COUNT:-0}" -eq 0 ]; then
        echo "⚠️ ATTENTION: Aucun test n'a été exécuté!"
        # Vérifier si les modules se sont chargés correctement
        if grep -q "Module.*loaded" "${TEMP_LOG}"; then
            echo "✅ Les modules ont été chargés avec succès sans test."
            exit 0
        else
            echo "❌ Les modules n'ont pas pu être chargés correctement."
            exit 1
        fi
    fi

    # Vérifier les résultats
    if [ "${FAILED_COUNT:-0}" -eq 0 ] && [ "${ERROR_COUNT:-0}" -eq 0 ]; then
        echo "✅ Tous les ${TOTAL_COUNT} tests ont réussi!"
        exit 0
    else
        echo "❌ ${FAILED_COUNT} tests ont échoué, ${ERROR_COUNT} erreurs détectées."
        exit 1
    fi
else
    # Fallback si le format de résumé n'est pas trouvé
    echo "⚠️ Format de résumé non reconnu - analyse détaillée:"

    # Vérifier les patterns alternatifs
    if grep -q "0 failed" "${TEMP_LOG}" && ! grep -q "FAIL:" "${TEMP_LOG}"; then
        # Compter les tests via les lignes de stats
        TEST_STATS=$(grep -c "tests.*queries" "${TEMP_LOG}" || echo "0")
        if [ "${TEST_STATS}" -gt 0 ]; then
            echo "✅ Tests détectés et passés avec succès (${TEST_STATS} modules testés)"
            exit 0
        else
            echo "❌ Aucun test détecté dans les statistiques"
            exit 1
        fi
    else
        echo "❌ Statut des tests incertain - vérifiez les logs manuellement."
        # Afficher les dernières lignes pour diagnostic
        echo "--- Dernières lignes des logs ---"
        tail -10 "${TEMP_LOG}"
        exit 1
    fi
fi
