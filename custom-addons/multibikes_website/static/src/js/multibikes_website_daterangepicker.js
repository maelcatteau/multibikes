/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import WebsiteSaleDaterangePicker from '@website_sale_renting/js/website_sale_renting_daterangepicker';

// Surcharge du widget WebsiteSaleDaterangePicker pour écouter les mises à jour des contraintes
publicWidget.registry.WebsiteSaleDaterangePicker = WebsiteSaleDaterangePicker.extend({
    /**
     * Ajout d'un écouteur pour l'événement renting_constraints_changed lors du démarrage.
     *
     * @override
     */
    start: async function () {
        console.log('[DaterangePicker] Initialisation du widget');
        await this._super.apply(this, arguments);
        // Attacher un écouteur pour les mises à jour des contraintes
        $('.oe_website_sale').on('renting_constraints_changed', this._onRentingConstraintsChanged.bind(this));
        console.log('[DaterangePicker] Écouteur pour renting_constraints_changed attaché');
    },

    /**
     * Nettoyage de l'écouteur lors de la destruction du widget.
     *
     * @override
     */
    destroy: function () {
        console.log('[DaterangePicker] Destruction du widget');
        $('.oe_website_sale').off('renting_constraints_changed', this._onRentingConstraintsChanged.bind(this));
        this._super.apply(this, arguments);
    },

    /**
     * Gestionnaire pour l'événement renting_constraints_changed.
     * Met à jour les contraintes de location lorsque l'événement est reçu.
     *
     * @param {Event} ev
     * @param {Object} constraints
     * @private
     */
    _onRentingConstraintsChanged: function (ev, constraints) {
        console.log('[DaterangePicker] Événement renting_constraints_changed reçu', constraints);
        
        const oldUnavailabilityDays = JSON.stringify(this.rentingUnavailabilityDays || []);
        const oldMinimalTime = JSON.stringify(this.rentingMinimalTime || { duration: 0, unit: 'day', start_date: null, end_date: null });
        
        this.rentingUnavailabilityDays = constraints.rentingUnavailabilityDays || [];
        this.rentingMinimalTime = constraints.rentingMinimalTime || { duration: 0, unit: 'day', start_date: null, end_date: null };
        this.websiteTz = constraints.websiteTz || 'UTC';
        
        console.log('[DaterangePicker] Contraintes mises à jour:');
        console.log('- Jours indisponibles: avant=', oldUnavailabilityDays, ', après=', JSON.stringify(this.rentingUnavailabilityDays));
        console.log('- Durée minimale: avant=', oldMinimalTime, ', après=', JSON.stringify(this.rentingMinimalTime));
        console.log('- Fuseau horaire:', this.websiteTz);
        
        // Vérifier la validité des dates après la mise à jour des contraintes
        this._verifyValidPeriod();
        console.log('[DaterangePicker] Vérification de la période terminée');
    }    
});

export default publicWidget.registry.WebsiteSaleDaterangePicker;
