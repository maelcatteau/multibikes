/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import WebsiteSaleDaterangePicker from '@website_sale_renting/js/website_sale_renting_daterangepicker';

// Surcharge du widget WebsiteSaleDaterangePicker
publicWidget.registry.WebsiteSaleDaterangePicker = WebsiteSaleDaterangePicker.extend({
    /**
     * Ajout d'un écouteur pour les contraintes et initialisation
     * @override
     */
    start: async function () {
        await this._super.apply(this, arguments);
        
        // Initialiser dailyConfigs au cas où
        this.dailyConfigs = {};
        
        // Attacher un écouteur pour les mises à jour des contraintes
        $('.oe_website_sale').on('renting_constraints_changed', this._onRentingConstraintsChanged.bind(this));
        
        // Ajouter les styles nécessaires
        this._addLegendStyles();
        
        // Ajouter la légende
        this._addLegend();
    },

    /**
     * Nettoyage
     * @override
     */
    destroy: function () {
        $('.oe_website_sale').off('renting_constraints_changed', this._onRentingConstraintsChanged.bind(this));
        this._super.apply(this, arguments);
    },

    /**
     * Met à jour les contraintes quand l'événement est déclenché
     */
    _onRentingConstraintsChanged: function (ev, constraints) {
        console.log('[DaterangePicker] Contraintes reçues:', constraints);
        
        this.rentingUnavailabilityDays = constraints.rentingUnavailabilityDays || [];
        this.rentingMinimalTime = constraints.rentingMinimalTime || { duration: 0, unit: 'day', start_date: null, end_date: null };
        this.websiteTz = constraints.websiteTz || 'UTC';
        
        // Correction: utiliser dailyConfigs, qui est le nom utilisé dans les données reçues
        this.dailyConfigs = constraints.dailyConfigs || {};
        
        console.log('[DaterangePicker] Configurations journalières stockées:', this.dailyConfigs);
    },

    /**
     * Surcharge de la méthode originale pour ajouter nos classes en plus
     * @param {Date} date - La date à évaluer
     * @returns {Array} - Un tableau de classes CSS à appliquer
     */
    _isCustomDate: function (date) {
        // Appel à la méthode originale pour obtenir les classes liées à la disponibilité des produits
        const result = this._super.apply(this, arguments);
        
        // Assurons-nous que result est un tableau
        const classes = Array.isArray(result) ? result : [result].filter(Boolean);
        
        // Si le jour est déjà marqué comme indisponible, on ne fait rien de plus
        if (classes.includes('o_daterangepicker_danger') || classes.includes('disabled')) {
            return classes;
        }
        
        // Ajouter nos propres classes basées sur les contraintes d'ouverture
        const jsDate = date instanceof Date ? date : (date.toDate ? date.toDate() : new Date(date));
        
        // Obtenir le jour de la semaine (0-6, 0=dimanche)
        let dayOfWeek = jsDate.getDay();
        // Convertir en format (0=lundi, 6=dimanche)
        dayOfWeek = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        
        // Obtenir la configuration pour ce jour
        const dayConfig = this.dailyConfigs[dayOfWeek];
        
        if (!dayConfig || !dayConfig.is_open) {
            classes.push('o_daterangepicker_closed');
        } else if (dayConfig.allow_pickup && dayConfig.allow_return) {
            classes.push('o_daterangepicker_both');
        } else if (dayConfig.allow_pickup) {
            classes.push('o_daterangepicker_pickup');
        } else if (dayConfig.allow_return) {
            classes.push('o_daterangepicker_return');
        }
        
        return classes;
    },

    /**
     * Ajoute une légende pour expliquer les couleurs dans le conteneur dédié.
     * @private
     */
    _addLegend: function () {
        const legendContainer = document.getElementById('rental_legend_container');
        
        if (!legendContainer) {
            console.warn("[DaterangePicker] Conteneur de légende 'rental_legend_container' non trouvé.");
            return;
        }
        
        // Vider le conteneur au cas où (si la méthode est appelée plusieurs fois)
        legendContainer.innerHTML = ''; 
        
        const legendHtml = `
            <div class="o_daterangepicker_legend">
                <div class="row">
                    <div class="col-6">
                        <div class="mt-1"><span class="o_legend_color o_daterangepicker_both me-2"></span> Départ et Retour possibles</div>
                        <div class="mt-1"><span class="o_legend_color o_daterangepicker_pickup me-2"></span> Départ uniquement</div>
                        <div class="mt-1"><span class="o_legend_color o_daterangepicker_return me-2"></span> Retour uniquement</div>
                    </div>
                    <div class="col-6">
                        <div class="mt-1"><span class="o_legend_color o_daterangepicker_closed me-2"></span> Fermé</div>
                        <div class="mt-1"><span class="o_legend_color o_daterangepicker_unavailable me-2"></span> Produit indisponible</div>
                    </div>
                </div>
            </div>
        `;
        
        legendContainer.innerHTML = legendHtml;
        console.log('[DaterangePicker] Légende ajoutée dans #rental_legend_container.');
    },
    
    /**
     * Ajoute les styles CSS nécessaires pour la légende et les dates
     */
    _addLegendStyles: function() {
        // Vérifier si les styles sont déjà ajoutés
        if (document.getElementById('daterangepicker-custom-styles')) {
            return;
        }
        
        // Créer un élément de style
        const styleEl = document.createElement('style');
        styleEl.id = 'daterangepicker-custom-styles';
        styleEl.innerHTML = `
            /* Styles pour les légendes */
            .o_daterangepicker_legend .o_legend_color {
                display: inline-block;
                width: 15px;
                height: 15px;
                border-radius: 2px;
            }
            
            /* Styles pour les dates dans le calendrier */
            .daterangepicker td.o_daterangepicker_both:not(.disabled):not(.off) {
                background-color: #fcf8e3 !important;
            }
            .daterangepicker td.o_daterangepicker_pickup:not(.disabled):not(.off) {
                background-color: #dff0d8 !important;
            }
            .daterangepicker td.o_daterangepicker_return:not(.disabled):not(.off) {
                background-color: #d9edf7 !important;
            }
            .daterangepicker td.o_daterangepicker_closed:not(.disabled):not(.off) {
                background-color: #f2dede !important;
            }
            .daterangepicker td.disabled, 
            .daterangepicker td.o_daterangepicker_danger {
                background-color: #ff6b6b !important;
                color: white !important;
            }
            
            /* Styles pour les légendes */
            .o_daterangepicker_legend .o_daterangepicker_both {
                background-color: #fcf8e3;
            }
            .o_daterangepicker_legend .o_daterangepicker_pickup {
                background-color: #dff0d8;
            }
            .o_daterangepicker_legend .o_daterangepicker_return {
                background-color: #d9edf7;
            }
            .o_daterangepicker_legend .o_daterangepicker_closed {
                background-color: #f2dede;
            }
            .o_daterangepicker_legend .o_daterangepicker_unavailable {
                background-color: #ff6b6b;
            }
        `;
        
        // Ajouter au head
        document.head.appendChild(styleEl);
    }
});

export default publicWidget.registry.WebsiteSaleDaterangePicker;
