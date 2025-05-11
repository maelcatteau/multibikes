# multibikes_base

## Description
Le module `multibikes_base` est un module Odoo personnalisé qui ajoute des fonctionnalités spécifiques pour la gestion des informations liées aux produits, aux partenaires et aux ventes. Il est conçu pour répondre aux besoins spécifiques de gestion des cautions et des informations d'identité.

## Fonctionnalités
1. **Ajout d'un champ "Numéro de caution" sur les bons de commande (Sales Order - SO)** :
    - Permet de suivre et de gérer les cautions associées aux commandes.

2. **Ajout de champs sur le modèle `product.template`** :
    - **Valeur en cas de vol** : Permet de définir une valeur spécifique pour un produit en cas de vol.
    - **Caution** : Permet de spécifier une caution associée à un produit.

3. **Ajout de champs sur le modèle `res.partner`** :
    - **Nationalité** : Permet de renseigner la nationalité d'un partenaire.
    - **Numéro de carte d'identité** : Permet de stocker le numéro de carte d'identité d'un partenaire.

4. **Ajout des champs associés dans les vues** :
    - Les champs ajoutés sont intégrés dans les vues correspondantes pour une gestion simplifiée et intuitive.

## Installation
1. Copier le module dans le répertoire `custom-addons` de votre déploiement Odoo.
2. Mettre à jour la liste des modules dans Odoo.
3. Installer le module `multibikes_base` via l'interface d'administration.

## Utilisation
- Lors de la création ou de la modification d'un bon de commande, vous pourrez renseigner le numéro de caution.
- Les champs "Valeur en cas de vol" et "Caution" sont disponibles dans la fiche produit.
- Les champs "Nationalité" et "Numéro de carte d'identité" sont accessibles dans la fiche partenaire.

## Auteurs
Ce module a été développé pour répondre aux besoins spécifiques de gestion des cautions et des informations d'identité dans le cadre de la gestion des produits et des partenaires.

