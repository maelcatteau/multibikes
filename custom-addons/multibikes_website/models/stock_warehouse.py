# -*- coding: utf-8 -*-

from odoo import models, fields

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_excluded_from_availability = fields.Boolean(
        string="Exclure des disponibilités",
        default=False,
        help="Si coché, les quantités de cet entrepôt ne seront pas prises en compte dans les disponibilités sur le site e-commerce."
    )
