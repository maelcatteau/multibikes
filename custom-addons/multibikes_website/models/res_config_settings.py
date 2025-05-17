from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    renting_periods = fields.One2many(
        related='company_id.renting_periods',
        readonly=False
    )