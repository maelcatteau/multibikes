# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import HttpCase
from odoo.addons.website.tools import MockRequest
from datetime import date, timedelta, datetime
import json
import logging
from .common import MultibikesWebsiteTestCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'multibikes_js')
class TestMultibikesWebsiteJS(HttpCase, MultibikesWebsiteTestCommon):
    """Tests pour le JavaScript du module MultiBikes Website"""

    def setUp(self):
        super(TestMultibikesWebsiteJS, self).setUp()
        
        # Créer un utilisateur de test pour la simulation de session
        self.website_user = self.env['res.users'].create({
            'name': 'Website Test User',
            'login': 'website_test_user',
            'password': 'website_test_user',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })
        
        # Créer un produit de test spécifique pour ces tests
        self.js_test_product = self._create_product_with_rental_pricing("Test JS Rental Product")
        
        # Enregistrer le tour pour les tests
        self._create_daterangepicker_tour()
        self._create_rental_constraints_tour()
        self._create_color_codes_legend_tour()

    def _create_product_with_rental_pricing(self, name):
        """Crée un produit avec des tarifs de location pour les tests JS"""
        product = self.env['product.product'].create({
            'name': name,
            'type': 'product',
            'categ_id': self.product_category.id,
            'rent_ok': True,
            'allow_out_of_stock_order': False,
            'show_availability': True,
            'website_published': True,
            'detailed_type': 'product',
        })
        
        # Tarif journalier
        self.env['product.pricing'].create({
            'product_template_id': product.product_tmpl_id.id,
            'duration': 1,
            'unit': 'day',
            'price': 100.0,
            'pricelist_id': self.pricelist.id,
            'currency_id': self.env.company.currency_id.id,
            'mb_website_published': True,
        })
        
        # Tarif horaire
        self.env['product.pricing'].create({
            'product_template_id': product.product_tmpl_id.id,
            'duration': 1,
            'unit': 'hour',
            'price': 15.0,
            'pricelist_id': self.pricelist.id,
            'currency_id': self.env.company.currency_id.id,
            'mb_website_published': True,
        })
        
        # Ajouter du stock
        self.env['stock.quant'].create({
            'product_id': product.id,
            'location_id': self.main_warehouse.lot_stock_id.id,
            'quantity': 10.0,
        })
        
        return product

    def _create_daterangepicker_tour(self):
        """Crée un tour pour tester le daterangepicker personnalisé"""
        self.env['ir.attachment'].create({
            'name': 'multibikes_daterangepicker_tour.js',
            'type': 'binary',
            'datas': f'''
                odoo.define('multibikes_website.daterangepicker_tour', function (require) {
                'use strict';

                const tour = require('web_tour.tour');
                const productId = {self.js_test_product.id};

                tour.register('multibikes_daterangepicker_tour', {{
                    test: true,
                    url: '/shop/product/' + productId,
                }}, [
                    // Vérifier que la page se charge avec le widget daterangepicker
                    {{
                        content: "Attendre que la page se charge",
                        trigger: '.o_website_sale',
                        run: function () {{
                            // Vérification explicite du chargement des composants
                            if (!$('.daterangepicker').length) {{
                                console.error("Le daterangepicker n'est pas chargé");
                            }}
                        }},
                    }},
                    // Vérifier la présence de la légende personnalisée
                    {{
                        content: "Vérifier la présence de la légende",
                        trigger: '.o_daterangepicker_legend',
                        run: function () {{
                            // Vérifier que tous les éléments de légende sont présents
                            if (!$('.o_daterangepicker_legend .o_daterangepicker_both').length) {{
                                console.error("Légende pour Départ et Retour manquante");
                            }}
                            if (!$('.o_daterangepicker_legend .o_daterangepicker_pickup').length) {{
                                console.error("Légende pour Départ uniquement manquante");
                            }}
                            if (!$('.o_daterangepicker_legend .o_daterangepicker_return').length) {{
                                console.error("Légende pour Retour uniquement manquante");
                            }}
                            if (!$('.o_daterangepicker_legend .o_daterangepicker_closed').length) {{
                                console.error("Légende pour Fermé manquante");
                            }}
                        }},
                    }},
                    // Vérifier que les styles personnalisés sont chargés
                    {{
                        content: "Vérifier les styles personnalisés",
                        trigger: 'head',
                        run: function () {{
                            if (!$('#daterangepicker-custom-styles').length) {{
                                console.error("Les styles personnalisés ne sont pas chargés");
                            }}
                        }},
                    }},
                    // Interagir avec le daterangepicker
                    {{
                        content: "Cliquer sur le champ date de début",
                        trigger: 'input[name="start_date"]',
                        run: 'click',
                    }},
                    {{
                        content: "Vérifier que le daterangepicker s'ouvre",
                        trigger: '.daterangepicker:visible',
                        run: function () {{
                            // Vérifier que des dates sont appliquées avec les classes personnalisées
                            const hasCustomClasses = $('.daterangepicker td.o_daterangepicker_both, ' +
                                                     '.daterangepicker td.o_daterangepicker_pickup, ' +
                                                     '.daterangepicker td.o_daterangepicker_return, ' +
                                                     '.daterangepicker td.o_daterangepicker_closed').length > 0;
                            if (!hasCustomClasses) {{
                                console.warn("Aucune date n'a de classe personnalisée appliquée");
                            }}
                        }},
                    }},
                    {{
                        content: "Sélectionner une date valide",
                        trigger: '.daterangepicker td:not(.disabled):not(.off):first',
                        run: 'click',
                    }},
                    {{
                        content: "Cliquer sur le champ date de fin",
                        trigger: 'input[name="end_date"]',
                        run: 'click',
                    }},
                    {{
                        content: "Vérifier que le daterangepicker s'ouvre à nouveau",
                        trigger: '.daterangepicker:visible',
                    }},
                    {{
                        content: "Sélectionner une date de fin valide (quelques jours plus tard)",
                        trigger: '.daterangepicker td:not(.disabled):not(.off):nth(5)',
                        run: 'click',
                    }},
                    {{
                        content: "Vérifier que les dates sont définies",
                        trigger: 'input[name="end_date"][value!=""]',
                    }},
                ]);
                }});
            '''.encode('utf-8'),
            'mimetype': 'application/javascript',
            'public': True,
        })

    def _create_rental_constraints_tour(self):
        """Crée un tour pour tester les contraintes de location"""
        self.env['ir.attachment'].create({
            'name': 'multibikes_rental_constraints_tour.js',
            'type': 'binary',
            'datas': f'''
                odoo.define('multibikes_website.rental_constraints_tour', function (require) {
                'use strict';

                const tour = require('web_tour.tour');
                const productId = {self.js_test_product.id};

                tour.register('multibikes_rental_constraints_tour', {{
                    test: true,
                    url: '/shop/product/' + productId,
                }}, [
                    // Attendre que la page se charge
                    {{
                        content: "Attendre que la page se charge",
                        trigger: '.o_website_sale',
                    }},
                    // Test de l'événement renting_constraints_changed
                    {{
                        content: "Vérifier que les contraintes sont chargées",
                        trigger: '.js_product',
                        run: function () {{
                            // Ajouter un écouteur pour vérifier si l'événement est déclenché
                            let constraintsReceived = false;
                            $('.oe_website_sale').on('renting_constraints_changed', function() {{
                                constraintsReceived = true;
                            }});
                            
                            // Modifier la date pour déclencher l'événement
                            const today = new Date();
                            const nextWeek = new Date(today);
                            nextWeek.setDate(today.getDate() + 7);
                            
                            // Format YYYY-MM-DD
                            const formattedDate = nextWeek.toISOString().split('T')[0];
                            
                            $('input[name="start_date"]').val(formattedDate).trigger('change');
                            
                            // Vérification
                            setTimeout(function() {{
                                if (!constraintsReceived) {{
                                    console.error("L'événement renting_constraints_changed n'a pas été déclenché");
                                }}
                            }}, 1000);
                        }},
                    }},
                    // Essayer une période trop courte pour tester la validation des durées minimales
                    {{
                        content: "Définir une date de début",
                        trigger: 'input[name="start_date"]',
                        run: function() {{
                            const today = new Date();
                            const formattedToday = today.toISOString().split('T')[0];
                            $(this).val(formattedToday).trigger('change');
                        }},
                    }},
                    {{
                        content: "Définir une date de fin trop proche (même jour)",
                        trigger: 'input[name="end_date"]',
                        run: function() {{
                            const today = new Date();
                            const formattedToday = today.toISOString().split('T')[0];
                            $(this).val(formattedToday).trigger('change');
                        }},
                    }},
                    {{
                        content: "Vérifier le message d'erreur de durée minimale",
                        trigger: '.o_website_sale',
                        run: function() {{
                            // Cliquer sur le bouton d'ajout au panier pour déclencher la validation
                            $('#add_to_cart').click();
                            
                            // Vérifier qu'un message d'erreur s'affiche
                            setTimeout(function() {{
                                if (!$('.alert-danger:contains("rental duration is too short")').length) {{
                                    // Si le message n'est pas exactement celui attendu, vérifier s'il y a une alerte générale
                                    if (!$('.alert-danger').length) {{
                                        console.error("Aucun message d'erreur de durée minimale n'est affiché");
                                    }}
                                }}
                            }}, 500);
                        }},
                    }},
                    // Essayer maintenant une période valide
                    {{
                        content: "Définir une nouvelle date de fin valide",
                        trigger: 'input[name="end_date"]',
                        run: function() {{
                            const today = new Date();
                            const validEndDate = new Date(today);
                            validEndDate.setDate(today.getDate() + 5); // Période de 5 jours
                            const formattedEndDate = validEndDate.toISOString().split('T')[0];
                            $(this).val(formattedEndDate).trigger('change');
                        }},
                    }},
                ]);
                }});
            '''.encode('utf-8'),
            'mimetype': 'application/javascript',
            'public': True,
        })

    def _create_color_codes_legend_tour(self):
        """Crée un tour pour tester l'affichage des codes couleur et la légende"""
        self.env['ir.attachment'].create({
            'name': 'multibikes_color_codes_tour.js',
            'type': 'binary',
            'datas': f'''
                odoo.define('multibikes_website.color_codes_tour', function (require) {
                'use strict';

                const tour = require('web_tour.tour');
                const productId = {self.js_test_product.id};

                tour.register('multibikes_color_codes_tour', {{
                    test: true,
                    url: '/shop/product/' + productId,
                }}, [
                    // Vérifier que la légende est affichée
                    {{
                        content: "Vérifier la présence de la légende des codes couleur",
                        trigger: '.o_daterangepicker_legend',
                    }},
                    // Vérifier la présence de tous les types d'entrées de légende
                    {{
                        content: "Vérifier la légende départ et retour",
                        trigger: '.o_daterangepicker_legend .o_daterangepicker_both',
                    }},
                    {{
                        content: "Vérifier la légende départ uniquement",
                        trigger: '.o_daterangepicker_legend .o_daterangepicker_pickup',
                    }},
                    {{
                        content: "Vérifier la légende retour uniquement",
                        trigger: '.o_daterangepicker_legend .o_daterangepicker_return',
                    }},
                    {{
                        content: "Vérifier la légende fermé",
                        trigger: '.o_daterangepicker_legend .o_daterangepicker_closed',
                    }},
                    {{
                        content: "Vérifier la légende indisponible",
                        trigger: '.o_daterangepicker_legend .o_daterangepicker_danger',
                    }},
                    // Tester l'interaction avec le calendrier pour voir les codes couleur
                    {{
                        content: "Ouvrir le calendrier de date de début",
                        trigger: 'input[name="start_date"]',
                        run: 'click',
                    }},
                    {{
                        content: "Vérifier que le calendrier s'ouvre",
                        trigger: '.daterangepicker:visible',
                        run: function() {{
                            // Vérifier la présence des classes CSS personnalisées dans le calendrier
                            const hasColorClasses = $('.daterangepicker td').toArray().some(el => {{
                                const $el = $(el);
                                return $el.hasClass('o_daterangepicker_both') || 
                                       $el.hasClass('o_daterangepicker_pickup') || 
                                       $el.hasClass('o_daterangepicker_return') || 
                                       $el.hasClass('o_daterangepicker_closed') ||
                                       $el.hasClass('o_daterangepicker_danger');
                            }});
                            
                            if (!hasColorClasses) {{
                                console.error("Aucune date n'a de classe de couleur appliquée");
                            }}
                        }},
                    }},
                    {{
                        content: "Sélectionner une date et fermer le calendrier",
                        trigger: '.daterangepicker td:not(.disabled):not(.off):first',
                        run: 'click',
                    }},
                ]);
                }});
            '''.encode('utf-8'),
            'mimetype': 'application/javascript',
            'public': True,
        })

    def test_controller_renting_constraints(self):
        """Test l'appel au contrôleur /rental/product/constraints"""
        # Authentification
        self.authenticate('admin', 'admin')
        
        # Appel au contrôleur
        response = self.url_open('/rental/product/constraints', data=json.dumps({}), headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'  # Pour simuler une requête AJAX
        })
        
        # Vérification
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertIn('all_periods', result)
        
        # Vérifier la liste des périodes
        periods = result['all_periods']
        self.assertTrue(len(periods) > 0)
        
        # Vérifier la structure d'une période
        period = periods[0]
        self.assertIn('id', period)
        self.assertIn('name', period)
        self.assertIn('start_date', period)
        self.assertIn('end_date', period)
        self.assertIn('is_closed', period)
        self.assertIn('minimal_time_duration', period)
        self.assertIn('minimal_time_unit', period)
        self.assertIn('day_configs', period)

    def test_daterangepicker_ui(self):
        """Test le fonctionnement UI du daterangepicker personnalisé"""
        # Lancer le tour daterangepicker
        self.start_tour("/", 'multibikes_daterangepicker_tour', login='admin')

    def test_rental_constraints_validation(self):
        """Test la validation des contraintes (durées minimales, jours fermés)"""
        # Lancer le tour des contraintes
        self.start_tour("/", 'multibikes_rental_constraints_tour', login='admin')

    def test_color_codes_and_legend(self):
        """Test l'affichage des codes couleur et de la légende"""
        # Lancer le tour des codes couleur
        self.start_tour("/", 'multibikes_color_codes_tour', login='admin')

    def test_js_patch_functions(self):
        """Test le fonctionnement des patches JavaScript pour les messages de validation"""
        # Configurer une requête simulée
        product = self.js_test_product
        
        # Simuler une requête au controller avec une période invalide
        with MockRequest(self.env, website=self.website, website_routing=True):
            # Simuler une requête AJAX
            today = fields.Date.today()
            tomorrow = today + timedelta(days=1)
            
            # Récupérer les données des périodes pour l'évaluation des contraintes
            response = self.url_open('/rental/product/constraints', data=json.dumps({}), headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            })
            
            result = json.loads(response.content)
            
            _logger.info(f"Données de périodes reçues: {result['all_periods']}")
            
            # Vérifier que le message d'erreur de durée minimale fonctionne
            # Cette vérification est indirecte via le tour, mais nous pouvons quand même
            # vérifier que les données nécessaires sont bien présentes dans la réponse
            
            has_period_with_minimal_duration = False
            for period in result['all_periods']:
                if period['minimal_time_duration'] > 0:
                    has_period_with_minimal_duration = True
                    break
            
            self.assertTrue(has_period_with_minimal_duration, 
                            "Il devrait y avoir au moins une période avec une durée minimale > 0")
