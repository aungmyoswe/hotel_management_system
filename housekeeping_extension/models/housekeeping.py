from odoo import models, fields, api

class HotelHousekeeping(models.Model):

    _inherit = "hotel.housekeeping"


    # @api.multi
    # def room_clean(self):
    #     """
    #     This method is used to change the state
    #     to clean of the hotel housekeeping
    #     ---------------------------------------
    #     @param self: object pointer
    #     """
      