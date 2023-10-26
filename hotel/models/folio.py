# from odoo import models,api,fields

# class FolioRecord(models.Model):
# 	_name = "folio.record"

# 	folio_id = fields.Many2one("hotel.folio","Folio",store=True)
# 	folio_room_id = fields.Many2one("hotel.folio.line","Room Folio")
# 	checkin_date = fields.Date("CheckIn")
# 	checkout_date = fields.Date("CheckOut")
# 	product_id = fields.Many2one("hotel.room",related="order_line_id.product_id","Room",store=True)
# 	reservation = fields.Many2one("hotel.reservation","Room",store=True)

