# -*- coding: utf-8 -*-
"""Model Stock Picking for Multibikes Website Module."""
from datetime import timedelta
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError, MissingError


_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # === Champs ===
    is_period_transfer = fields.Boolean(
        string="Transfert de période",
        default=False,
        help="Indique si ce transfert fait partie"
        " d'un transfert saisonnier automatique",
        copy=False,
        readonly=True,  # Protégé dans l'interface
    )

    period_config_id = fields.Many2one(
        "mb.renting.stock.period.config",
        string="Configuration de période",
        help="Configuration de période associée à ce transfert",
        copy=False,
        ondelete="set null",
        readonly=True,  # Protégé dans l'interface
    )

    # Nouveau champ pour identifier les transferts ratés
    has_failed_products = fields.Boolean(
        string="Transfert partiellement raté",
        default=False,
        help="Indique si certains produits du transfert n'ont pas pu être traités",
        compute="_compute_has_failed_products",
        store=True,
    )

    failed_product_details = fields.Text(
        string="Détails des échecs produits",
        help="Liste des produits qui n'ont pas pu être transférés avec les quantités",
        compute="_compute_failed_product_details",
        store=True,
    )

    # === Champs calculés pour l'analyse des échecs ===

    @api.depends(
        "move_ids",
        "move_ids.state",
        "move_ids.product_uom_qty",
        "move_ids.move_line_ids",
        "move_ids.move_line_ids.qty_done",
        "state",
    )
    def _compute_has_failed_products(self):
        """Détermine si le transfert a des produits en échec"""
        for picking in self:
            if not picking.is_period_transfer:
                picking.has_failed_products = False
                continue

            has_failures = False

            if picking.state in [
                "draft",
                "waiting",
                "confirmed",
                "partially_available",
            ]:
                # Vérifier si certains mouvements n'ont pas assez de stock réservé
                for move in picking.move_ids:
                    if move.state not in ["done", "cancel"]:
                        # Calculer la quantité effectivement réservée via les move_lines
                        reserved_qty = sum(move.move_line_ids.mapped("quantity"))
                        if move.product_uom_qty > reserved_qty:
                            has_failures = True
                            break

                # Ou si le transfert est en retard
                if not has_failures and picking.scheduled_date:
                    now = fields.Datetime.now()
                    if picking.scheduled_date < now - timedelta(hours=2):
                        has_failures = True

            picking.has_failed_products = has_failures

    @api.depends(
        "move_ids",
        "move_ids.state",
        "move_ids.product_uom_qty",
        "move_ids.move_line_ids",
        "move_ids.move_line_ids.qty_done",
    )
    def _compute_failed_product_details(self):
        """Calcule les détails des produits en échec"""
        for picking in self:
            if not picking.is_period_transfer:
                picking.failed_product_details = ""
                continue

            failed_details = []

            for move in picking.move_ids:
                if move.state not in ["done", "cancel"]:
                    qty_expected = move.product_uom_qty

                    # Quantité réservée = somme des quantités dans les move_lines
                    qty_reserved = sum(move.move_line_ids.mapped("quantity"))

                    # Quantité effectivement faite =
                    # somme des qty_done dans les move_lines
                    qty_done = sum(move.move_line_ids.mapped("qty_done"))

                    if qty_expected > qty_reserved:
                        shortage = qty_expected - qty_reserved
                        failed_details.append(
                            f"• {move.product_id.name}"
                            f" (Réf: {move.product_id.default_code or 'N/A'}): "
                            f"Manque {shortage} sur {qty_expected} attendues"
                            f" (réservé: {qty_reserved}, fait: {qty_done})"
                        )

            # Ajouter info sur le retard si applicable
            if picking.scheduled_date and not failed_details:
                now = fields.Datetime.now()
                if picking.scheduled_date < now - timedelta(hours=2):
                    delay_hours = (now - picking.scheduled_date).total_seconds() / 3600
                    failed_details.append(
                        f"⚠️ Transfert en retard de {delay_hours:.1f} heures"
                    )

            picking.failed_product_details = (
                "\n".join(failed_details) if failed_details else ""
            )

    # === Méthodes de détection des transferts ratés ===

    @api.model
    def detect_failed_transfers(self):
        """
        Méthode utilitaire qui détecte les transferts ratés et retourne une liste d'IDs

        Returns:
            list: Liste des IDs des transferts (stock.picking) considérés comme échoués
        """
        _logger.info("🔍 Début de la détection des transferts ratés")

        failed_transfer_ids = []
        now = fields.Datetime.now()

        # Définir la tolérance (par exemple 2 heures après l'heure programmée)
        tolerance_hours = 2
        cutoff_datetime = now - timedelta(hours=tolerance_hours)

        # Rechercher les transferts automatiques potentiellement ratés
        domain = [
            ("is_period_transfer", "=", True),  # Transferts de période
            ("scheduled_date", "<=", cutoff_datetime),  # Date programmée dépassée
            ("state", "in", ["draft", "waiting", "confirmed", "partially_available"]),
        ]

        failed_pickings = self.search(domain)

        for picking in failed_pickings:
            # Vérifications supplémentaires pour confirmer l'échec
            scheduled_date = picking.scheduled_date
            delay_hours = (now - scheduled_date).total_seconds() / 3600

            # Log détaillé pour diagnostic
            _logger.warning("🚨 Transfert raté détecté: %s", picking.name)
            _logger.warning("   - Date programmée: %s", scheduled_date)
            _logger.warning("   - Retard: %.1f heures", delay_hours)
            _logger.warning("   - État actuel: %s", picking.state)
            _logger.warning("   - Origine: %s", picking.origin)

            # Analyser les détails des échecs par produit
            failed_products = self._analyze_product_failures(picking)
            if failed_products:
                _logger.error("   - Problèmes de stock détectés:")
                for product_issue in failed_products:
                    _logger.error(
                        "     * %s : besoin %s, réservé %s, manque %s",
                        product_issue["product"],
                        product_issue["needed"],
                        product_issue["reserved"],
                        product_issue["shortage"],
                    )

            failed_transfer_ids.append(picking.id)

        _logger.info(
            "🔍 Détection terminée: %s transferts ratés trouvés",
            len(failed_transfer_ids),
        )

        # Si des transferts ratés sont trouvés, log un résumé
        if failed_transfer_ids:
            _logger.error(
                "🚨 ALERTE: %s transferts sont en échec!", len(failed_transfer_ids)
            )
            _logger.error("   IDs concernés: %s", failed_transfer_ids)

            # Notifier les échecs
            self._notify_failed_transfers(failed_transfer_ids)

        return failed_transfer_ids

    def _analyze_product_failures(self, picking):
        """
        Analyse les échecs par produit pour un transfert donné

        Args:
            picking: Enregistrement stock.picking à analyser

        Returns:
            list: Liste des dictionnaires décrivant les échecs par produit
        """
        failed_products = []

        for move in picking.move_ids:
            if move.state in ["waiting", "confirmed", "partially_available"]:
                # Calculer les quantités via les move_lines
                reserved_qty = sum(move.move_line_ids.mapped("quantity"))
                done_qty = sum(move.move_line_ids.mapped("qty_done"))
                needed_qty = move.product_uom_qty

                if needed_qty > reserved_qty:
                    shortage = needed_qty - reserved_qty
                    failed_products.append(
                        {
                            "move_id": move.id,
                            "product": move.product_id.name,
                            "product_id": move.product_id.id,
                            "product_code": move.product_id.default_code or "N/A",
                            "needed": needed_qty,
                            "reserved": reserved_qty,
                            "done": done_qty,
                            "shortage": shortage,
                            "location_src": move.location_id.name,
                            "location_dest": move.location_dest_id.name,
                        }
                    )

        return failed_products

    def get_failed_products_for_virtualization(self):
        """
        Retourne les détails des produits en échec pour la virtualisation

        Returns:
            dict: Dictionnaire avec les détails des échecs pour virtualisation
        """
        self.ensure_one()

        if not self.is_period_transfer:
            return {}

        failed_products = self._analyze_product_failures(self)

        virtualization_data = {
            "picking_id": self.id,
            "picking_name": self.name,
            "period_config_id": (
                self.period_config_id.id if self.period_config_id else False
            ),
            "scheduled_date": self.scheduled_date,
            "current_state": self.state,
            "failed_products": [],
        }

        for product_failure in failed_products:
            virtualization_data["failed_products"].append(
                {
                    "product_id": product_failure["product_id"],
                    "product_name": product_failure["product"],
                    "product_code": product_failure["product_code"],
                    "shortage_qty": product_failure["shortage"],
                    "location_src_id": self.location_id.id,
                    "location_dest_id": self.location_dest_id.id,
                    "transfer_direction": self._get_transfer_direction(),
                }
            )

        return virtualization_data

    def _get_transfer_direction(self):
        """
        Détermine la direction du transfert (vers/depuis hivernage)

        Returns:
            str: 'to_winter', 'from_winter', ou 'unknown'
        """
        self.ensure_one()

        # Récupérer les entrepôts
        main_warehouse = self.env["stock.warehouse"].get_main_rental_warehouse()
        winter_warehouse = self.env["stock.warehouse"].get_winter_storage_warehouse()

        if not main_warehouse or not winter_warehouse:
            return "unknown"

        if (
            self.location_id == main_warehouse.lot_stock_id
            and self.location_dest_id == winter_warehouse.lot_stock_id
        ):
            return "to_winter"
        if (
            self.location_id == winter_warehouse.lot_stock_id
            and self.location_dest_id == main_warehouse.lot_stock_id
        ):
            return "from_winter"
        return "unknown"

    def _notify_failed_transfers(self, failed_transfer_ids):
        """
        Méthode privée pour notifier les transferts ratés

        Args:
            failed_transfer_ids (list): Liste des IDs des transferts ratés
        """
        if not failed_transfer_ids:
            return

        try:
            message_body = f"""
            <p><strong>⚠️ Transferts de stock en échec détectés</strong></p>
            <p>{len(failed_transfer_ids)}
            transferts automatiques n'ont pas pu être exécutés:</p>
            <ul>
            """

            failed_pickings = self.browse(failed_transfer_ids)
            for picking in failed_pickings:
                message_body += (
                    f"<li>{picking.name} - {picking.origin}"
                    f" (prévu le {picking.scheduled_date})</li>"
                )

            message_body += """
            </ul>
            <p>Veuillez vérifier les stocks et traiter ces transferts.</p>
            """

            # Créer une activité pour les gestionnaires de stock
            admin_users = self.env["res.users"].search(
                [("groups_id", "in", [self.env.ref("stock.group_stock_manager").id])]
            )

            for admin in admin_users:
                self.env["mail.activity"].create(
                    {
                        "summary": "🚨 Transferts de stock en échec",
                        "note": message_body,
                        "res_model": "stock.picking",
                        "res_id": (
                            failed_pickings[0].id if failed_pickings else admin.id
                        ),
                        "user_id": admin.id,
                        "activity_type_id": self.env.ref(
                            "mail.mail_activity_data_todo"
                        ).id,
                        "date_deadline": fields.Date.today(),
                    }
                )

            _logger.info(
                "📧 Notifications envoyées à %s administrateurs", len(admin_users)
            )

        except (ValidationError, AccessError, MissingError) as e:
            _logger.error("❌ Erreur lors de l'envoi des notifications: %s", e)
        except Exception:
            _logger.error("❌ Erreur inattendue lors de l'envoi des notifications")
            raise  # Re-raise pour ne pas masquer les erreurs critiques

    @api.model
    def attempt_retry_failed_transfers(self, failed_transfer_ids=None):
        """
        Tente de relancer automatiquement les transferts ratés

        Args:
            failed_transfer_ids (list, optional): Liste spécifique d'IDs à traiter.

        Returns:
            dict: Résumé des actions effectuées
        """
        if failed_transfer_ids is None:
            failed_transfer_ids = self.detect_failed_transfers()

        if not failed_transfer_ids:
            return {
                "success": 0,
                "failed": 0,
                "message": "Aucun transfert raté à traiter",
            }

        _logger.info(
            "💡 Tentative de relance de %s transferts", len(failed_transfer_ids)
        )

        success_count = 0
        still_failed_count = 0
        results = []

        failed_pickings = self.browse(failed_transfer_ids)

        for picking in failed_pickings:
            try:
                # Tenter de vérifier la disponibilité
                picking.action_assign()

                # Si maintenant disponible, noter le succès
                if picking.state == "assigned":
                    success_count += 1
                    results.append(f"✅ {picking.name}: réassigné avec succès")
                    _logger.info("✅ Transfert %s réparé automatiquement", picking.name)
                else:
                    still_failed_count += 1
                    results.append(
                        f"❌ {picking.name}: toujours bloqué ({picking.state})"
                    )
                    _logger.warning("❌ Transfert %s toujours en échec", picking.name)

            except Exception as e:
                still_failed_count += 1
                results.append(f"💥 {picking.name}: erreur lors de la relance - {e}")
                _logger.error(
                    "💥 Erreur lors de la relance de %s : %s", picking.name, e
                )

        summary = {
            "success": success_count,
            "failed": still_failed_count,
            "details": results,
            "message": f"{success_count} transferts relancés,"
            f" {still_failed_count} toujours en échec",
        }

        _logger.info("💡 Relance terminée: %s", {summary["message"]})
        return summary

    # === Protection avec clause d'urgence ===

    def _check_period_transfer_immutability(self):
        """
        Verrouillage avec possibilité de déverrouillage temporaire
        """
        period_transfers = self.filtered("is_period_transfer")
        if period_transfers:
            transfer_names = period_transfers.mapped("name")
            raise UserError(
                "🚫 TRANSFERTS DE PÉRIODE VERROUILLÉS 🚫\n\n"
                f"Transferts protégés :\n• {chr(10).join(transfer_names)}\n\n"
                "❌ Ces transferts ne peuvent pas être modifiés\n"
                "✅ Ils sont gérés automatiquement par le système saisonnier\n\n"
                "⚠️  Contactez le développeur pour une intervention d'urgence"
            )

    def write(self, vals):
        """
        Protection avec clause de déverrouillage temporaire
        """
        # Clause d'urgence : déverrouillage temporaire
        if self.env.context.get("admin_override"):
            return super().write(vals)

        # Protection normale
        self._check_period_transfer_immutability()

        return super().write(vals)

    def unlink(self):
        """
        Protection contre la suppression avec clause d'urgence
        """
        # Clause d'urgence
        if self.env.context.get("admin_override"):
            return super().unlink()

        # Protection normale
        self._check_period_transfer_immutability()

        return super().unlink()

    # === Contrainte de cohérence ===

    @api.constrains("is_period_transfer", "period_config_id")
    def _check_period_config_consistency(self):
        """
        Vérification de cohérence
        """
        for picking in self:
            if picking.is_period_transfer and not picking.period_config_id:
                raise UserError(
                    f"Le transfert de période {picking.name} doit avoir "
                    "une configuration de période associée."
                )

    def action_emergency_unlock_wizard(self):
        """Ouvrir le wizard de déverrouillage avec mot de passe"""

        if not self.is_period_transfer:
            raise UserError("❌ Ce transfert n'est pas verrouillé")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Déverrouiller Transfert de Période',
            'res_model': 'stock.picking.unlock.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
            }
        }
    def action_emergency_relock(self):
        """Bouton pour re-verrouiller un transfert de période après test"""
        if not self.env.user.has_group('base.group_system'):
            raise UserError("Seuls les administrateurs peuvent verrouiller les transferts")

        if not self.period_config_id:
            raise UserError("Ce transfert n'est pas associé à une configuration de période")

        self.with_context(admin_override=True).write({
            'is_period_transfer': True,
            'note': f"🔒 Re-verrouillé manuellement le {fields.Datetime.now()} par {self.env.user.name}"
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',  # Refresh complet de la page
            'params': {
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': '🔒 Transfert re-verrouillé',
                        'message': f'Le transfert {self.name} est maintenant protégé',
                        'type': 'success',
                    }
                }
            }
        }
