{
    'name': 'Multibikes base',
    'version': '1.0',
    'category': 'Sales/Rental',
    'summary': 'Module de base pour la gestion des locations de vélos',
    'description': """
        Module de base pour Multibikes qui ajoute :
        - Gestion des cautions pour les locations
        - Personnalisation des fiches produits
        - Personnalisation des commandes
    """,
    'author': 'Maël CATTEAU',
    'depends': ['base', 'sale', 'sale_renting', 'website_sale_renting'],
    'data': [
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}