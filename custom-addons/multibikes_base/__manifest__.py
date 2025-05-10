{
    'name': 'Multibikes base',
    'version': '1.0',
    'category': 'Sales/Rental',
    'depends': ['sale_renting', 'website_sale_renting'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'data': [
    'views/product_template_views.xml',
    'views/product_pricing_views.xml',
    ],
}