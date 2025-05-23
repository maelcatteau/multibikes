# models/sale_order_line.py
from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    mb_caution_subtotal = fields.Monetary(
        string='Caution totale',
        currency_field='currency_id',
        compute='_compute_mb_caution_total',
        store=True,
        help="Montant total de la caution (caution unitaire × quantité)"
    )
    
    @api.depends('product_id.mb_caution', 'product_uom_qty')
    def _compute_mb_caution_subtotal(self):
        for line in self:
            line.mb_caution_subtotal = line.product_id.mb_caution * line.product_uom_qty

    @api.onchange('product_id.mb_caution', 'product_uom_qty')
    def _onchange_product_id_caution(self):
        if self.product_id:
            self.mb_caution_subtotal = self.product_id.mb_caution * self.product_uom_qty
# models/sale_order_line.py
from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    # Champs pour affichage dans les vues
    mb_caution_unit = fields.Monetary(
        string='Caution unitaire',
        compute='_compute_mb_fields',
        currency_field='currency_id',
        help="Montant de la caution unitaire"
    )
    
    mb_value_in_case_of_theft = fields.Monetary(
        string='Valeur en cas de vol',
        compute='_compute_mb_fields',
        currency_field='currency_id',
        help="Valeur du produit en cas de vol"
    )
    
    mb_caution_subtotal = fields.Monetary(
        string='Caution totale',
        compute='_compute_mb_fields',
        currency_field='currency_id',
        help="Montant total de la caution (caution unitaire × quantité)"
    )
    
    @api.depends('product_id', 'product_uom_qty')
    def _compute_mb_fields(self):
        for line in self:
            if line.product_id and line.product_id.product_tmpl_id:
                template = line.product_id.product_tmpl_id
                line.mb_caution_unit = template.mb_caution or 0.0
                line.mb_value_in_case_of_theft = template.mb_value_in_case_of_theft or 0.0
                line.mb_caution_subtotal = line.mb_caution_unit * line.product_uom_qty
            else:
                line.mb_caution_unit = 0.0
                line.mb_value_in_case_of_theft = 0.0
                line.mb_caution_subtotal = 0.0
