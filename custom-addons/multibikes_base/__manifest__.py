# -*- coding: utf-8 -*-
"""Manifest for the multibikes_base module."""
{
    # Informations générales sur le module
    "name": "Multibikes base",
    "version": "18.0.1.0.0",
    "category": "Sales/Rental",
    "summary": "Module de base pour la gestion des locations de vélos",
    "author": "Maël CATTEAU",
    # Dépendances du module
    "depends": ["base", "sale", "sale_renting", "sale_management", "web"],
    # Fichiers de données (vues, menus, actions, etc.)
    "data": [
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
        "report/sale_report_caution.xml",
        "wizard/sale_order_discount.xml",
    ],
    # Configuration d'installation
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
