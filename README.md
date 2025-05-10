# Déploiement Odoo Enterprise MultiBikes

Ce projet contient les fichiers de configuration nécessaires pour déployer Odoo 18.0 Enterprise dans un environnement Docker pour MultiBikes.

## Structure du Projet

```
.
├── docker-compose.yml     # Configuration Docker Compose
├── Dockerfile            # Image Docker personnalisée pour Odoo
├── entrypoint.sh        # Script d'entrée du conteneur
├── config/
│   └── odoo.conf        # Fichier de configuration Odoo
└── custom-addons/       # Modules personnalisés
    └── multibikes_base  # Module de base MultiBikes
```

## Prérequis

- Docker
- Docker Compose
- Accès au package Odoo Enterprise (odoo_18.0+e.latest_all.deb)

## Installation

1. Assurez-vous que les prérequis sont installés
2. Clonez ce dépôt
3. Placez le fichier `odoo_18.0+e.latest_all.deb` à la racine du projet
4. Lancez les conteneurs :

```bash
docker-compose up -d
```

## Configuration

### Environnement

Le déploiement utilise les services suivants :
- Odoo 18.0 Enterprise
- PostgreSQL (base de données)

### Volumes Docker

- `/var/lib/odoo` : Stockage des données Odoo
- `/mnt/extra-addons` : Modules personnalisés
- `/etc/odoo` : Configuration Odoo

### Ports

- 8069 : Interface web Odoo
- 8072 : Live chat / Long polling

## Modules Personnalisés

### multibikes_base

Module de base contenant les personnalisations spécifiques à MultiBikes.

## Maintenance

### Sauvegarde

Les données sont persistantes grâce aux volumes Docker. Il est recommandé de sauvegarder régulièrement :
- La base de données PostgreSQL
- Le dossier filestore (/var/lib/odoo)
- Les modules personnalisés (/mnt/extra-addons)

### Mise à jour

Pour mettre à jour Odoo :

1. Arrêtez les conteneurs : `docker-compose down`
2. Remplacez le fichier .deb par la nouvelle version
3. Reconstruisez l'image : `docker-compose build`
4. Relancez les conteneurs : `docker-compose up -d`

## Support

Pour toute question ou problème, veuillez créer une issue dans le dépôt du projet.