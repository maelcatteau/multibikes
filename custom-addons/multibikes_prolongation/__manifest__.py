{
    'name': 'Multibikes prolongation',
    'summary': 'Module de prolongation de location pour Multibikes',
    'description': """
        Ce module permet de prolonger les locations de matériel.
        Il ajoute une fonctionnalité pour créer des commandes de prolongation basées sur des
        commandes de location existantes.
    """,
    'version': '1.0',
    'category': 'Sales/Rental',
    'depends': ['sale_renting', 'stock'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'data': [
    'security/ir.model.access.csv',
    'views/rental_extension_views.xml',
    ],
}