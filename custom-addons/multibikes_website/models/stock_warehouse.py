# -*- coding: utf-8 -*-
"""Model Stock Warehouse for multibikes_website module."""
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    is_main_rental_warehouse = fields.Boolean(
        string="Est l'entrepôt principal",
        default=False,
        help="Si coché, le matériel stocké dans cet entrepôt sera disponible",
    )

    is_winter_storage_warehouse = fields.Boolean(
        string="Est l'entrepôt d'hivernage",
        default=False,
        help="Si coché, le matériel stocké dans cet entrepôt sera indisponible",
    )

    # Contrainte SQL : Un seul entrepôt principal par compagnie
    _sql_constraints = [
        (
            "unique_main_rental_warehouse",
            "EXCLUDE (company_id WITH =) WHERE (is_main_rental_warehouse = true)",
            "Un seul entrepôt principal de location est autorisé par compagnie.",
        ),
        (
            "unique_winter_storage_warehouse",
            "EXCLUDE (company_id WITH =) WHERE (is_winter_storage_warehouse = true)",
            "Un seul entrepôt d'hivernage est autorisé par compagnie.",
        ),
    ]

    @api.constrains("is_main_rental_warehouse", "is_winter_storage_warehouse")
    def _check_warehouse_types_exclusivity(self):
        """
        Vérifie qu'un entrepôt ne peut pas être à la fois principal ET d'hivernage
        """
        for warehouse in self:
            is_both_types = (
                warehouse.is_main_rental_warehouse
                and warehouse.is_winter_storage_warehouse
            )
            if is_both_types:
                raise ValidationError(
                    self.env._(
                        "L'entrepôt '%s' ne peut pas être à la fois l'entrepôt principal "
                        "et l'entrepôt d'hivernage.",
                        warehouse.name,
                    )
                )

    @api.constrains("is_main_rental_warehouse")
    def _check_unique_main_rental_warehouse(self):
        """
        Vérifie qu'il n'y a qu'un seul entrepôt principal par compagnie
        (contrainte Python en complément de la contrainte SQL)
        """
        for warehouse in self:
            if warehouse.is_main_rental_warehouse:
                other_main = self.search(
                    [
                        ("is_main_rental_warehouse", "=", True),
                        ("company_id", "=", warehouse.company_id.id),
                        ("id", "!=", warehouse.id),
                    ]
                )
                if other_main:
                    raise ValidationError(
                        self.env._(
                            "Il ne peut y avoir qu'un seul entrepôt"
                            " principal par compagnie. "
                            "L'entrepôt '%s' est déjà configuré comme entrepôt principal.",
                            other_main[0].name,
                        )
                    )

    @api.constrains("is_winter_storage_warehouse")
    def _check_unique_winter_storage_warehouse(self):
        """
        Vérifie qu'il n'y a qu'un seul entrepôt d'hivernage par compagnie
        """
        for warehouse in self:
            if warehouse.is_winter_storage_warehouse:
                other_winter = self.search(
                    [
                        ("is_winter_storage_warehouse", "=", True),
                        ("company_id", "=", warehouse.company_id.id),
                        ("id", "!=", warehouse.id),
                    ]
                )
                if other_winter:
                    raise ValidationError(
                        self.env._(
                            "Il ne peut y avoir qu'un seul entrepôt"
                            " d'hivernage par compagnie."
                            "L'entrepôt %s est déjà configuré comme entrepôt d'hivernage.",
                            other_winter[0].name,
                        )
                    )

    # Méthodes utilitaires
    @api.model
    def get_main_rental_warehouse(self, company_id=None):
        """
        Retourne l'entrepôt principal de location pour la compagnie donnée
        """
        if not company_id:
            company_id = self.env.company.id

        return self.search(
            [("is_main_rental_warehouse", "=", True), ("company_id", "=", company_id)],
            limit=1,
        )

    @api.model
    def get_winter_storage_warehouse(self, company_id=None):
        """
        Retourne l'entrepôt d'hivernage pour la compagnie donnée
        """
        if not company_id:
            company_id = self.env.company.id

        return self.search(
            [
                ("is_winter_storage_warehouse", "=", True),
                ("company_id", "=", company_id),
            ],
            limit=1,
        )
