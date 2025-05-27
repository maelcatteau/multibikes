# -*- coding: utf-8 -*-

from odoo import fields, models

class ProductPricing(models.Model):
    _inherit = 'product.pricing'
    
    mb_website_published = fields.Boolean(
        string='Visible sur le site web',
        default=False,
        help="When checked, this pricing will be visible on the website."
    )