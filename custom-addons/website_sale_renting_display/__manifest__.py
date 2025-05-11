# -*- coding: utf-8 -*-
{
    'name': 'Website Rental Price Display',
    'version': '1.0',
    'summary': 'Controls rental price display on website based on publication status',
    'description': """
        This module extends the website rental functionality to allow control over 
        which pricing rules are displayed on the website. Pricing rules can be 
        published or unpublished independently.
    """,
    'category': 'Website/Website',
    'author': 'Maël CATTEAU',
    'license': 'LGPL-3',
    
    # Modules requis
    'depends': [
        'website_sale_renting',
        'sale_renting',
        'website_sale',
    ],
    
    # Fichiers de données chargés lors de l'installation
    'data': [
        'views/website_published_templates.xml',
    ],
    
    # Indique si le module est installable
    'installable': True,
    'application': False,
    'auto_install': False,
    
    # Pour la compatibilité avec les autres versions d'Odoo
    'odoo': {
        'min_version': '18.0',  # Ajustez à votre version d'Odoo
    }
}
