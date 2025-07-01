Déploiement
===========

.. toctree::
   :maxdepth: 2

   docker
   environments
Docker & Conteneurisation
=========================

Configuration Docker
-------------------

Le projet utilise plusieurs fichiers docker-compose selon l'environnement :

- ``docker-compose_dev.yaml`` : Environnement de développement
- ``docker-compose_staging.yaml`` : Environnement de staging
- ``docker-compose_prod.yaml`` : Environnement de production
- ``docker-compose_test.yaml`` : Tests automatisés

Dockerfiles
-----------

- ``Dockerfile.dev`` : Image de développement
- ``Dockerfile.staging`` : Image de staging
- ``Dockerfile.prod`` : Image de production optimisée
- ``Dockerfile.odooEEbase`` : Image de base Odoo Enterprise

Scripts Docker
--------------

- ``clean_odoo_volumes.sh`` : Nettoyage des volumes
- ``entrypoint_dev.sh`` : Point d'entrée développement
- ``entrypoint_prod.sh`` : Point d'entrée production
- ``entrypoint_staging.sh`` : Point d'entrée staging
EOF

# deployment/environments.rst
cat > deployment/environments.rst << 'EOF'
Environnements
==============

Variables d'environnement
-------------------------

Le projet utilise des fichiers .env séparés par environnement :

Développement
~~~~~~~~~~~~~

- ``env/Dev.env`` : Variables Odoo développement
- ``env/Database_dev.env`` : Configuration base de données dev

Staging
~~~~~~~

- ``env/Staging.env`` : Variables Odoo staging
- ``env/Database_staging.env`` : Configuration base de données staging

Production
~~~~~~~~~~

- ``env/Prod.env`` : Variables Odoo production
- ``env/Database_prod.env`` : Configuration base de données production

Configuration
~~~~~~~~~~~~~

Voir les fichiers d'exemple dans ``examples/`` :

- ``Database.env.example``
- ``Odoo.env.example``
- ``nginx_proxy_manager_conf.example``