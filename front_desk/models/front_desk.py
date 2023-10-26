from odoo import models, fields, api

class Partner(models.Model):
    _inherit = "res.partner"

    agency = fields.Boolean("Agency",store=True)
    partner_nrc = fields.Char("NRC",store=True)
    partner_line = fields.One2many("res.partner.line","partner_line_id",string="Line")

class Partner(models.Model):
    _name = "res.partner.line"

    partner_line_id = fields.Many2one("res.partner",string="Partner")
    room_type = fields.Many2one("hotel.room.type",string="Room Type")
    currency = fields.Many2one("res.currency",string="Curency")
    price = fields.Float("Pirce")
