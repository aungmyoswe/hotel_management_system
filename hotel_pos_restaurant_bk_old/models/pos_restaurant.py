# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = "pos.order"

    folio_id = fields.Many2one('hotel.folio', 'Folio Number',store=True,copy=True)

    ### Change to save from export_as_JSON from model.js thantshweaung 20181101 start
    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['folio_id'] = ui_order.get('folio_id', False)
        print order_fields['folio_id'],"fo"
        return order_fields

    # @api.onchange('room_id')
    # def get_folio_form_room(self):
    #     value = []
    #     if self.room_id:
    #         folio_line_ids = self.env['hotel.folio.line'].search([('product_id','=',self.room_id.id)])
    #         for folio in folio_line_ids:
    #             if folio.folio_id.state == 'draft':
    #                 value.append(folio.folio_id.id)
    #         folio_ids = self.env['hotel.folio'].search([('id','=',value[0])])
    #         self.folio_id = value[0]
    #         self.partner_id = folio_ids.partner_id
    ### Change to save from export_as_JSON from model.js thantshweaung 20181101 end

class HotelFolio(models.Model):

    _inherit = 'hotel.folio'
    _order = 'folio_pos_order_ids desc'

    folio_pos_order_ids = fields.Many2many('pos.order', 'hotel_pos_rel',
                                           'hotel_folio_id', 'pos_id',
                                           'Orders', store=True, copy=True)

    @api.multi
    def action_invoice_create(self, grouped=False, states=None):
        state = ['confirmed', 'done']
        folio = super(HotelFolio)
        invoice_id = folio.action_invoice_create(grouped=False, states=state)
        for line in self:
            for pos_order in line.folio_pos_order_ids:
                pos_order.write({'invoice_id': invoice_id})
                pos_order.action_invoice_state()
        return invoice_id

    @api.multi
    def action_cancel(self):
        '''
        @param self: object pointer
        '''
        for folio in self:
            for rec in folio.folio_pos_order_ids:
                rec.write({'state': 'cancel'})
        return super(HotelFolio, self).action_cancel()


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def post(self):
        res = super(AccountPayment, self).post()
        for rec in self:
            invoice_id = rec._context.get('active_id', False)
            folio = self.env['hotel.folio'].search([('hotel_invoice_id', '=',
                                                     invoice_id)], limit=1)
            for order in folio.folio_pos_order_ids:
                amount = order.amount_total - order.amount_paid
                data = rec.read()[0]
                data['journal'] = rec.journal_id.id
                data['amount'] = amount
                if amount != 0.0:
                    order.add_payment(data)
                if order.test_paid():
                    order.action_pos_order_paid()
        return res
