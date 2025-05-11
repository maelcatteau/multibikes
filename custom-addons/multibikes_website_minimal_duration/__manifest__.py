{
    'name': 'Multibikes website minimal duration',
    'summary': 'Manage minimal duration for product pricing on the website',
    'description': """
        This module allows you to manage the minimal duration for product pricing on the website.
        It adds fields to control the minimal duration for each season.
    """,
    'version': '1.0',
    'category': 'Sales/Rental',
    'depends': ['website_sale_renting'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'data': [
      'views/res_config_settings_views.xml'
    ]
}