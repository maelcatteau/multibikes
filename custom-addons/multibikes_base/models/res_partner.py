from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    mb_nationalite = fields.Char(
        string='Nationalité du client',
        help="Permet de renseigner la nationalité du client"
    )

    mb_n_id = fields.Char(
        string='Numéro de la carte d\'identité',
        help="Permet de renseigner le numéro de la carte d'identité du client"
    )