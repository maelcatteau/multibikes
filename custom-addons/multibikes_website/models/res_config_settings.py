from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Période 1 (Basse saison)
    mb_renting_period1_start_date = fields.Date(
        string="Date début période 1",
        related='company_id.mb_renting_period1_start_date',
        readonly=False
    )
    mb_renting_period1_end_date = fields.Date(
        string="Date fin période 1",
        related='company_id.mb_renting_period1_end_date',
        readonly=False
    )
    mb_renting_period1_minimal_time_duration = fields.Integer(
        string="Durée minimale période 1",
        related='company_id.mb_renting_period1_minimal_time_duration',
        readonly=False
    )
    mb_renting_period1_minimal_time_unit = fields.Selection(
        [('hour', 'Heures'), ('day', 'Jours'), ('week', 'Semaine')],
        string="Unité de durée période 1",
        related='company_id.mb_renting_period1_minimal_time_unit',
        readonly=False
    )

    # Période 2 (Moyenne saison)
    mb_renting_period2_start_date = fields.Date(
        string="Date début période 2",
        related='company_id.mb_renting_period2_start_date',
        readonly=False
    )
    mb_renting_period2_end_date = fields.Date(
        string="Date fin période 2",
        related='company_id.mb_renting_period2_end_date',
        readonly=False
    )
    mb_renting_period2_minimal_time_duration = fields.Integer(
        string="Durée minimale période 2",
        related='company_id.mb_renting_period2_minimal_time_duration',
        readonly=False
    )
    mb_renting_period2_minimal_time_unit = fields.Selection(
        [('hour', 'Heures'), ('day', 'Jours'), ('week', 'Semaine')],
        string="Unité de durée période 2",
        related='company_id.mb_renting_period2_minimal_time_unit',
        readonly=False
    )

    # Période 3 (Haute saison)
    mb_renting_period3_start_date = fields.Date(
        string="Date début période 3",
        related='company_id.mb_renting_period3_start_date',
        readonly=False
    )
    mb_renting_period3_end_date = fields.Date(
        string="Date fin période 3",
        related='company_id.mb_renting_period3_end_date',
        readonly=False
    )
    mb_renting_period3_minimal_time_duration = fields.Integer(
        string="Durée minimale période 3",
        related='company_id.mb_renting_period3_minimal_time_duration',
        readonly=False
    )
    mb_renting_period3_minimal_time_unit = fields.Selection(
        [('hour', 'Heures'), ('day', 'Jours'), ('week', 'Semaine')],
        string="Unité de durée période 3",
        related='company_id.mb_renting_period3_minimal_time_unit',
        readonly=False
    )
