{
    'name': 'Multibikes base',
    'version': '1.0',
    'category': 'Sales/Rental',
    'depends': ['base','sale_renting', 'website_sale_renting'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'data': [
    'views/product_template_views.xml',
    'views/res_partner_views.xml'
    ],
}