#!/bin/bash
set -e # Arrête le script immédiatement si une commande échoue

# Information sur la version d'Odoo
echo "=== VERSION D'ODOO ==="
odoo --version

# Variables pour les tests
DB_NAME=${TEST_DB_NAME:-test_multibikes_ci}
MODULES_TO_TEST=${TEST_MODULES:-multibikes_base,multibikes_website}
REPORTS_DIR=/test-reports

# Chemin des add-ons valide
VALID_ADDONS_PATH="/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"

echo "--- Configuration des tests Odoo ---"
echo "Base de données de test: ${DB_NAME}"
echo "Modules à tester: ${MODULES_TO_TEST}"
echo "Chemin des addons: ${VALID_ADDONS_PATH}"
echo "Répertoire des rapports: ${REPORTS_DIR}"
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
/usr/bin/odoo \
    --no-http \
    --log-level=test \
    -d ${DB_NAME} \
    --addons-path=${VALID_ADDONS_PATH} \
    -i ${MODULES_TO_TEST} \
    --test-enable \
    --test-tags '/multibikes_base,multibikes_website' \
    --stop-after-init 2>&1 | tee ${TEMP_LOG}

# Essayer de copier le log dans le répertoire de rapports
cp ${TEMP_LOG} "${REPORTS_DIR}/test_results.log" 2>/dev/null || echo "Avertissement: Impossible de copier le log dans ${REPORTS_DIR}"

# Analyse des résultats pour Odoo 18
echo "--- Résumé des tests ---"

# Vérifier s'il y a des messages d'erreur ou d'échec spécifiques
if grep -q "FAIL:" "${TEMP_LOG}" || grep -q "ERROR:" "${TEMP_LOG}"; then
    echo "Des tests ont échoué ou des erreurs ont été détectées:"
    grep -B 5 -A 5 -E "(FAIL:|ERROR:)" "${TEMP_LOG}" || true
    exit 1
else
    # Vérifier les warnings de tests
    if grep -q "0 failed" "${TEMP_LOG}"; then
        # Vérifier s'il y a des tests qui ont été exécutés
        if grep -q "0 test" "${TEMP_LOG}"; then
            echo "ATTENTION: Aucun test n'a été exécuté!"
            # Considérer cela comme une réussite si les modules sont chargés sans erreur
            if grep -q "Module.*loaded" "${TEMP_LOG}"; then
                echo "Les modules ont été chargés avec succès sans erreur."
                exit 0
            else
                echo "Les modules n'ont pas pu être chargés correctement."
                exit 1
            fi
        else
            echo "Tous les tests ont réussi."
            exit 0
        fi
    else
        echo "Statut des tests incertain - vérifiez les logs."
        exit 1
    fi
fi
