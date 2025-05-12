{
    'name': 'Multibikes website visibility',
    'summary': 'Manage website visibility for product pricing',
    'description': """
        This module allows you to manage the visibility of product pricing on the website.
        It adds a checkbox to control whether a pricing is visible or not.
    """,
    'author': 'Maël CATTEAU',
    'version': '1.0',
    'category': 'Sales/Rental',
    'depends': ['sale_renting', 'website_sale_renting'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'data': [
    'views/product_pricing_views.xml',
    'views/product_template_views.xml',
    'views/product_template_template.xml'
    ],
}