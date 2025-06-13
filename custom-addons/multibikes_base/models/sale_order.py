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


    partner_phone = fields.Char(
        string="Téléphone client",
        related='partner_id.mobile',
        readonly=True,
        store=False
    )
    
    mb_type_de_caution = fields.Selection(
        selection=[
            ("espece", "Espèces"),
            ("cheque", "Chèque"),
            ("carte_bancaire", "Carte Bancaire"),
        ],
        string="Type de caution",
        help="Type de caution pour la location",
    )

    mb_numero_de_caution = fields.Integer(
        string="Numéro du dossier de caution",
        help=(
            "Numéro du dossier de caution pour la location."
            "Ce numéro est utilisé pour faire le lien avec l'empreinte de carte"
        ),
    )

    mb_caution_total = fields.Monetary(
        string="Caution totale",
        compute="_compute_mb_caution_total",
        store=True,
        help="Montant total de la caution pour la location",
    )

    mb_caution_discount_product_id = fields.Many2one(
        "product.product",
        string="Produit remise caution",
        help="Produit utilisé pour les remises de caution dans le wizard",
    )

    @api.depends("order_line.mb_caution_subtotal")
    def _compute_mb_caution_total(self):
        for order in self:
            order.mb_caution_total = sum(
                line.mb_caution_subtotal or 0.0 for line in order.order_line
            )
