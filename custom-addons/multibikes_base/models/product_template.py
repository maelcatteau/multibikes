# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductTemplate(models.Model):
    """
    Extension du modèle Product Template
    -----------------------------------
    Ajoute des champs pour gérer les cautions et les valeurs de remplacement
    des produits de location.
    """
    _inherit = 'product.template'

    # Champ pour la caution
    mb_caution = fields.Monetary(
        string='Caution', 
        currency_field='currency_id', 
        help="Montant de la caution à payer pour la location de ce produit."
    )
    
    # Champ pour la valeur en cas de vol
    mb_value_in_case_of_theft = fields.Monetary(
        string='Valeur en cas de vol', 
        currency_field='currency_id', 
        help="Valeur du produit en cas de vol ou de perte, utilisée pour facturer le client."
    )
    
    # Champ pour la devise
    mb_currency_id = fields.Many2one(
        'res.currency', 
        string='Devise', 
        required=True, 
        default=lambda self: self.env.company.currency_id,
        help="Devise utilisée pour les montants de caution et de valeur en cas de vol."
    )
