# Module de Prolongation de Location pour Multibikes

## Description
Ce module étend les fonctionnalités de location d'Odoo pour permettre la prolongation des locations existantes. Il permet aux utilisateurs de sélectionner des articles spécifiques d'une commande de location et de créer une nouvelle commande pour prolonger leur période de location.

## Fonctionnalités principales

### Pour les utilisateurs
- **Prolongation de location**: Bouton dédié sur les commandes de location pour prolonger la période de location
- **Sélection d'articles**: Possibilité de choisir quels articles prolonger et en quelle quantité
- **Traçabilité**: Suivi des relations entre les commandes originales et leurs prolongations
- **Gestion automatique des stocks**: Mise à jour automatique des quantités livrées et retournées

### Pour les administrateurs
- **Visibilité des prolongations**: Filtres dédiés pour identifier facilement les commandes de prolongation
- **Historique complet**: Vue détaillée des prolongations liées à chaque location

## Installation

### Prérequis
- Module `sale_renting` d'Odoo
- Module `stock` d'Odoo

### Étapes d'installation
1. Téléchargez le module dans le dossier des addons personnalisés
2. Mettez à jour la liste des modules dans Odoo
3. Recherchez "Multibikes prolongation" et installez le module
4. Redémarrez le serveur Odoo

## Utilisation

### Prolonger une location
1. Accédez à une commande de location confirmée
2. Cliquez sur le bouton "Prolonger la location"
3. Définissez les dates de début et de fin de la prolongation
4. Sélectionnez les articles à prolonger et ajustez les quantités si nécessaire
5. Validez pour créer la commande de prolongation

### Consulter les prolongations
1. Ouvrez une commande de location
2. Accédez à l'onglet "Prolongations"
3. Consultez la liste des prolongations associées ou cliquez sur "Voir les prolongations"

## Structure technique

### Modèles
- Extension de `sale.order` pour ajouter les champs et méthodes liés aux prolongations
- Wizard `rental.extension.wizard` pour gérer le processus de prolongation
- Lignes de wizard `rental.extension.wizard.line` pour la sélection des articles

### Vues
- Modification de la vue formulaire des commandes pour ajouter le bouton de prolongation
- Ajout d'un onglet "Prolongations" dans les commandes
- Formulaire dédié pour le wizard de prolongation

## Maintenance et support
Pour toute question ou problème concernant ce module, veuillez contacter l'équipe de support Multibikes.

## Licence
Ce module est distribué sous licence LGPL-3. 