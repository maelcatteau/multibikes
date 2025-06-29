from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SignRequest(models.Model):
    _inherit = 'sign.request'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Commande',
        help='Commande liée à cette demande de signature'
    )

    def _message_post_after_sign(self):
        """Appelé après signature - Actions post-signature"""
        super()._message_post_after_sign()

        # Si c'est lié à une commande, effectuer les actions nécessaires
        if self.sale_order_id:
            self._handle_signed_quotation()

    def _handle_signed_quotation(self):
        """Traiter le devis après signature"""
        try:
            # Mettre à jour le statut de signature
            self.sale_order_id.signature_status = 'signed'

            # Optionnel : Confirmer automatiquement le devis
            if self.sale_order_id.state in ['draft', 'sent']:
                self.sale_order_id.action_confirm()
                _logger.info(f"Devis {self.sale_order_id.name} confirmé automatiquement après signature")

            # Log pour suivi
            _logger.info(f"Devis signé traité: {self.sale_order_id.name}")

            # Optionnel : Envoyer notification
            self._send_signature_notification()

        except Exception as e:
            _logger.error(f"Erreur traitement devis signé: {e}")

    def _send_signature_notification(self):
        """Envoyer notification après signature (optionnel)"""
        try:
            # Notification interne
            self.sale_order_id.message_post(
                body=f"✅ Le devis a été signé avec succès. Document disponible dans la demande de signature.",
                message_type='notification'
            )
        except Exception as e:
            _logger.error(f"Erreur notification: {e}")
