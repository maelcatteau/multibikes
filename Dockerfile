FROM ubuntu:22.04

# Éviter les interactions avec les paquets
ENV DEBIAN_FRONTEND=noninteractive

# Installation des dépendances
RUN apt-get update && apt-get install -y \
    postgresql-client \
    python3 \
    python3-pip \
    libpq-dev \
    wget \
    gnupg \
    lsb-release \
    wkhtmltopdf \
    ca-certificates \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Vérifier la connexion internet
RUN echo "Test de connexion Internet" && \
    ping -c 2 google.com || echo "Échec du ping, mais on continue" && \
    curl -I https://www.odoo.com || echo "Échec de curl, mais on continue"

# Configurer le répertoire de travail
WORKDIR /opt/odoo

# Copier l'archive .deb
COPY ./odoo_18.0+e.latest_all.deb /tmp/

# Installer les dépendances Python supplémentaires
RUN pip3 install --no-cache-dir phonenumbers pycountry python-stdnum requests pyOpenSSL cryptography

# Installer le package Odoo Enterprise
RUN apt-get update && \
    apt-get install -y --no-install-recommends /tmp/odoo_18.0+e.latest_all.deb && \
    apt-get -f install -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/odoo_18.0+e.latest_all.deb

# Créer les répertoires nécessaires
RUN mkdir -p /var/lib/odoo /var/log/odoo /mnt/extra-addons
RUN chown -R odoo:odoo /var/lib/odoo /var/log/odoo /mnt/extra-addons

# S'assurer que le dossier de configuration est accessible
RUN mkdir -p /etc/odoo && chown -R odoo:odoo /etc/odoo && chmod 775 /etc/odoo

# Copier le script d'entrée
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

VOLUME ["/var/lib/odoo", "/mnt/extra-addons"]

# Exposer les ports Odoo
EXPOSE 8069 8072

# Passer à l'utilisateur odoo pour exécuter Odoo
USER odoo

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo", "-c", "/etc/odoo/odoo.conf"]