// Fichier: /multibikes_website_minimal_duration/static/src/js/rental_constraints.js

odoo.define('multibikes_website_minimal_duration.RentalConstraints', function (require) {
    'use strict';

    // Utiliser la classe PublicWidget correcte
    var publicWidget = require('web.public.widget');
    
    // Étendre le widget existant WebsiteSale
    var WebsiteSale = publicWidget.registry.WebsiteSale;
    
    if (WebsiteSale) {
        WebsiteSale.include({
            /**
             * Surcharge pour intercepter les mises à jour des contraintes de location
             */
            _onChangeCombination: function (ev, $parent, combination) {
                var self = this;
                
                // Appel original
                this._super.apply(this, arguments);
                
                console.log("Combination info:", combination);
                
                // Vérifier si nous avons des informations sur la durée minimale
                if (combination && combination.renting_minimal_duration && combination.renting_minimal_unit) {
                    console.log("Durée minimale détectée:", combination.renting_minimal_duration, combination.renting_minimal_unit);
                    
                    // Mise à jour de l'affichage
                    this._updateMinimalDuration($parent, combination);
                }
            },
            
            /**
             * Met à jour l'affichage de la durée minimale
             */
            _updateMinimalDuration: function ($parent, combination) {
                var duration = combination.renting_minimal_duration;
                var unit = combination.renting_minimal_unit;
                
                // Trouver l'élément à mettre à jour
                var $minimalDuration = $parent.find('.js_minimal_rental_duration, .oe_rental_minimal_duration');
                
                if ($minimalDuration.length) {
                    // Formatter l'unité
                    var unitLabel = unit;
                    if (unit === 'hour') unitLabel = duration > 1 ? 'heures' : 'heure';
                    if (unit === 'day') unitLabel = duration > 1 ? 'jours' : 'jour';
                    if (unit === 'week') unitLabel = duration > 1 ? 'semaines' : 'semaine';
                    
                    // Mettre à jour le texte
                    $minimalDuration.text(duration + ' ' + unitLabel);
                }
            }
        });
    } else {
        console.error("Le widget WebsiteSale n'a pas été trouvé. Vérifiez que le module website_sale est correctement chargé.");
    }
});
