# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError

class SaleOrderDiscount(models.TransientModel):
    _inherit = 'sale.order.discount'

    # Champs pour la caution
    caution_discount_amount = fields.Monetary(string="Caution Discount Amount")
    apply_caution_discount = fields.Boolean(string="Apply Caution Discount")

    def _get_caution_discount_product(self):
        """Return product.product used for caution discount line"""
        self.ensure_one()
        caution_discount_product = self.sale_order_id.mb_caution_discount_product_id
        if not caution_discount_product:
            if (
                self.env['product.product'].has_access('create')
                and self.sale_order_id.has_access('write')
                and self.sale_order_id._filtered_access('write')
                and self.sale_order_id.check_field_access_rights('write', ['mb_caution_discount_product_id'])
            ):
                caution_discount_product_vals = {
                    'name': _('Remise Caution'),
                    'type': 'service',
                    'invoice_policy': 'order',
                    'list_price': 0.0,
                    'mb_caution': 0.0,  # Ajouter ce champ
                    'company_id': self.company_id.id,
                    'taxes_id': None,
                }
                caution_discount_product = self.env['product.product'].create(caution_discount_product_vals)
                self.sale_order_id.mb_caution_discount_product_id = caution_discount_product
            else:
                raise ValidationError(_(
                    "There does not seem to be any caution discount product configured for this order yet."
                    " Please ask an administrator to configure it first."
                ))
        return caution_discount_product

    def _create_caution_discount_line(self):
        """Create SOline for caution discount"""
        self.ensure_one()
        if not self.apply_caution_discount or not self.caution_discount_amount:
            return

        caution_discount_product = self._get_caution_discount_product()
        
        # Mettre à jour le champ mb_caution du produit avec la valeur de remise
        caution_discount_product.write({'mb_caution': -self.caution_discount_amount})
        
        vals = {
            'order_id': self.sale_order_id.id,
            'product_id': caution_discount_product.id,
            'sequence': 999,
            'name': _('Caution Discount'),
        }
        
        return self.env['sale.order.line'].create(vals)


    def action_apply_discount(self):
        # Appliquer les remises de prix existantes
        result = super().action_apply_discount()
        
        # Appliquer la remise sur caution si nécessaire
        if self.apply_caution_discount:
            self._create_caution_discount_line()
        
        return result
