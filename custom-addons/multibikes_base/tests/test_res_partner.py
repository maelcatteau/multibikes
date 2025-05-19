# -*- coding: utf-8 -*-

from odoo.tests import tagged
from .common import MultibikesBaseTestCommon

@tagged('post_install', '-at_install')
class TestResPartner(MultibikesBaseTestCommon):
    """Tests pour le modèle ResPartner"""
    
    def test_partner_nationalite(self):
        """Test du champ nationalité sur le partenaire"""
        # Vérification de la valeur initiale
        self.assertEqual(self.partner.mb_nationalite, 'Française')
        
        # Modification de la nationalité et vérification
        self.partner.mb_nationalite = 'Belge'
        self.assertEqual(self.partner.mb_nationalite, 'Belge')
    
    def test_create_partner_with_nationalite(self):
        """Test de création d'un partenaire avec nationalité"""
        new_partner = self.env['res.partner'].create({
            'name': 'Nouveau Client',
            'email': 'nouveau.client@example.com',
            'mb_nationalite': 'Italienne',
        })
        
        self.assertEqual(new_partner.mb_nationalite, 'Italienne')
