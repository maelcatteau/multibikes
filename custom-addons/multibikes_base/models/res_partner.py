from odoo import fields, models

class ResPartner(models.Model):
    """
    Extension du modèle Res Partner
    ------------------------------
    Ajoute des champs pour gérer les informations d'identité des clients
    nécessaires pour les contrats de location.
    """
    _inherit = 'res.partner'
    
    mb_nationalite = fields.Char(
        string='Nationalité du client',
        help="Permet de renseigner la nationalité du client pour les contrats de location"
    )

    mb_n_id = fields.Char(
        string='Numéro de la carte d\'identité',
        help="Permet de renseigner le numéro de la carte d'identité du client pour la vérification d'identité lors de la location"
    )