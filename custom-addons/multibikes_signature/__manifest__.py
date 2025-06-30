# -*- coding: utf-8 -*-
# Manifest for the multibikes_signature module.
{
    # Informations générales sur le module
    "name": "Multibikes signature",
    "version": "18.0.1.0.0",
    "category": "Sales/Rental",
    "summary": "Module de base pour la gestion des signatures sur les contrats de location",
    "author": "Maël CATTEAU",
    # Dépendances du module
    "depends": ["base", "sale", "sale_renting", "sale_management", "web", "sign", "multibikes_base"],
    # Fichiers de données (vues, menus, actions, etc.)
    "data": [
        "views/sale_order_views.xml",
    ],
    # Configuration d'installation
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
