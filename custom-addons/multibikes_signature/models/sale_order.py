from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sign_request_id = fields.Many2one('sign.request', string='Demande de signature', readonly=True)

    def action_send_for_signature(self):
        """Envoyer le devis pour signature - Version avec gestion d'états"""
        self.ensure_one()

        if not self.partner_id.email:
            raise UserError("Le client doit avoir une adresse email pour recevoir la demande de signature.")

        try:
            # Générer le PDF
            pdf_content = self._generate_quotation_pdf()

            # Créer le template de signature
            sign_template = self._create_sign_template(pdf_content)

            # Créer la demande de signature
            sign_request = self._create_sign_request(sign_template)

            # Lier la demande au devis
            self.sign_request_id = sign_request.id

            # CORRECTION: Gestion intelligente des états
            _logger.info(f"État initial: {sign_request.state}")

            # Vérifier si on peut changer l'état
            try:
                # Option 1: Méthode spécifique
                if hasattr(sign_request, 'action_sent') and callable(getattr(sign_request, 'action_sent')):
                    sign_request.action_sent()
                    _logger.info("Utilisé action_sent()")

                # Option 2: Changement d'état direct si pas d'autres contraintes
                elif sign_request.state == 'draft':
                    # Vérifier que tous les prérequis sont remplis
                    if len(sign_request.request_item_ids) > 0 and len(sign_request.template_id.sign_item_ids) > 0:
                        sign_request.write({'state': 'sent'})
                        _logger.info("État changé manuellement à 'sent'")
                    else:
                        _logger.warning("Prérequis non remplis pour l'envoi")

            except Exception as state_error:
                _logger.error(f"Impossible de changer l'état: {state_error}")
                # On continue mais on laisse en draft

            _logger.info(f"État final: {sign_request.state}")

            return {
                'type': 'ir.actions.act_window',
                'name': 'Demande de signature',
                'res_model': 'sign.request',
                'res_id': sign_request.id,
                'view_mode': 'form',
                'target': 'current',
            }

        except Exception as e:
            _logger.error(f"Erreur lors de l'envoi pour signature: {e}")
            import traceback
            _logger.error(traceback.format_exc())
            raise UserError(f"Impossible d'envoyer le devis pour signature: {e}")

    def _generate_quotation_pdf(self):
        """Version simple inspirée du code account"""
        try:
            # Utiliser exactement la même approche que dans votre code account
            report = self.env['ir.actions.report']

            # Préparer les données comme dans _get_rendering_context
            data = {
                'doc_ids': [self.id],
                'doc_model': 'sale.order',
                'docs': self.browse([self.id]),
            }

            # Pré-traitement comme dans _pre_render_qweb_pdf
            report_ref = self.env.ref('sale.action_report_saleorder')

            # Générer le PDF
            pdf_content = report._render_qweb_pdf(
                report_ref,
                res_ids=[self.id],
                data=data
            )

            # Traiter le résultat
            if isinstance(pdf_content, tuple):
                pdf_data = pdf_content[0]
            else:
                pdf_data = pdf_content

            _logger.info(f"PDF généré: {len(pdf_data)} bytes")
            return base64.b64encode(pdf_data).decode('utf-8')

        except Exception as e:
            _logger.error(f"Erreur génération PDF: {e}")
            raise UserError(f"Impossible de générer le PDF: {e}")

    def _create_sign_template(self, pdf_content):
        """Créer un template de signature - Version corrigée"""
        try:
            _logger.info("=== CRÉATION TEMPLATE SIGNATURE ===")

            # Créer l'attachment pour le PDF
            attachment = self.env['ir.attachment'].create({
                'name': f'Devis_{self.name}.pdf',
                'type': 'binary',
                'datas': pdf_content,
                'res_model': 'sale.order',
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            _logger.info(f"Attachment créé: {attachment.id}")

            # Créer le template de signature
            sign_template = self.env['sign.template'].create({
                'name': f'Template_Devis_{self.name}',
                'attachment_id': attachment.id,
                'active': True,  # Assurer que le template est actif
            })
            _logger.info(f"Template créé: {sign_template.id}")

            # CORRECTION 1: Vérifier que les références existent
            try:
                signature_type = self.env.ref('sign.sign_item_type_signature')
                customer_role = self.env.ref('sign.sign_item_role_customer')
                _logger.info(f"Types trouvés - Signature: {signature_type.id}, Customer: {customer_role.id}")
            except Exception as e:
                _logger.error(f"Erreur références: {e}")
                # Chercher manuellement si les refs n'existent pas
                signature_type = self.env['sign.item.type'].search([('name', 'ilike', 'signature')], limit=1)
                customer_role = self.env['sign.item.role'].search([('name', 'ilike', 'customer')], limit=1)

                if not signature_type:
                    signature_type = self.env['sign.item.type'].search([], limit=1)
                if not customer_role:
                    customer_role = self.env['sign.item.role'].search([], limit=1)

            # CORRECTION 2: Ajouter une zone de signature avec des valeurs plus robustes
            sign_item = self.env['sign.item'].create({
                'template_id': sign_template.id,
                'type_id': signature_type.id,
                'required': True,
                'responsible_id': customer_role.id,
                'page': 1,
                'posX': 0.65,  # Position X (65% de la largeur)
                'posY': 0.75,  # Position Y (75% de la hauteur)
                'width': 0.25,  # Largeur (25% de la page)
                'height': 0.12, # Hauteur (12% de la page)
                'name': 'signature_client',
            })
            _logger.info(f"Zone de signature créée: {sign_item.id}")

            return sign_template

        except Exception as e:
            _logger.error(f"Erreur création template: {e}")
            import traceback
            _logger.error(traceback.format_exc())
            raise

    def _create_sign_request(self, sign_template):
        """Créer une demande de signature avec les items en une seule fois"""
        try:
            _logger.info("=== CRÉATION DEMANDE SIGNATURE ===")

            # CORRECTION: Créer la demande avec les items directement
            sign_request_data = {
                'template_id': sign_template.id,
                'reference': f'Signature_Devis_{self.name}',
                'subject': f'Signature du devis {self.name}',
                'message': f'Veuillez signer le devis {self.name}',
                # Créer les items en même temps
                'request_item_ids': [(0, 0, {
                    'role_id': self.env.ref('sign.sign_item_role_customer').id,
                    'partner_id': self.partner_id.id,
                    'signer_email': self.partner_id.email,
                })]
            }

            sign_request = self.env['sign.request'].create(sign_request_data)
            _logger.info(f"Sign request créé: {sign_request.id}, état: {sign_request.state}")
            _logger.info(f"Nombre d'items: {len(sign_request.request_item_ids)}")

            return sign_request

        except Exception as e:
            _logger.error(f"Erreur création sign request: {e}")
            import traceback
            _logger.error(traceback.format_exc())
            raise

    def _debug_sign_request_states(self, sign_request):
        """Debug pour voir les états et méthodes disponibles"""
        try:
            _logger.info("=== DEBUG ÉTATS SIGNATURE ===")

            # États de la demande
            if hasattr(sign_request, '_fields') and 'state' in sign_request._fields:
                state_field = sign_request._fields['state']
                if hasattr(state_field, 'selection'):
                    if callable(state_field.selection):
                        try:
                            states = state_field.selection(sign_request)
                            _logger.info(f"États sign.request possibles: {states}")
                        except:
                            _logger.info("États sign.request: fonction dynamique")
                    else:
                        _logger.info(f"États sign.request possibles: {state_field.selection}")

            # Méthodes disponibles
            methods = [m for m in dir(sign_request) if not m.startswith('_') and ('sent' in m.lower() or 'send' in m.lower() or 'sign' in m.lower())]
            _logger.info(f"Méthodes signature disponibles: {methods}")

            # Vérifier les items
            _logger.info(f"Nombre d'items: {len(sign_request.request_item_ids)}")
            for item in sign_request.request_item_ids:
                _logger.info(f"Item: partner={item.partner_id.name}, mail={item.mail}, état={getattr(item, 'state', 'N/A')}")

        except Exception as e:
            _logger.error(f"Erreur debug états: {e}")