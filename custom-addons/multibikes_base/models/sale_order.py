# -*- coding: utf-8 -*-
"""Model SaleOrder for multibikes_base module."""
from odoo import models, fields, api


class SaleOrder(models.Model):
    """
    Extension du modèle Sale Order
    -----------------------------
    Ajoute des champs pour gérer les cautions ET les remises globales
    associés aux commandes de location.
    """

    _inherit = "sale.order"


    # Champs related modifiables pour les informations du partenaire
    partner_phone = fields.Char(
        string="Customer phone",
        related='partner_id.mobile',
        readonly=False,
        store=False,
        help="Customer's phone number"
    )

    partner_email = fields.Char(
        string="Customer Email",
        related='partner_id.email',
        readonly=False,
        store=False,
        help="Customer's email adress"
    )

    partner_lang = fields.Selection(
        string="Customer's language",
        related='partner_id.lang',
        readonly=False,
        store=False,
        help="Preferred language of the customer"
    )

    mb_type_de_caution = fields.Selection(
        selection=[
            ("espece", "Cash"),
            ("cheque", "Check"),
            ("carte_bancaire", "Credit card"),
        ],
        string="Type of deposit",
        help="Type of deposit for the rental",
    )

    mb_numero_de_caution = fields.Integer(
        string="Deposit file n°",
        help=(
            "Deposit file n° used for this rental"
            "This number is used to link with the credit card imprint"
        ),
    )

    mb_caution_total = fields.Monetary(
        string="Total deposit",
        compute="_compute_mb_caution_total",
        store=True,
        help="Total amount of the deposit for the rental",
    )

    mb_caution_discount_product_id = fields.Many2one(
        "product.product",
        string="Deposit discount",
        help="Product used for deposit discounts in the wizard",
    )

    @api.depends("order_line.mb_caution_subtotal")
    def _compute_mb_caution_total(self):
        for order in self:
            order.mb_caution_total = sum(
                line.mb_caution_subtotal or 0.0 for line in order.order_line
            )

    @api.onchange('partner_phone')
    def _onchange_partner_phone(self):
        """Synchronise le téléphone avec le partenaire"""
        if self.partner_id and self.partner_phone:
            self.partner_id.phone = self.partner_phone

    @api.onchange('partner_email')
    def _onchange_partner_email(self):
        """Synchronise l'email avec le partenaire"""
        if self.partner_id and self.partner_email:
            self.partner_id.email = self.partner_email

    @api.onchange('partner_lang')
    def _onchange_partner_lang(self):
        """Synchronise la langue avec le partenaire"""
        if self.partner_id and self.partner_lang:
            self.partner_id.lang = self.partner_lang

    @api.onchange('partner_id')
    def _onchange_partner_id_custom(self):
        """Met à jour les champs quand le partenaire change"""
        if self.partner_id:
            self.partner_phone = self.partner_id.phone
            self.partner_email = self.partner_id.email
            self.partner_lang = self.partner_id.lang