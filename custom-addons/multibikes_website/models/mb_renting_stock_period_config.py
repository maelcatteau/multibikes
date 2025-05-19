from odoo import api, fields, models

class MBRentingStockPeriodConfig(models.Model):
    _name= 'mb.renting.stock.period.config'
    _description = 'Configuration de la période de stock pour la location'
    _rec_name = 'period_id'
    
    period_id = fields.Many2one('mb.renting.period', required=True, ondelete='cascade', string='Période')
    
    # Champ pour lier les produits stockables
    storable_product_ids = fields.Many2many(
        'product.product',
        string='Produits stockables',
        domain=[('is_storable', '=', True)],
        help="Liste des produits stockables associés à cette période"
    )