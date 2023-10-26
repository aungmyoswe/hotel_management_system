from odoo import models, fields, api


class PayCategory(models.Model):
	_name = "pay.category"

	name = fields.Char('Name', size=64, required=True)
	childs = fields.Many2one("pay.category",string="Category")

class HotelFolio(models.Model):
	_inherit = "hotel.folio"

	type_payment = fields.Many2one("pay.category",string="Payment Type",store=True)

class HotelReservation(models.Model):
	_inherit = "hotel.reservation"

	type_payment = fields.Many2one("pay.category",string="Payment Type",store=True)

class QuickRoomReservation(models.TransientModel):
    _inherit = 'quick.room.reservation'

    type_payment = fields.Many2one("pay.category",string="Payment Type",store=True)