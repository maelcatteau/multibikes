from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    x_partner_nationalite = fields.Char(
        string='Nationalité du client',
        help="Permet de renseigner la nationalité du client"
    )

    x_partner_n_id = fields.Char(
        string='Numéro de la carte d\'identité',
        help="Permet de renseigner le numéro de la carte d'identité du client"
    )