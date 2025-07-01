from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SignRequest(models.Model):
    _inherit = 'sign.request'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Commande de vente',
        compute='_compute_sale_order_id',
        store=True
    )


    @api.depends('reference_doc')
    def _compute_sale_order_id(self):
        """Extraire l'ID de sale.order depuis reference_doc"""
        for record in self:
            if (record.reference_doc and
                hasattr(record.reference_doc, '_name') and
                record.reference_doc._name == 'sale.order'):
                record.sale_order_id = record.reference_doc.id
            else:
                record.sale_order_id = False

    def _message_post_after_sign(self):
        """Appelé après signature - logique améliorée"""
        super()._message_post_after_sign()

        # NOUVEAU : Gestion via reference_doc (comme sale_rental_sign)
        if (hasattr(self, 'reference_doc') and
            self.reference_doc and
            self.reference_doc._name == 'sale.order'):

            self._handle_signed_quotation()

    def _handle_signed_quotation(self):
        """Traiter le devis après signature"""
        try:
            order = self.reference_doc

            # Mettre à jour le statut
            order.signature_status = 'signed'

            # Optionnel : Confirmer automatiquement le devis
            if order.state in ['draft', 'sent']:
                order.action_confirm()
                _logger.info(f"Devis {order.name} confirmé automatiquement après signature")

            # Notification sur la commande
            order.message_post(
                body=f"✅ Le devis a été signé avec succès. Document signé disponible dans les demandes de signature.",
                message_type='notification'
            )

            _logger.info(f"Devis signé traité: {order.name}")

        except Exception as e:
            _logger.error(f"Erreur traitement devis signé: {e}")

    def _get_linked_record_action(self, default_action=None):
        """NOUVEAU : Retourner vers le bon devis (comme sale_rental_sign)"""
        self.ensure_one()
        if self.reference_doc and self.reference_doc._name == 'sale.order':
            action = self.env['ir.actions.act_window']._for_xml_id('sale.action_orders')
            action.update({
                "views": [(False, "form")],
                "view_mode": 'form',
                "res_id": self.reference_doc.id,
            })
            return action
        else:
            return super()._get_linked_record_action(default_action=default_action)
