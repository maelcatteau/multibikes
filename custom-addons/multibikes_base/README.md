# Module Multibikes Base

Module de base pour la gestion des locations de vélos dans Odoo.

## Fonctionnalités

### Gestion des Produits (Vélos)
- **Cautions** : Possibilité de définir un montant de caution pour chaque vélo
- **Valeur en cas de vol** : Montant facturé en cas de vol ou perte totale
- **Tailles** : Définition des tailles minimales et maximales recommandées

### Gestion des Commandes
- **Type de caution** : Choix entre carte bancaire, espèces ou chèque
- **Numéro de caution** : Référence de la caution (ex: 4 derniers chiffres CB)

### Rapports
- **Rapport de devis/commande avec cautions** : Affichage des cautions dans les devis standards
- **Rapport de caution uniquement** : Facture spécifique pour les cautions
- **Support multilingue** : Français, anglais et allemand

## Structure du Module

```
multibikes_base/
├── models/
│   ├── product_template.py    # Extension des produits pour les cautions
│   ├── sale_order.py         # Extension des commandes
│   └── sale_order_line.py    # Logique des lignes de commande
├── views/
│   ├── product_template_views.xml  # Vues des produits
│   └── sale_order_views.xml       # Vues des commandes
├── report/
│   └── sale_report_caution.xml    # Templates des rapports
├── tests/
│   ├── test_product_template.py   # Tests des produits
│   └── test_sale_order.py        # Tests des commandes
└── i18n/                          # Fichiers de traduction
```

## Installation

1. Placer le module dans le dossier `custom-addons`
2. Redémarrer Odoo
3. Aller dans **Applications**
4. Rechercher "Multibikes base"
5. Cliquer sur **Installer**

## Configuration

Aucune configuration particulière n'est requise. Le module étend automatiquement les vues existantes.

