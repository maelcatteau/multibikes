# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class MultibikesBaseTestCommon(TransactionCase):
    """Classe commune pour les tests du module multibikes_base"""

    @classmethod
    def setUpClass(cls):
        """Configuration initiale des tests"""
        super(MultibikesBaseTestCommon, cls).setUpClass()

        # Création d'un partenaire de test
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Client Test",
                "email": "client.test@example.com",
            }
        )

        # Création d'une catégorie de produit
        cls.product_category = cls.env["product.category"].create(
            {
                "name": "Vélos",
            }
        )

        # Création d'un produit (vélo) de test
        cls.product = cls.env["product.template"].create(
            {
                "name": "Vélo de Test",
                "type": "consu",
                "categ_id": cls.product_category.id,
                "list_price": 50.0,
                "rent_ok": True,
                "mb_caution": 200.0,
                "mb_value_in_case_of_theft": 500.0,
                "mb_size_min": 160.0,
                "mb_size_max": 185.0,
            }
        )

        # Création d'une commande de test
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "mb_type_de_caution": "carte_bancaire",
                "mb_numero_de_caution": 12345,
            }
        )
