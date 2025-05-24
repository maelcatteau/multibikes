# Support Multilingue - Module Multibikes Base

Ce module supporte maintenant les traductions en français, anglais et allemand pour tous les rapports de caution.

## Langues Supportées

- **Français (fr_FR)** : Langue par défaut
- **Anglais (en_US)** : Traduction complète
- **Allemand (de_DE)** : Traduction complète

## Activation des Traductions

### 1. Installation du Module
Lors de l'installation du module, les langues sont automatiquement activées.

### 2. Configuration Manuelle (si nécessaire)
1. Aller dans **Paramètres > Traductions > Langues**
2. Activer les langues souhaitées :
   - English (en_US)
   - Deutsch (de_DE)
   - Français (fr_FR)

### 3. Configuration des Utilisateurs
1. Aller dans **Paramètres > Utilisateurs et Sociétés > Utilisateurs**
2. Sélectionner l'utilisateur
3. Dans l'onglet **Préférences**, définir la **Langue**

### 4. Configuration des Partenaires
1. Aller dans **Ventes > Clients**
2. Sélectionner le client
3. Dans l'onglet **Ventes & Achats**, définir la **Langue**

## Utilisation

Les rapports s'adapteront automatiquement à la langue :
- Du partenaire (client) pour les rapports générés depuis les commandes
- De l'utilisateur connecté par défaut

### Exemple de Traductions

| Français | Anglais | Allemand |
|----------|---------|----------|
| Caution Unitaire | Unit Deposit | Einzelkaution |
| Total Caution | Deposit Total | Kautionssumme |
| Facture de Caution | Deposit Invoice | Kautionsrechnung |
| Commercial | Salesperson | Verkäufer |
| Quantité | Quantity | Menge |

## Mise à Jour des Traductions

Pour mettre à jour les traductions après modification du code :

```bash
# Redémarrer Odoo et mettre à jour le module
docker exec <container_name> /usr/bin/odoo -u multibikes_base -d <database_name>

# Ou via l'interface Odoo
# Aller dans Apps > Module Updates > Update List
# Chercher "Multibikes base" et cliquer sur "Upgrade"
```

## Fichiers de Traduction

Les fichiers de traduction se trouvent dans `i18n/` :
- `fr.po` : Français
- `en.po` : Anglais  
- `de.po` : Allemand
- `multibikes_base.pot` : Template pour nouvelles traductions 