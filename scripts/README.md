# Scripts de Gestion Odoo

## 📋 Vue d'ensemble

Cette collection de scripts facilite la gestion des instances Odoo en production et staging, incluant la sauvegarde, la restauration et la synchronisation des données.

## 🚀 Guide de démarrage rapide

### Workflow complet Production → Staging

Le plus simple est d'utiliser le script interactif :

```bash
./scripts/workflow_prod_to_staging.sh
```

Ce script vous guidera à travers toutes les étapes nécessaires.

## 📦 Scripts disponibles

### 1. `transfer_db.sh` - Sauvegarde et Restauration

Script principal pour sauvegarder et restaurer des bases Odoo.

**Sauvegarde :**
```bash
./scripts/transfer_db.sh backup prod multibikes
./scripts/transfer_db.sh backup staging multibikes ~/mes-backups
```

**Restauration :**
```bash
./scripts/transfer_db.sh restore staging multibikes ./backup.tar.gz
```

### 2. `workflow_prod_to_staging.sh` - Workflow interactif

Script guidé pour copier la production vers le staging.

```bash
./scripts/workflow_prod_to_staging.sh
```

Options disponibles :
- Copie simple (sauvegarde → restauration)
- Copie avec nettoyage complet des volumes
- Affichage des commandes manuelles

### 3. `clean_odoo_volumes.sh` - Nettoyage des volumes

⚠️ **ATTENTION** : Supprime TOUTES les données !

```bash
./scripts/clean_odoo_volumes.sh staging
```

### 4. `fix_odoo_init.sh` - Correction d'initialisation

Corrige les problèmes d'initialisation après une restauration.

```bash
./scripts/fix_odoo_init.sh staging multibikes
```

### 5. `utils/sanitize_db_name.sh` - Normalisation des noms

Vérifie et normalise les noms de bases de données.

```bash
./scripts/utils/sanitize_db_name.sh multibikes-test
# Sortie : multibikes_test
```

## ⚠️ Notes importantes

### Noms de bases de données

**ÉVITEZ** les caractères spéciaux dans les noms de bases :
- ❌ `multibikes-test`
- ❌ `multibikes.prod`
- ✅ `multibikes_test`
- ✅ `multibikes_prod`

Les scripts gèrent les noms avec caractères spéciaux, mais il est préférable de les éviter.

### Conteneurs

Les scripts utilisent ces noms de conteneurs :
- Production : `odoo-prod`
- Staging : `odoo-staging`

### Format des sauvegardes

Les sauvegardes sont au format `.tar.gz` et contiennent :
- Le dump SQL de la base
- Le filestore (images, documents, etc.)

## 🔧 Cas d'usage typiques

### 1. Copie simple prod → staging

```bash
# Option 1 : Workflow interactif
./scripts/workflow_prod_to_staging.sh

# Option 2 : Commandes manuelles
./scripts/transfer_db.sh backup prod multibikes
./scripts/transfer_db.sh restore staging multibikes ./backup_prod_*/multibikes_backup_*.tar.gz
```

### 2. Restauration sur volumes vierges

```bash
# 1. Nettoyer complètement le staging
./scripts/clean_odoo_volumes.sh staging

# 2. Restaurer la sauvegarde
./scripts/transfer_db.sh restore staging multibikes ./backup.tar.gz

# 3. Si erreur "Database not initialized"
./scripts/fix_odoo_init.sh staging multibikes
```

### 3. Sauvegarde quotidienne

Ajoutez à votre crontab :
```bash
0 2 * * * /chemin/vers/scripts/transfer_db.sh backup prod multibikes /chemin/backups/daily
```

## 🔍 Troubleshooting

### Erreur "Database not initialized"

Après une restauration sur volumes vierges :
```bash
./scripts/fix_odoo_init.sh staging multibikes
```

### Erreur avec les noms de bases

Si votre nom contient des tirets ou caractères spéciaux :
```bash
# Vérifier le nom
./scripts/utils/sanitize_db_name.sh mon-nom-base

# Utiliser le nom suggéré pour la restauration
```

### Voir les logs

```bash
docker logs -f odoo-staging
docker logs -f odoo-prod
```

### Mettre à jour tous les modules

Après une restauration :
```bash
docker exec odoo-staging /usr/bin/odoo -d multibikes -u all --stop-after-init
docker restart odoo-staging
```

## 📞 Support

En cas de problème :
1. Vérifiez les logs : `docker logs -f odoo-staging`
2. Vérifiez l'état des conteneurs : `docker ps`
3. Utilisez le script de correction : `./scripts/fix_odoo_init.sh` 