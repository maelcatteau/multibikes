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