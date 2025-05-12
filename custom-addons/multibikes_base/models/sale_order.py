from odoo import models, fields

class SaleOrder(models.Model):
    """
    Extension du modèle Sale Order
    -----------------------------
    Ajoute des champs pour gérer les cautions
    associés aux commandes de location.
    """
    _inherit = 'sale.order'

    mb_type_de_caution = fields.Selection(
        selection=[
            ('espece', 'Espèces'),
            ('cheque', 'Chèque'),
            ('carte_bancaire', 'Carte Bancaire')
        ],
        string="Type de caution",
        help="Type de caution pour la location"
    )
    
    
    mb_numero_de_caution = fields.Integer(
        string="Numéro du dossier de caution",
        help="Numéro du dossier de caution pour la location. Ce numéro est utilisé pour faire le lien aavec l'empreinte de carte"
    )