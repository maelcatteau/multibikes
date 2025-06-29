# -*- coding: utf-8 -*-
"""Model SaleOrderLine for multibikes_base module."""
from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Champs reliés sur le produit
    mb_caution_unit = fields.Monetary(
        string="Unit deposit",
        related="product_id.mb_caution",
        currency_field="currency_id",
        readonly=True,
        store=True,
        help="Amount of the unit deposit",
        precompute=True,
    )

    mb_value_in_case_of_theft = fields.Monetary(
        string="Value in case of theft",
        related="product_id.mb_value_in_case_of_theft",
        currency_field="currency_id",
        readonly=True,
        store=True,
        help="Value of the product in case of theft or loss",
    )

    mb_caution_subtotal = fields.Monetary(
        string="Total deposit",
        compute="_compute_mb_subtotal",
        store=True,
        currency_field="currency_id",
        help="Total amount of the deposit (unit deposit x quantity)",
        precompute=True,
    )

    @api.depends("mb_caution_unit", "product_uom_qty")
    def _compute_mb_subtotal(self):
        for line in self:
            caution = line.mb_caution_unit or 0.0
            qty = line.product_uom_qty or 0.0
            line.mb_caution_subtotal = caution * qty
