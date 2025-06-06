# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import MultibikesWebsiteTestCommon as MultibikesWebsiteProductTestCommon


@tagged("post_install", "-at_install")
class TestProductPricing(MultibikesWebsiteProductTestCommon):
    """Tests pour le modèle product.pricing avec les extensions multibikes_website"""

    def test_mb_website_published(self):
        """Test de la visibilité des tarifs sur le site web"""
        # Vérifier les valeurs initiales
        self.assertTrue(self.pricing_hour.mb_website_published)
        self.assertTrue(self.pricing_day.mb_website_published)
        self.assertFalse(self.pricing_week.mb_website_published)

        # Changer la visibilité d'un tarif
        self.pricing_hour.mb_website_published = False
        self.assertFalse(self.pricing_hour.mb_website_published)

        # Vérifier que les autres tarifs ne sont pas affectés
        self.assertTrue(self.pricing_day.mb_website_published)
        self.assertFalse(self.pricing_week.mb_website_published)

        # Publier tous les tarifs
        self.pricing_hour.mb_website_published = True
        self.pricing_week.mb_website_published = True

        # Vérifier que tous les tarifs sont maintenant publiés
        self.assertTrue(self.pricing_hour.mb_website_published)
        self.assertTrue(self.pricing_day.mb_website_published)
        self.assertTrue(self.pricing_week.mb_website_published)
