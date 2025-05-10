from odoo import api, fields, models

class ProductPricing(models.Model):
    _inherit = 'product.pricing'
    
    website_published = fields.Boolean(
        string='Visible sur le site web',
        default=True,
        help="When checked, this pricing will be visible on the website."
    )