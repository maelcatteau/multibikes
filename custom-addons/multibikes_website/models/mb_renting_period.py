# -*- coding: utf-8 -*-
"""Model MBRentingDayConfig for multibikes_base module."""
import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class MBRentingPeriod(models.Model):
    _name = "mb.renting.period"
    _description = "Renting Period"
    _order = "start_date"

    name = fields.Char("Nom", required=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.company
    )

    start_date = fields.Datetime(required=True)
    end_date = fields.Datetime(required=True)

    is_closed = fields.Boolean("Closed", default=False)

    recurrence_id = fields.Many2one(
        "sale.temporal.recurrence",
        string="Récurrence de location",
        required=True,
        help="Règle de récurrence utilisée pour définir la durée minimale de location.",
    )
    recurrence_name = fields.Char(
        related="recurrence_id.name",
        string="Nom de la récurrence",
        store=False,
        readonly=True,
    )
    recurrence_duration = fields.Integer(
        related="recurrence_id.duration",
        string="Durée minimale",
        store=False,
        readonly=True,
    )
    recurrence_unit = fields.Selection(
        related="recurrence_id.unit",
        string="Unité de durée",
        store=False,
        readonly=True,
    )

    day_configs_ids = fields.One2many(
        "mb.renting.day.config",
        "period_id",
        string="Day Configurations",
        domain="[('company_id', '=', company_id)]",
    )

    # Relation inverse vers les configurations de stock
    stock_period_config_ids = fields.One2many(
        "mb.renting.stock.period.config", "period_id", string="Configurations de stock"
    )

    total_storable_products = fields.Integer(
        string="Produits stockables disponibles",
        compute="_compute_total_storable_products",
        help="Nombre total de produits stockables à configurer",
    )

    # Champ pour indiquer combien de produits restent à configurer
    remaining_products_to_configure = fields.Integer(
        string="Produits restants à configurer",
        compute="_compute_products_to_configure",
        store=False,
        help="Nombre de produits stockables qui n'ont pas encore été configurés",
    )

    # Champ pour indiquer combien de jours restent à configurer
    remaining_days_to_configure = fields.Integer(
        string="Jours restants à configurer",
        compute="_compute_days_to_configure",
        store=False,
        help="Nombre de jours de la semaine qui n'ont pas encore été configurés",
    )

    state = fields.Selection(
        [
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
    ],
    string='État',
    default='draft',
    tracking=True)

    status = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("confirmed", "Confirmée"),
            ("active", "Active"),
            ("past", "Passée"),
            ("closed", "Fermée"),
        ],
        string="Statut",
        compute="_compute_status",
        store=False,
    )

    _sql_constraints = [
        (
            "date_check",
            "CHECK(start_date <= end_date)",
            "The start date must be before the end date.",
        ),
        (
            "company_dates_unique",
            "UNIQUE(company_id, start_date, end_date)",
            "A period with these dates already exists.",
        ),
    ]

    @api.depends("company_id")
    def _compute_total_storable_products(self):
        """Calcule le nombre total de produits stockables dans le système."""
        for period in self:
            domain = [("is_storable", "=", True)]
            if period.company_id:
                domain.extend(
                    [
                        "|",
                        ("company_id", "=", period.company_id.id),
                        ("company_id", "=", False),
                    ]
                )

            # Recherche tous les produits stockables selon le domaine
            product_count = self.env["product.product"].search_count(domain)
            period.total_storable_products = product_count

    @api.depends("stock_period_config_ids.storable_product_ids")
    def _compute_products_to_configure(self):
        """
        Calcule le nombre de produits stockables qui n'ont PAS encore été configurés.
        Ce sont les produits qui sont stockables mais qui ne figurent pas
        dans stock_period_config_ids.storable_product_ids.
        """
        for period in self:
            # Récupérer tous les produits stockables
            domain = [("is_storable", "=", True)]
            if period.company_id:
                domain.extend(
                    [
                        "|",
                        ("company_id", "=", period.company_id.id),
                        ("company_id", "=", False),
                    ]
                )
            all_storable_products = self.env["product.product"].search(domain)

            # Récupérer les IDs des produits déjà configurés pour cette période
            configured_product_ids = period.stock_period_config_ids.mapped(
                "storable_product_ids"
            ).ids

            # Compter les produits non configurés
            unconfigured_count = 0
            for product in all_storable_products:
                if product.id not in configured_product_ids:
                    unconfigured_count += 1

            period.remaining_products_to_configure = unconfigured_count

    @api.depends("day_configs_ids")
    def _compute_days_to_configure(self):
        """
        Calcule le nombre de jours restants à configurer.
        """
        for period in self:
            domain = [('period_id', '=', period.id)]
            if period.company_id:
                domain.append(('company_id', '=', period.company_id.id))

            configured_count = self.env['mb.renting.day.config'].search_count(domain)
            period.remaining_days_to_configure = 7 - configured_count




    @api.depends('state', 'is_closed', 'start_date', 'end_date')
    def _compute_status(self):
        """Calcule le statut en fonction de l'état et des dates."""
        now = fields.Datetime.now()

        for record in self:
            if record.state == 'draft':
                record.status = 'draft'
            elif record.is_closed:
                record.status = 'closed'
            elif record.end_date and now > record.end_date:
                record.status = 'past'
            elif record.start_date and now >= record.start_date and record.end_date and now <= record.end_date:
                record.status = 'active'
            elif record.state == 'confirmed':
                record.status = 'confirmed'  # Période confirmée mais pas encore active
            else:
                record.status = 'confirmed'

    @api.constrains("start_date", "end_date", "company_id")
    def _check_no_overlap(self):
        """Empêcher les chevauchements mais autoriser les contacts"""
        for record in self:
            # Périodes qui se chevauchent VRAIMENT (pas juste se touchent)
            overlapping = self.search(
                [
                    ("company_id", "=", record.company_id.id),
                    ("id", "!=", record.id),
                    ("start_date", "<", record.end_date),
                    ("end_date", ">", record.start_date),
                ]
            )
            if overlapping:
                raise ValidationError(
                    f"Cette période chevauche avec :"
                    f"{', '.join(overlapping.mapped('name'))}\n"
                    f"Les périodes peuvent se toucher mais pas se chevaucher."
                )

    def __str__(self):
        """Affichage lisible de la période"""
        start = self.start_date.strftime("%d/%m/%Y")
        end = self.end_date.strftime("%d/%m/%Y")
        return f"{self.name} ({start} - {end})"

    def action_create_default_day_configs(self):
        """Crée les configurations par défaut pour tous les jours de la semaine"""
        created_count = 0
        for day in range(1, 8):  # 1-7 pour Lundi-Dimanche
            existing = self.env["mb.renting.day.config"].search(
                [
                    ("period_id", "=", self.id),
                    ("company_id", "=", self.company_id.id),
                    ("day_of_week", "=", str(day)),
                ]
            )
            if not existing:
                self.env["mb.renting.day.config"].create(
                    {
                        "period_id": self.id,
                        "company_id": self.company_id.id,
                        "day_of_week": str(day),
                        "is_open": day <= 5,  # Ouvert en semaine par défaut
                    }
                )
                created_count += 1

        self.env.cr.flush()

        if created_count > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'message': f"✅ {created_count} configuration(s) ajoutée(s)",
                    'type': 'success'
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'message': "ℹ️ Toutes les configurations existent déjà",
                    'type': 'info'
                }
            }

    @api.model
    def find_period_for_date(self, target_date):
        """Trouve la période active pour une date donnée"""

        # Conversion en datetime si nécessaire
        if hasattr(target_date, "date"):
            target_datetime = target_date
        else:
            # Si c'est une date, convertir en datetime début de journée
            target_datetime = fields.Datetime.to_datetime(target_date)

        return self.search(
            [
                ("company_id", "=", self.env.company.id),
                ("start_date", "<=", target_datetime),
                ("end_date", ">=", target_datetime),
                ("is_closed", "=", False),
            ],
            limit=1,
        )

    @api.model_create_multi
    def create(self, vals):
        """Création avec logique de périodes consécutives"""
        if "company_id" in vals:
            company_id = vals["company_id"]

            # Chercher la dernière période de la société
            last_period = self.search(
                [("company_id", "=", company_id)], order="end_date desc", limit=1
            )

            # Si pas de start_date ET qu'il y a une période précédente
            if last_period and not vals.get("start_date"):
                vals["start_date"] = last_period.end_date

            # Auto-suggestion du nom si pas fourni
            if not vals.get("name"):
                # Plus robuste pour les créations multiples
                count = self.search_count([("company_id", "=", company_id)])
                vals["name"] = f"Période {count + 1}"

        return super().create(vals)

    @api.model
    def get_next_period_start(self, company_id=None):
        """Retourne la date de début suggérée pour la prochaine période"""
        if not company_id:
            company_id = self.env.company.id

        last_period = self.search(
            [("company_id", "=", company_id)], order="end_date desc", limit=1
        )

        if last_period:
            return last_period.end_date

        return fields.Datetime.now()

    def action_create_next_period(self):
        """Action pour créer rapidement la période suivante"""
        next_start = self.end_date

        return {
            "type": "ir.actions.act_window",
            "name": "Nouvelle période",
            "res_model": "mb.renting.period",
            "view_mode": "form",
            "view_type": "form",
            "target": "new",
            "context": {
                "default_company_id": self.company_id.id,
                "default_start_date": next_start,
                "default_name": f"Période suivant {self.name}",
            },
        }

    def action_auto_configure_all_products(self):
        """Configure automatiquement tous les produits stockables
        avec stock par défaut"""
        # Récupérer tous les produits stockables
        all_storable_products = self.env["product.product"].search(
            [
                ("is_storable", "=", True),
                ("active", "=", True),
                "|",
                ("company_id", "=", self.company_id.id),
                ("company_id", "=", False),
            ]
        )

        # Récupérer les produits déjà configurés
        already_configured = self.stock_period_config_ids.mapped("storable_product_ids")

        # Produits à configurer
        products_to_configure = all_storable_products - already_configured

        if products_to_configure:
            configs_to_create = []
            for product in products_to_configure:
                configs_to_create.append(
                    {
                        "period_id": self.id,
                        "storable_product_ids": [(6, 0, [product.id])],
                        "stock_available_for_period": 0,
                    }
                )

            # ✅ Créer toutes les configs en une fois (plus efficace)
            self.env["mb.renting.stock.period.config"].create(configs_to_create)

            message = f"{len(products_to_configure)} produit(s) ajouté(s) à configurer"
        else:
            message = "Tous les produits sont déjà configurés pour cette période."

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            "params": {
                "message": f"✅ {message}",
                "type": "success",
            },
        }

    def action_generate_all_transfers(self):
        """
        Génère tous les transferts nécessaires
        pour toutes les configurations de cette période
        """
        self.ensure_one()

        _logger.info(
            "🚀 Génération de tous les transferts pour la période %s", self.name
        )

        configs_with_products = self.stock_period_config_ids.filtered(
            "storable_product_ids"
        )

        if not configs_with_products:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Aucune configuration trouvée",
                    "message": "Aucune configuration de stock avec produits"
                    "n'a été trouvée pour cette période.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        total_transfers = 0
        total_errors = 0

        for config in configs_with_products:
            result = config.action_generate_transfers()
            if result.get("params", {}).get("type") == "success":
                total_transfers += len(config.storable_product_ids)
            else:
                total_errors += 1

        if total_errors == 0:
            message = (
                f"✅ Génération terminée avec succès !\n"
                f"{total_transfers} transfert(s) créé(s) au total."
            )
            notification_type = "success"
        else:
            message = (
                f"⚠️ Génération terminée avec {total_errors} erreur(s).\n"
                f"Consultez les logs pour plus de détails."
            )
            notification_type = "warning"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Génération des transferts terminée",
                "message": message,
                "type": notification_type,
                "sticky": True,
            },
        }
    # Actions pour la gestion des états
    def action_confirm(self):
        """Confirme la période de location."""
        for record in self:
            if record.state != 'draft':
                raise UserError("Seules les périodes en brouillon peuvent être confirmées.")

            # Validations avant confirmation
            self._validate_before_confirm()
            record.state = 'confirmed'

    def action_reset_to_draft(self):
        """Remet la période en brouillon (pour les administrateurs uniquement)."""
        if not self.env.user.has_group('base.group_system'):
            raise UserError("Seuls les administrateurs peuvent remettre en brouillon.")

        for record in self:
            record.state = 'draft'

    def _validate_before_confirm(self):
        """Validations à effectuer avant confirmation."""
        for record in self:
            if not record.start_date or not record.end_date:
                raise ValidationError("Les dates de début et fin sont obligatoires.")
            if record.start_date >= record.end_date:
                raise ValidationError("La date de fin doit être postérieure à la date de début.")
            if record.remaining_days_to_configure > 0:
                raise ValidationError(
                    f"Il reste {record.remaining_days_to_configure} jour(s) à configurer avant de confirmer."
                )
            if record.remaining_products_to_configure > 0:
                raise ValidationError(
                    f"Il reste {record.remaining_products_to_configure} produit(s) à configurer avant de confirmer."
                )
            if not record.recurrence_id:
                raise ValidationError(
                    "La durée minimale de location est obligatoire pour confirmer la période."
                )

    def write(self, vals):
        """Empêche toute modification une fois confirmé."""
        for record in self:
            if record.state == 'confirmed' and not self.env.user.has_group('base.group_system'):
                # Filtrer uniquement les champs système automatiques
                system_fields = ['__last_update', 'write_date', 'write_uid', 'display_name']

                user_modified_fields = [
                    field for field in vals.keys()
                    if field not in system_fields
                    and not field.startswith('__')
                ]

                if user_modified_fields:
                    raise UserError(
                        "Cette période est confirmée et ne peut plus être modifiée. "
                        "Contactez un administrateur pour effectuer des modifications."
                    )

        return super().write(vals)

    def unlink(self):
        """Empêche la suppression des périodes confirmées."""
        for record in self:
            if record.state == 'confirmed':
                raise UserError("Impossible de supprimer une période confirmée.")
        return super().unlink()