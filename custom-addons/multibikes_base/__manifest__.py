{
    # Informations générales sur le module
    'name': 'Multibikes base',
    'version': '1.0',
    'category': 'Sales/Rental',
    'summary': 'Module de base pour la gestion des locations de vélos',
    'description': """
        Module de base pour Multibikes qui ajoute :
        - Gestion des cautions pour les locations
        - Personnalisation des fiches produits
        - Personnalisation des commandes
        - Support multilingue (français, anglais, allemand)
    """,
    'author': 'Maël CATTEAU',
    
    # Dépendances du module
    'depends': ['base', 'sale', 'sale_renting'],
    
    # Fichiers de données (vues, menus, actions, etc.)
    'data': [
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'report/sale_report_caution.xml'
    ],
    
    # Configuration d'installation
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}