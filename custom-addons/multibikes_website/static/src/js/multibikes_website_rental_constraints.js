/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { rpc } from "@web/core/network/rpc";

// Surcharge du widget WebsiteSale pour ajouter la logique de contraintes de location
WebsiteSale.include({
    /**
     * Surcharge de _onChangeCombination pour déclencher une requête AJAX vers /rental/product/constraints.
     *
     * @param {Event} ev
     * @param {JQueryElement} $parent
     * @param {Object} combination
     * @returns
     */
    _onChangeCombination: function (ev, $parent, combination) {
        const result = this._super.apply(this, arguments);
        this._updateRentalConstraints($parent);
        return result;
    },

    /**
     * Méthode pour charger les contraintes de location lors du démarrage du widget.
     * et les stocker dans l'instance.
     * 
     * @private
     * @returns {Promise} Promesse contenant les contraintes de location
     */
    async _loadRentingConstraints() {
        console.log('[WebsiteSale] _loadRentingConstraints appelé');
        try {
            const constraints = await rpc('/rental/product/constraints', {});
            
            console.log('[WebsiteSale] Contraintes chargées:', constraints);
            this.allPeriods = constraints.all_periods;
            
            return constraints;
        } catch (error) {
            console.error("[WebsiteSale] Erreur lors du chargement des contraintes:", error);
            return null;
        }
    },

    /**
     * Méthode pour mettre à jour les contraintes de locations en 
     * fonction de la date de début de la location. En déclenchant
     * un événement renting_constraints_changed sur le document.
     *
     * @private
     * @param {JQueryElement} $parent - Élément parent du formulaire
     * @returns {Promise} Promesse de mise à jour des contraintes
     */
    _updateRentalConstraints: async function ($parent) {
        console.log('[WebsiteSale] _updateRentalConstraints appelé');
        
        // Obtenir la date de début de location
        const rentingDates = this._getRentingDates();
        const startDate = rentingDates.start_date;
        const productId = this._getProductId($parent?.closest('form'));
        
        console.log('[WebsiteSale] Données initiales:', { 
            startDate: startDate || 'non défini',
            productId: productId || 'non défini'
        });

        // Si nous n'avons pas encore chargé les contraintes, le faire maintenant
        if (!this.allPeriods) {
            await this._loadRentingConstraints();
        }
        
        if (!this.allPeriods) {
            console.warn("[WebsiteSale] Impossible de mettre à jour les contraintes : données non chargées");
            return;
        }

        // Si pas de date de début, utiliser la date actuelle
        let dateToCheck;
        if (!startDate) {
            dateToCheck = new Date();
        } else if (typeof startDate === 'string') {
            dateToCheck = new Date(startDate);
        } else if (startDate instanceof Date) {
            dateToCheck = startDate;
        } else if (startDate.isLuxonDateTime) {
            // Cas d'un objet DateTime Luxon
            dateToCheck = startDate.toJSDate();
        } else {
            dateToCheck = new Date(startDate);
        }
        
        console.log('[WebsiteSale] Date à vérifier:', dateToCheck);
        
        // Formater la date en YYYY-MM-DD pour la comparaison avec les périodes
        const formattedDate = dateToCheck.toISOString().split('T')[0];
        console.log('[WebsiteSale] Date formatée pour comparaison:', formattedDate);
        
        // Trouver la période correspondant à la date
        const matchingPeriod = this.allPeriods.find(period => {
            return period.start_date <= formattedDate && period.end_date >= formattedDate;
        });
        
        console.log('[WebsiteSale] Période correspondante:', matchingPeriod);
        
        if (!matchingPeriod) {
            console.warn(`[WebsiteSale] Aucune période trouvée pour la date ${formattedDate}`);
            // Utiliser les contraintes par défaut si aucune période ne correspond
            return;
        }
        
        // Obtenir le jour de la semaine (0-6, dimanche = 0 en JavaScript)
        const dayOfWeek = dateToCheck.getDay();
        // Ajuster pour avoir lundi = 0, dimanche = 6 (format Odoo)
        const odooDoW = (dayOfWeek + 6) % 7;
        
        console.log('[WebsiteSale] Jour de la semaine (format Odoo):', odooDoW);
        
        // Obtenir la configuration du jour pour cette période
        const dayConfig = matchingPeriod.day_configs[odooDoW];
        
        console.log('[WebsiteSale] Configuration du jour:', dayConfig);
        
        const eventData = {
            rentingUnavailabilityDays: this.rentingUnavailabilityDays,
            rentingMinimalTime: {
                duration: matchingPeriod.minimal_time_duration,
                unit: matchingPeriod.minimal_time_unit,
                name: matchingPeriod.minimal_time_name,
                start_date: matchingPeriod.start_date,
                end_date: matchingPeriod.end_date
            },
            websiteTz: this.websiteTz,
            dailyConfigs: matchingPeriod.day_configs
        };
        
        console.log('[WebsiteSale] Déclenchement événement renting_constraints_changed avec:', eventData);
        
        // Déclencher l'événement DOM
        $('.oe_website_sale').trigger('renting_constraints_changed', eventData);

        return;
    }
});
