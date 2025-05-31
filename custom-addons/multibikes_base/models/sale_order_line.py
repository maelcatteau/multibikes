# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    # Champs reliés sur le produit
    mb_caution_unit = fields.Monetary(
        string='Caution unitaire',
        related='product_id.mb_caution',
        currency_field='currency_id',
        readonly=True,
        store=True, 
        help="Montant de la caution unitaire",
        precompute=True
    )
    
    mb_value_in_case_of_theft = fields.Monetary(
        string='Valeur en cas de vol',
        related='product_id.mb_value_in_case_of_theft',
        currency_field='currency_id',
        readonly=True,
        store=True,  
        help="Valeur du produit en cas de vol"
    )
    
    mb_caution_subtotal = fields.Monetary(
        string='Caution totale',
        compute='_compute_mb_subtotal',
        store=True,
        currency_field='currency_id',
        help="Montant total de la caution (caution unitaire × quantité)",
        precompute=True,
    )
    
    @api.depends('mb_caution_unit', 'product_uom_qty')
    def _compute_mb_subtotal(self):
        for line in self:
            caution = line.mb_caution_unit or 0.0
            qty = line.product_uom_qty or 0.0
            line.mb_caution_subtotal = caution * qty
