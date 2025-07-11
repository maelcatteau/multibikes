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
        "sale_order_id",
        string="Demandes de Signature"
    )
    sign_request_count = fields.Integer(
        "# Demandes de Signature",
        compute="_compute_sign_request",
        store=True
    )

    # AMÉLIORÉ : Champ computed pour le statut de signature
    signature_status = fields.Selection([
        ('none', 'Aucune'),
        ('sent', 'Envoyée'),
        ('signed', 'Signée'),
        ('completed', 'Complétée'),
        ('cancelled', 'Annulée')
    ], string='Statut signature', compute='_compute_signature_status', store=True)

    @api.depends('sign_request_ids', 'sign_request_ids.state')
    def _compute_sign_request(self):
        """Calculer les demandes de signature liées via reference_doc"""
        ref_values = [f"sale.order,{rec.id}" for rec in self]

        if not ref_values:
            self.update({
                'sign_request_ids': False,
                'sign_request_count': 0
            })
            return

        sign_data = self.env["sign.request"]._read_group(
            domain=[('reference_doc', 'in', ref_values)],
            groupby=['reference_doc'],
            aggregates=['id:recordset'],
        )

        # Initialiser tous les enregistrements
        for order in self:
            order.sign_request_ids = False
            order.sign_request_count = 0

        # Grouper les demandes par commande
        for reference_doc, sign_requests in sign_data:
            if sign_requests and reference_doc:
                # Extraire l'ID de la commande depuis la référence
                try:
                    model, res_id = reference_doc.split(',')
                    if model == 'sale.order':
                        order = self.browse(int(res_id))
                        if order.exists():
                            order.sign_request_ids = [Command.set(sign_requests.ids)]
                            order.sign_request_count = len(sign_requests)
                except (ValueError, AttributeError):
                    _logger.warning(f"Référence invalide: {reference_doc}")
                    continue

    @api.depends('sign_request_ids.state', 'sign_request_ids.request_item_ids.state')
    def _compute_signature_status(self):
        """Calculer le statut de signature basé sur les demandes"""
        for order in self:
            if not order.sign_request_ids:
                order.signature_status = 'none'
                continue

            # Récupérer toutes les demandes actives (non supprimées)
            active_requests = order.sign_request_ids.filtered(lambda r: r.state != 'canceled')

            if not active_requests:
                order.signature_status = 'cancelled'
                continue

            # Analyser les états des demandes
            states = active_requests.mapped('state')

            # Vérifier l'état des items de signature
            all_request_items = active_requests.mapped('request_item_ids')
            item_states = all_request_items.mapped('state')

            # Logique de détermination du statut
            if 'completed' in states:
                order.signature_status = 'completed'
            elif 'signed' in item_states or any(item.state == 'completed' for item in all_request_items):
                order.signature_status = 'signed'
            elif 'sent' in states:
                order.signature_status = 'sent'
            else:
                order.signature_status = 'none'

    def _get_signature_status_info(self):
        """Méthode utilitaire pour obtenir des informations détaillées sur le statut"""
        self.ensure_one()

        if not self.sign_request_ids:
            return {
                'status': 'none',
                'message': 'Aucune demande de signature',
                'details': {}
            }

        active_requests = self.sign_request_ids.filtered(lambda r: r.state != 'canceled')

        if not active_requests:
            return {
                'status': 'cancelled',
                'message': 'Toutes les demandes ont été annulées',
                'details': {'cancelled_count': len(self.sign_request_ids)}
            }

        # Informations détaillées
        details = {
            'total_requests': len(active_requests),
            'completed_requests': len(active_requests.filtered(lambda r: r.state == 'completed')),
            'sent_requests': len(active_requests.filtered(lambda r: r.state == 'sent')),
            'signers': []
        }

        # Informations sur les signataires
        for request in active_requests:
            for item in request.request_item_ids:
                details['signers'].append({
                    'email': item.signer_email,
                    'state': item.state,
                    'signed_date': item.signing_date,
                    'partner_name': item.partner_id.name if item.partner_id else 'Inconnu'
                })

        status_messages = {
            'completed': 'Signature complétée',
            'signed': 'Signature en cours',
            'sent': 'Demande envoyée',
            'none': 'Pas de signature'
        }

        return {
            'status': self.signature_status,
            'message': status_messages.get(self.signature_status, 'Statut inconnu'),
            'details': details
        }

    def action_view_sign(self):
        """Action pour voir les demandes de signature avec gestion des cas vides"""
        self.ensure_one()

        if not self.sign_request_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Aucune signature',
                    'message': 'Aucune demande de signature trouvée pour cette commande.',
                    'type': 'info',
                }
            }

        action = self.env["ir.actions.actions"]._for_xml_id("sign.sign_request_action")

        if self.sign_request_count > 1:
            ref_values = [f"sale.order,{self.id}"]
            action["domain"] = [('reference_doc', 'in', ref_values)]
            action["context"] = {'default_reference_doc': f"sale.order,{self.id}"}
        elif self.sign_request_count == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.sign_request_ids.ids[0]

        return action

    def action_send_signature_by_email(self):
        """Envoie la demande de signature par email avec vérification de statut"""
        self.ensure_one()

        if not self.partner_id.email:
            raise UserError("Le client doit avoir une adresse email pour pouvoir signer le devis.")

        # Vérifier le statut actuel
        current_status = self.signature_status

        if current_status in ['signed', 'completed']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Signature déjà effectuée',
                    'message': 'Ce devis a déjà été signé.',
                    'type': 'warning',
                }
            }

        if current_status == 'sent':
            # Permettre le renvoi mais avec avertissement
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Demande déjà envoyée',
                    'message': 'Une demande de signature a déjà été envoyée. Voulez-vous la renvoyer ?',
                    'type': 'warning',
                }
            }

        try:
            # Vérifier s'il y a déjà une demande en cours
            existing_request = self.sign_request_ids.filtered(lambda r: r.state != 'canceled')

            if existing_request:
                _logger.info(f"Demande existante trouvée: {existing_request.ids}")
                # Renvoyer la demande existante plutôt que d'en créer une nouvelle
                existing_request.action_send()
            else:
                # Créer template et demande
                sign_template = self._create_sign_template()
                sign_request = self._create_sign_request(sign_template)
                sign_request.reference_doc = f"sale.order,{self.id}"

            # Le statut sera automatiquement mis à jour par _compute_signature_status
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Email envoyé!',
                    'message': f'La demande de signature a été envoyée à {self.partner_id.email}',
                    'type': 'success',
                }
            }

        except Exception as e:
            _logger.error(f"Erreur lors de l'envoi par email: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Erreur!',
                    'message': f'Impossible d\'envoyer le devis par email: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    def _create_sign_template(self):
        """Votre logique existante - génération auto template depuis QWeb"""
        try:
            _logger.info("=== GÉNÉRATION PDF DEPUIS QWEB ===")

            # Générer le PDF depuis le rapport QWeb
            pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                'multibikes_base.report_rental_contract', self.ids
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
        """Ajouter zone signature + case à cocher sur la dernière page"""
        try:
            signature_type = self.env.ref('sign.sign_item_type_signature', raise_if_not_found=False)
            checkbox_type = self.env.ref('sign.sign_item_type_checkbox', raise_if_not_found=False)
            customer_role = self.env.ref('sign.sign_item_role_customer', raise_if_not_found=False)

            if not signature_type or not customer_role or not checkbox_type:
                _logger.warning("Types de signature/checkbox non trouvés")
                return

            _logger.info(f"Types trouvés - Signature: {signature_type.id}, Checkbox: {checkbox_type.id}, Customer: {customer_role.id}")

            # Déterminer le nombre de pages du PDF
            last_page = self._get_pdf_page_count(template)

            _logger.info(f"Nombre de pages détecté: {last_page}")

            # 1. Créer la case à cocher AVANT la signature
            checkbox_item = self.env['sign.item'].create({
                'template_id': template.id,
                'type_id': checkbox_type.id,
                'required': True,
                'responsible_id': customer_role.id,
                'page': last_page,
                'posX': 0.06,  # Position à gauche
                'posY': 0.475,  # Un peu plus haut que la signature
                'width': 0.019,  # Petite case
                'height': 0.019,
                'name': 'accept_conditions',  # Nom unique pour la case
            })

            # 2. Créer la zone de signature
            signature_item = self.env['sign.item'].create({
                'template_id': template.id,
                'type_id': signature_type.id,
                'required': True,
                'responsible_id': customer_role.id,
                'page': last_page,
                'posX': 0.66,   # Position à droite
                'posY': 0.75,   # En dessous de la case
                'width': 0.2,
                'height': 0.05,
                'name': 'customer_signature',  # Nom unique pour la signature
            })

            _logger.info(f"Case à cocher créée: {checkbox_item.id}")
            _logger.info(f"Zone de signature créée: {signature_item.id}")

        except Exception as e:
            _logger.error(f"Erreur ajout signature/checkbox: {e}")
            raise


    def _get_pdf_page_count(self, template):
        """Déterminer le nombre de pages du PDF avec pdfminer"""
        try:
            if not template.attachment_id:
                _logger.warning("Aucun attachment trouvé sur le template")
                return self._estimate_last_page()

            # Utiliser pdfminer pour compter les pages
            try:
                from pdfminer.high_level import extract_pages
                import io

                # Décoder le PDF
                pdf_data = base64.b64decode(template.attachment_id.datas)
                pdf_file = io.BytesIO(pdf_data)

                # Compter les pages avec pdfminer
                pages = list(extract_pages(pdf_file))
                page_count = len(pages)

                _logger.info(f"Nombre de pages via pdfminer: {page_count}")
                return page_count

            except ImportError:
                _logger.warning("pdfminer non disponible, utilisation de l'estimation")
                return self._estimate_last_page()
            except Exception as e:
                _logger.error(f"Erreur pdfminer: {e}")
                return self._estimate_last_page()

        except Exception as e:
            _logger.error(f"Erreur détection pages PDF: {e}")
            return self._estimate_last_page()

    def _estimate_last_page(self):
        """Estimer la dernière page basée sur le contenu du contrat"""
        try:
            # Logique d'estimation basée sur le nombre de lignes de commande
            line_count = len(self.order_line)

            # Estimation basée sur la structure de ton rapport :
            # Page 1 : En-tête + informations client + début tableau
            # Page 2 : Suite tableau + conditions générales
            # Page 3+ : Fin conditions générales + médiation + signatures

            if line_count <= 8:
                # Commande simple : tout tient sur 3 pages
                return 3
            elif line_count <= 15:
                # Commande moyenne : 4 pages
                return 4
            elif line_count <= 25:
                # Grosse commande : 5 pages
                return 5
            else:
                # Très grosse commande : 6 pages
                return 6

        except Exception as e:
            _logger.error(f"Erreur estimation pages: {e}")
            return 3  # Valeur par défaut sécurisée


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