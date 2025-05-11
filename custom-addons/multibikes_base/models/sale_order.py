from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_numero_de_caution = fields.Integer(
        string="Numéro du dossier de caution",
        help="Numéro du dossier de caution pour la location"
    )