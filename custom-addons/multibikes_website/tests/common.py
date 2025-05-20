# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from odoo.tests.common import TransactionCase
import logging
import time
import uuid

_logger = logging.getLogger(__name__)

class MultibikesWebsiteTestCommon(TransactionCase):
    """Classe commune pour les tests du module multibikes_website"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration initiale des tests"""
        super(MultibikesWebsiteTestCommon, cls).setUpClass()
         
        # Création d'un identifiant de test unique
        # Utilisation de uuid pour générer un identifiant unique
        cls.test_id = uuid.uuid4().hex[:6]


        # Dates de test (uniformisation en utilisant date.today())
        cls.today = date.today()
        cls.yesterday = cls.today - timedelta(days=1)
        cls.tomorrow = cls.today + timedelta(days=1)
        cls.next_week = cls.today + timedelta(days=7)
        cls.last_week = cls.today - timedelta(days=7)
        cls.next_month = cls.today + timedelta(days=30)
        cls.last_month = cls.today - timedelta(days=30)
        
        # Création des sociétés pour les tests
        cls.main_company = cls.env['res.company'].create({
            'name': 'Main Test Company',
        })
        
        # Définir la société comme société courante pour les tests
        cls.env.user.company_id = cls.main_company.id
        cls.env.user.company_ids = [(4, cls.main_company.id)]
        
        cls.second_company = cls.env['res.company'].create({
            'name': 'Second Test Company',
        })
        
        # Créer un site web pour les tests
        cls.website = cls.env['website'].create({
            'name': 'Test Website',
            'company_id': cls.main_company.id,
        })
        
        # Créer une liste de prix et l'associer au site web
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Test Pricelist',
            'currency_id': cls.env.ref('base.EUR').id,
        })
        cls.website.pricelist_id = cls.pricelist.id
        cls.website.currency_id = cls.env.ref('base.EUR').id
        
        # ----- PÉRIODES DE LOCATION -----
        
        # Création de périodes de location pour la société principale
        cls.current_period = cls.env['mb.renting.period'].create({
            'name': 'Période Actuelle',
            'company_id': cls.main_company.id,
            'start_date': cls.last_week,
            'end_date': cls.next_week,
            'minimal_time_duration': 2,
            'minimal_time_unit': 'day',
            'is_closed': False,
        })
        
        cls.future_period = cls.env['mb.renting.period'].create({
            'name': 'Période Future',
            'company_id': cls.main_company.id,
            'start_date': cls.tomorrow,
            'end_date': cls.next_month,
            'minimal_time_duration': 3,
            'minimal_time_unit': 'day',
            'is_closed': False,
        })
        
        cls.past_period = cls.env['mb.renting.period'].create({
            'name': 'Période Passée',
            'company_id': cls.main_company.id,
            'start_date': cls.last_month,
            'end_date': cls.yesterday,
            'minimal_time_duration': 1,
            'minimal_time_unit': 'day',
            'is_closed': True,
        })
        
        # Période pour la seconde société
        cls.second_company_period = cls.env['mb.renting.period'].create({
            'name': 'Période Autre Société',
            'company_id': cls.second_company.id,
            'start_date': cls.last_week,
            'end_date': cls.next_week,
            'minimal_time_duration': 4,
            'minimal_time_unit': 'hour',
            'is_closed': False,
        })
        
        # ----- CONFIGURATION DES JOURS -----
        
        # Création de configurations de jour pour la période actuelle
        # Lundi (0)
        cls.monday_config = cls.env['mb.renting.day.config'].create({
            'period_id': cls.current_period.id,
            'company_id': cls.main_company.id,
            'day_of_week': '0',
            'is_open': True,
            'allow_pickup': True,
            'pickup_hour_from': 9.0,
            'pickup_hour_to': 12.0,
            'allow_return': True,
            'return_hour_from': 14.0,
            'return_hour_to': 18.0,
        })
        
        # Dimanche (6) - fermé
        cls.sunday_config = cls.env['mb.renting.day.config'].create({
            'period_id': cls.current_period.id,
            'company_id': cls.main_company.id,
            'day_of_week': '6',
            'is_open': False,
        })
        
        # ----- CATÉGORIES DE PRODUITS -----
        
        cls.product_category = cls.env['product.category'].create({
            'name': 'Vélos Test',
        })
        
        # ----- RÉCURRENCES TEMPORELLES -----
        
        cls.recurrence_hour = cls.env['sale.temporal.recurrence'].create({
            'name': 'Heure',
            'unit': 'hour',
            'duration': 1,
        })
        
        cls.recurrence_day = cls.env['sale.temporal.recurrence'].create({
            'name': 'Jour',
            'unit': 'day',
            'duration': 1,
        })
        
        cls.recurrence_week = cls.env['sale.temporal.recurrence'].create({
            'name': 'Semaine',
            'unit': 'week',
            'duration': 1,
        })
        
        # ----- ENTREPÔTS -----
        
        cls.main_warehouse = cls.env['stock.warehouse'].create({
            'name': 'Entrepôt Principal',
            'code': 'MAIN',
            'company_id': cls.main_company.id,
            'is_excluded_from_availability': False,
        })
        
        cls.secondary_warehouse = cls.env['stock.warehouse'].create({
            'name': 'Entrepôt Secondaire',
            'code': 'SEC',
            'company_id': cls.main_company.id,
            'is_excluded_from_availability': False,
        })
        
        cls.excluded_warehouse = cls.env['stock.warehouse'].create({
            'name': 'Entrepôt Exclu',
            'code': 'EXCL',
            'company_id': cls.main_company.id,
            'is_excluded_from_availability': True,
        })
        
        cls.other_company_warehouse = cls.env['stock.warehouse'].create({
            'name': 'Entrepôt Autre Société',
            'code': 'OTHER',
            'company_id': cls.second_company.id,
            'is_excluded_from_availability': False,
        })
        
        # ----- PRODUITS -----
        
        # Produit stockable simple
        cls.storable_product = cls.env['product.product'].create({
            'name': 'Vélo Stockable Test',
            'type': 'consu',
            'categ_id': cls.product_category.id,
            'default_code': 'VST001',
            'is_storable': True,
            'is_published': True,
        })
        
        # Second produit stockable
        cls.storable_product2 = cls.env['product.product'].create({
            'name': 'Vélo Stockable Test 2',
            'type': 'consu',
            'categ_id': cls.product_category.id,
            'default_code': 'VST002',
            'is_storable': True,
            'is_published': True,
        })
        
        # Produit de location
        cls.rental_product_template = cls.env['product.template'].create({
            'name': f'Vélo de Location Test {cls.test_id}_S1',
            'categ_id': cls.product_category.id,
            'type': 'consu',
            'rent_ok': True,
            'tracking': 'none',
            'is_storable': True,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
            'default_code': 'VLT001',
            'list_price': 100.00,
        })
        
        cls.rental_product = cls.rental_product_template.product_variant_id 
        
        # Produit non louable
        cls.non_rental_product_template = cls.env['product.template'].create({
            'name': f'Accessoire Vélo Test {cls.test_id}_S2',
            'categ_id': cls.product_category.id,
            'type': 'consu',
            'rent_ok': False,
            'tracking': 'none',
            'is_storable': True,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
            'default_code': 'AVT001',
            'list_price': 50.00,
        })
        
        cls.non_rental_product = cls.non_rental_product_template.product_variant_id
        
        # ----- TARIFS DE LOCATION -----
        
        cls.pricing_hour = cls.env['product.pricing'].create({
            'product_template_id': cls.rental_product_template.id,
            'recurrence_id': cls.recurrence_hour.id,
            'price': 5.0,
            'currency_id': cls.env.ref('base.EUR').id,
            'pricelist_id': cls.pricelist.id,
            'mb_website_published': True,
            'name': 'Tarif horaire',
        })
        
        cls.pricing_day = cls.env['product.pricing'].create({
            'product_template_id': cls.rental_product_template.id,
            'recurrence_id': cls.recurrence_day.id,
            'price': 25.0,
            'currency_id': cls.env.ref('base.EUR').id,
            'pricelist_id': cls.pricelist.id,
            'mb_website_published': True,
            'name': 'Tarif journalier',
        })
        
        cls.pricing_week = cls.env['product.pricing'].create({
            'product_template_id': cls.rental_product_template.id,
            'recurrence_id': cls.recurrence_week.id,
            'price': 150.0,
            'currency_id': cls.env.ref('base.EUR').id,
            'pricelist_id': cls.pricelist.id,
            'mb_website_published': False,  # Non publié sur le site web
            'name': 'Tarif hebdomadaire',
        })
        
        # ----- STOCK -----
        
        # Configuration du stock pour les périodes
        cls.stock_period_config = cls.env['mb.renting.stock.period.config'].create({
            'period_id': cls.current_period.id,
            'storable_product_ids': [(6, 0, [cls.storable_product.id])],
            'stock_available_for_period': 10,
        })
        
        # Ajout de stock pour les produits
        # Stock pour le produit principal de location dans tous les entrepôts
        cls.env['stock.quant'].create({
            'product_id': cls.rental_product.id,
            'location_id': cls.main_warehouse.lot_stock_id.id,
            'quantity': 5.0,
        })
        
        cls.env['stock.quant'].create({
            'product_id': cls.rental_product.id,
            'location_id': cls.secondary_warehouse.lot_stock_id.id,
            'quantity': 3.0,
        })
        
        cls.env['stock.quant'].create({
            'product_id': cls.rental_product.id,
            'location_id': cls.excluded_warehouse.lot_stock_id.id,
            'quantity': 3.0,
        })
        
        # Stock pour le produit stockable (non de location)
        cls.env['stock.quant'].create({
            'product_id': cls.storable_product.id,
            'location_id': cls.main_warehouse.lot_stock_id.id,
            'quantity': 5.0,
        })
        
        # ----- MOUVEMENTS DE STOCK -----
        
        # Définir des dates de location pour les tests
        cls.start_date_dt = datetime.now()
        cls.end_date_dt = cls.start_date_dt + timedelta(days=2)
        
        # Mouvement sortant de l'entrepôt exclu vers l'entrepôt principal
        cls.outgoing_move = cls.env['stock.move'].create({
            'name': 'Test outgoing move',
            'product_id': cls.rental_product.id,
            'product_uom': cls.env.ref('uom.product_uom_unit').id,
            'product_uom_qty': 1.0,
            'location_id': cls.excluded_warehouse.lot_stock_id.id,
            'location_dest_id': cls.main_warehouse.lot_stock_id.id,
            'date': (cls.start_date_dt + timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S'),
        })
        
        # Mouvement entrant de l'entrepôt principal vers l'entrepôt exclu
        cls.incoming_move = cls.env['stock.move'].create({
            'name': 'Test incoming move',
            'product_id': cls.rental_product.id,
            'product_uom': cls.env.ref('uom.product_uom_unit').id,
            'product_uom_qty': 2.0,
            'location_id': cls.main_warehouse.lot_stock_id.id,
            'location_dest_id': cls.excluded_warehouse.lot_stock_id.id,
            'date': (cls.start_date_dt + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
        })
