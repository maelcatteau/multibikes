# -*- coding: utf-8 -*-
"""Model ProductTemplate for multibikes_base module."""
from odoo import models, fields


class ProductTemplate(models.Model):
    """
    Extension du modèle Product Template
    -----------------------------------
    Ajoute des champs pour gérer les cautions et les valeurs de remplacement
    des produits de location.
    """

    _inherit = "product.template"

    # Champ pour la caution
    mb_caution = fields.Monetary(
        string="Deposit",
        currency_field="currency_id",
        help="Amount of deposit for renting this product",
    )

    # Champ pour la valeur en cas de vol
    mb_value_in_case_of_theft = fields.Monetary(
        string="Value in case of theft",
        currency_field="currency_id",
        help=(
            "Value of the product in case of theft or loss, "
            "used to bill the customer."
        ),
    )

    # Champs pour la taille
    mb_size_min = fields.Float(
        string="Minimal size (cm)",
        help="Minimal size of the cyclist in cm",
    )

    mb_size_max = fields.Float(
        string="Maximal size (cm)",
        help="Maximal size of the cyclist in cm",
    )
