# ./dockerfiles/Dockerfile.app
# Utilise l'image de base Odoo Enterprise privée que vous avez poussée
FROM ghcr.io/maelcatteau/odoo-ee-base:18.0

# Temporairement root pour copier les scripts et changer les permissions
USER root 

# Copier les scripts nécessaires
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY run_tests.sh /run_tests.sh
RUN chmod +x /run_tests.sh

# Créer et configurer le répertoire pour les rapports de test
RUN mkdir -p /test-reports && \
    chmod 777 /test-reports

# S'assurer que les répertoires pour les volumes existent et ont les bonnes permissions
# /mnt/extra-addons et /etc/odoo sont déjà créés et chownés dans l'image de base.
# On s'assure juste qu'ils sont bien là et accessibles si besoin.
# RUN mkdir -p /mnt/extra-addons /etc/odoo /var/lib/odoo /var/log/odoo && \
#     chown -R odoo:odoo /mnt/extra-addons /etc/odoo /var/lib/odoo /var/log/odoo

# Les volumes seront gérés par docker-compose
VOLUME ["/var/lib/odoo", "/mnt/extra-addons", "/etc/odoo", "/test-reports"]

EXPOSE 8069 8072

USER odoo

# L'ENTRYPOINT par défaut peut être celui de l'application
ENTRYPOINT ["/entrypoint.sh"]
# Le CMD par défaut peut être de lancer Odoo normalement
CMD ["odoo", "-c", "/etc/odoo/odoo.conf"]
