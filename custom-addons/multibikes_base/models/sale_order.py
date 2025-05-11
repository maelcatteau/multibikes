from odoo import models, fields

class SaleOrder(models.Model):
    """
    Extension du modèle Sale Order
    -----------------------------
    Ajoute des champs pour gérer les numéros de dossier de caution
    associés aux commandes de location.
    """
    _inherit = 'sale.order'

    mb_numero_de_caution = fields.Integer(
        string="Numéro du dossier de caution",
        help="Numéro du dossier de caution pour la location. Ce numéro est utilisé pour faire le lien aavec l'empreinte de carte"
    )