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

## Conventions de nommage

Pour maintenir une cohérence dans la base de code et faciliter la maintenance, nous suivons des conventions de nommage strictes pour les modules et les champs.

### Modules

Tous les modules personnalisés doivent avoir un nom qui commence par `multibikes_` suivi d'un identifiant descriptif en minuscules. Par exemple :
- `multibikes_base`
- `multibikes_prolongation`
- `multibikes_website_visibility`
- `multibikes_website_minimal_duration`

### Champs

Tous les champs personnalisés définis dans les modèles doivent avoir un nom qui commence par le préfixe `mb_` pour éviter les conflits avec les modules standards d'Odoo et faciliter l'identification des champs personnalisés. Par exemple :
- `mb_is_rental_extension`
- `mb_original_rental_id`
- `mb_renting_period1_start_date`

Cette convention s'applique à tous les types de champs : Many2one, One2many, Many2many, Boolean, Integer, Float, Date, Datetime, etc.

## Conventions de nommage des commits

Nous suivons une convention spécifique pour les messages de commit afin de maintenir un historique clair et faciliter la génération de changelogs. Chaque message de commit doit suivre le format suivant :

[TYPE][DOMAINE] Description concise du changement


### Types de commits
- **[FEAT]** : Nouvelle fonctionnalité
- **[FIX]** : Correction de bug
- **[DOCS]** : Modifications de la documentation
- **[STYLE]** : Changements de formatage qui n'affectent pas le fonctionnement du code
- **[REFACTOR]** : Restructuration du code sans changement de fonctionnalité
- **[PERF]** : Améliorations de performance
- **[TEST]** : Ajout ou modification de tests
- **[CHORE]** : Modifications aux outils de build, dépendances, etc.

### Domaines/Modules
- **[BASE]** : Module multibikes_base
- **[WEBVIS]** : Module multibikes_website_visibility
- **[PROLONG]** : Module multibikes_prolongation
- **[WEBMIN]** : Module multibikes_website_minimal_duration
- **[GENERAL]** : Changement affectant la structure globale

### Exemples

[FEAT][BASE] Ajoute l'authentification à deux facteurs
[FIX][WEBVIS] Résout le problème de chargement d'images sur Safari
[DOCS][PROLONG] Met à jour la documentation du module de prolongation
[STYLE][WEBMIN] Standardise l'indentation dans les fichiers CSS
[REFACTOR][BASE] Simplifie la logique de validation des formulaires
[PERF][WEBVIS] Optimise les requêtes à la base de données
[TEST][PROLONG] Ajoute des tests unitaires pour le module de prolongation
[CHORE][WEBMIN] Met à jour les dépendances obsolètes