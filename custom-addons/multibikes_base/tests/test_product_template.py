# -*- coding: utf-8 -*-

from odoo.tests import tagged
from .common import MultibikesBaseTestCommon


@tagged("post_install", "-at_install")
class TestProductTemplate(MultibikesBaseTestCommon):
    """Tests pour le modèle ProductTemplate"""

    def test_product_caution_fields(self):
        """Test des champs de caution sur le produit"""
        # Vérification des valeurs initiales
        self.assertEqual(self.product.mb_caution, 200.0)
        self.assertEqual(self.product.mb_value_in_case_of_theft, 500.0)
        self.assertEqual(self.product.mb_currency_id, self.env.company.currency_id)

        # Modification de la caution et vérification
        self.product.mb_caution = 300.0
        self.assertEqual(self.product.mb_caution, 300.0)

    def test_product_size_fields(self):
        """Test des champs de taille sur le produit"""
        # Vérification des valeurs initiales
        self.assertEqual(self.product.mb_size_min, 160.0)
        self.assertEqual(self.product.mb_size_max, 185.0)

        # Modification des tailles et vérification
        self.product.mb_size_min = 150.0
        self.product.mb_size_max = 190.0
        self.assertEqual(self.product.mb_size_min, 150.0)
        self.assertEqual(self.product.mb_size_max, 190.0)
