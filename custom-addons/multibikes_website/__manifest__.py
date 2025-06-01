{
    'name': 'MultiBikes Website Extensions',
    'summary': 'Fonctionnalités avancées pour le site web MultiBikes',
    'description': """
        Ce module étend les fonctionnalités du site web e-commerce MultiBikes avec:
        
        1. Gestion de la visibilité des tarifs sur le site web
        2. Configuration de durées minimales de location par période saisonnière
        3. Calcul dynamique des contraintes de location selon la date
        4. Filtrage intelligent des tarifs affichés dans la table de prix
        5. Amélioration de l'expérience utilisateur pour la location de vélos
    """,
    'version': '18.0.1.0.0',
    'category': 'Sales/Rental',
    'depends': [
        'web',
        'website_sale',
        'website_sale_renting',
        'stock',
        'product',
        'multibikes_base',
        'website_sale_stock',
        'website_sale_stock_renting'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/product_pricing_views.xml',
        'views/product_template_template_views.xml',
        'views/stock_warehouse_views.xml',
        'views/stock_picking_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'multibikes_website/static/src/js/multibikes_website_sale_DaterangePicker.js',
            'multibikes_website/static/src/js/multibikes_website_sale.js',
            'multibikes_website/static/src/scss/custom_dates.scss',
        ],
    },
    'author': 'MultiBikes',
    'maintainer': 'Équipe MultiBikes',
    'website': 'https://www.multibikes.com',
}