from odoo import models, fields, api, Command
from odoo.exceptions import UserError
import base64
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # NOUVEAU : Champs pour l'intégration native Sign
    sign_request_ids = fields.One2many(
        "sign.request",
        string="Demandes de Signature",
        compute="_compute_sign_request"
    )
    sign_request_count = fields.Integer(
        "# Demandes de Signature",
        compute="_compute_sign_request"
    )
    signature_status = fields.Selection([
        ('none', 'Aucune'),
        ('sent', 'Envoyée'),
        ('signed', 'Signée')
    ], string='Statut signature', default='none')

    def _compute_sign_request(self):
        """NOUVEAU : Calculer les demandes de signature liées via reference_doc"""
        ref_values = [f"sale.order,{rec.id}" for rec in self]
        sign_data = self.env["sign.request"]._read_group(
            domain=[('reference_doc', 'in', ref_values)],
            groupby=['reference_doc'],
            aggregates=['id:recordset'],
        )

        # Initialiser
        self.sign_request_ids = False
        self.sign_request_count = 0

        # Grouper les demandes par commande
        for dummy, sign_requests in sign_data:
            if sign_requests:
                order = sign_requests[:1].reference_doc
                order.sign_request_ids = [Command.set(sign_requests.ids)]
                order.sign_request_count = len(sign_requests)

    def action_view_sign(self):
        """NOUVEAU : Action pour voir les demandes de signature"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sign.sign_request_action")

        if self.sign_request_count > 1:
            ref_values = [f"sale.order,{self.id}"]
            action["domain"] = [('reference_doc', 'in', ref_values)]
        elif self.sign_request_count == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.sign_request_ids.ids[0]
        else:
            action = {"type": "ir.actions.act_window_close"}

        return action

    def action_send_for_signature(self):
        """Votre action originale - génération automatique + signature"""
        self.ensure_one()

        if not self.partner_id.email:
            raise UserError("Le client doit avoir une adresse email pour pouvoir signer le devis.")

        try:
            # Vérifier s'il y a déjà une demande en cours pour éviter les doublons
            existing_request = self.sign_request_ids.filtered(
                lambda r: r.state == 'sent' and not r.completed_by_all()
            )

            if existing_request:
                _logger.info(f"Demande existante trouvée: {existing_request.id}")
                self.signature_status = 'sent'
                return existing_request.go_to_document()

            # Votre logique existante : générer template depuis QWeb
            sign_template = self._create_sign_template()
            _logger.info(f"Template créé: {sign_template.id}")

            # Créer la demande de signature avec la sauvegarde améliorée
            sign_request = self._create_sign_request(sign_template)
            _logger.info(f"Sign request créé: {sign_request.id}")

            # NOUVEAU : Lier via reference_doc (comme sale_rental_sign)
            sign_request.reference_doc = f"sale.order,{self.id}"

            # Générer le nom du fichier
            filename = f"Devis_{self.name}_{self.partner_id.name}.pdf"

            # Récupérer l'attachment du template (créé dans _create_sign_template)
            attachment = sign_template.attachment_id
            if not attachment:
                raise UserError("Erreur lors de la création du document PDF.")

            # Ouvrir le wizard d'envoi Sign avec nos paramètres
            action = self.env['ir.actions.act_window']._for_xml_id('sign.action_sign_send_request')
            action.update({
                "context": {
                    "default_template_id": sign_template.id,
                    "default_filename": filename,
                    "default_attachment_ids": [(6, 0, [attachment.id])],
                    "sign_directly_without_mail": True,
                    "default_res_model": "sale.order",
                    "default_res_id": self.id,
                    "default_reference_doc": f"sale.order,{self.id}",
                    "default_signers_data": [{
                        'partner_id': self.partner_id.id,
                        'role': 1,
                        'mail': self.partner_id.email,
                    }],
                },
                "target": "new",
            })

            self.signature_status = 'sent'
            return action

        except Exception as e:
            _logger.error(f"Erreur lors de l'envoi pour signature: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Erreur!',
                    'message': f'Impossible d\'envoyer le devis pour signature: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    # GARDER : Toutes vos fonctions de génération QWeb
    def _create_sign_template(self):
        """Votre logique existante - génération auto template depuis QWeb"""
        try:
            _logger.info("=== GÉNÉRATION PDF DEPUIS QWEB ===")

            # Générer le PDF depuis le rapport QWeb
            pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                'sale.report_saleorder', self.ids
            )
            _logger.info(f"PDF généré: {len(pdf_content)} bytes")

            # Créer l'attachment
            attachment = self.env['ir.attachment'].create({
                'name': f'Devis_{self.name}.pdf',
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'sale.order',
                'res_id': self.id,
                'mimetype': 'application/pdf',
            })
            _logger.info(f"Attachment créé: {attachment.id}")

            # Créer le template Sign
            template = self.env['sign.template'].create({
                'attachment_id': attachment.id,
                'name': f'Template_Devis_{self.name}',
            })
            _logger.info(f"Template créé: {template.id}")

            # Ajouter zone de signature
            self._add_signature_field(template)

            return template

        except Exception as e:
            _logger.error(f"Erreur création template: {e}")
            raise

    def _add_signature_field(self, template):
        """Votre logique existante - ajout zone signature"""
        try:
            signature_type = self.env.ref('sign.sign_item_type_signature', raise_if_not_found=False)
            customer_role = self.env.ref('sign.sign_item_role_customer', raise_if_not_found=False)

            if not signature_type or not customer_role:
                _logger.warning("Types de signature non trouvés")
                return

            _logger.info(f"Types trouvés - Signature: {signature_type.id}, Customer: {customer_role.id}")

            signature_item = self.env['sign.item'].create({
                'template_id': template.id,
                'type_id': signature_type.id,
                'required': True,
                'responsible_id': customer_role.id,
                'page': 1,
                'posX': 0.7,
                'posY': 0.8,
                'width': 0.2,
                'height': 0.05,
            })

            _logger.info(f"Zone de signature créée: {signature_item.id}")

        except Exception as e:
            _logger.error(f"Erreur ajout signature: {e}")
            raise

    def _create_sign_request(self, sign_template):
        """Votre logique existante - création demande avec items"""
        try:
            _logger.info("=== CRÉATION DEMANDE SIGNATURE ===")

            sign_request_data = {
                'template_id': sign_template.id,
                'reference': f'Signature_Devis_{self.name}',
                'subject': f'Signature du devis {self.name}',
                'message': f'Veuillez signer le devis {self.name}',
                'request_item_ids': [(0, 0, {
                    'role_id': self.env.ref('sign.sign_item_role_customer').id,
                    'partner_id': self.partner_id.id,
                    'signer_email': self.partner_id.email,
                })]
            }

            sign_request = self.env['sign.request'].create(sign_request_data)
            _logger.info(f"Sign request créé: {sign_request.id}, état: {sign_request.state}")

            return sign_request

        except Exception as e:
            _logger.error(f"Erreur création sign request: {e}")
            import traceback
            _logger.error(traceback.format_exc())
            raise
