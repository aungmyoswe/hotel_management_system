# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
import datetime
import urllib2
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dt
from odoo.exceptions import except_orm, ValidationError
import pytz


class HotelFolio(models.Model):

    _inherit = 'hotel.folio'
    _order = 'reservation_id desc'

    reservation_id = fields.Many2one('hotel.reservation',
                                     string='Reservation Id')

    @api.multi
    def write(self, vals):
        context = dict(self._context)
        if not context:
            context = {}
        context.update({'from_reservation': True})
        res = super(HotelFolio, self).write(vals)
        reservation_line_obj = self.env['hotel.room.reservation.line']
        for folio_obj in self:
            if folio_obj.reservation_id:
                for reservation in folio_obj.reservation_id:
                    reservation_obj = (reservation_line_obj.search
                                       ([('reservation_id', '=',
                                          reservation.id)]))
                    if len(reservation_obj) == 1:
                        for line_id in reservation.reservation_line:
                            line_id = line_id.reserve
                            for room_id in line_id:
                                vals = {'room_id': room_id.id,
                                        'check_in': folio_obj.checkin_date,
                                        'check_out': folio_obj.checkout_date,
                                        'state': 'assigned',
                                        'reservation_id': reservation.id,
                                        }
                                reservation_obj.write(vals)
        return res


class HotelFolioLineExt(models.Model):

    _inherit = 'hotel.folio.line'

    @api.onchange('checkin_date', 'checkout_date')
    def on_change_checkout(self):
        res = super(HotelFolioLineExt, self).on_change_checkout()
        hotel_room_obj = self.env['hotel.room']
        avail_prod_ids = []
        hotel_room_ids = hotel_room_obj.search([])
        for room in hotel_room_ids:
            assigned = False
            for line in room.room_reservation_line_ids:
                if line.status != 'cancel':
                    if(self.checkin_date <= line.check_in <=
                        self.checkout_date) or (self.checkin_date <=
                                                line.check_out <=
                                                self.checkout_date):
                        assigned = True
                    elif(line.check_in <= self.checkin_date <=
                         line.check_out) or (line.check_in <=
                                             self.checkout_date <=
                                             line.check_out):
                        assigned = True
            if not assigned:
                avail_prod_ids.append(room.product_id.id)
        return res

    @api.multi
    def write(self, vals):
        """
        Overrides orm write method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        update Hotel Room Reservation line history"""
        reservation_line_obj = self.env['hotel.room.reservation.line']
        room_obj = self.env['hotel.room']
        prod_id = vals.get('product_id') or self.product_id.id
        chkin = vals.get('checkin_date') or self.checkin_date
        chkout = vals.get('checkout_date') or self.checkout_date
        is_reserved = self.is_reserved

        if prod_id and is_reserved:
            prod_domain = [('product_id', '=', prod_id)]
            prod_room = room_obj.search(prod_domain, limit=1)

            if (self.product_id and self.checkin_date and self.checkout_date):
                old_prd_domain = [('product_id', '=', self.product_id.id)]
                old_prod_room = room_obj.search(old_prd_domain, limit=1)
                if prod_room and old_prod_room:
                    # check for existing room lines.
                    srch_rmline = [('room_id', '=', old_prod_room.id),
                                   ('check_in', '=', self.checkin_date),
                                   ('check_out', '=', self.checkout_date),
                                   ]
                    rm_lines = reservation_line_obj.search(srch_rmline)
                    if rm_lines:
                        rm_line_vals = {'room_id': prod_room.id,
                                        'check_in': chkin,
                                        'check_out': chkout}
                        rm_lines.write(rm_line_vals)
        return super(HotelFolioLineExt, self).write(vals)


class HotelReservation(models.Model):

    _name = "hotel.reservation"
    _rec_name = "reservation_no"
    _description = "Reservation"
    _order = 'reservation_no desc'
    _inherit = ['mail.thread', 'ir.needaction_mixin']


    @api.model
    def _get_currency(self):
        comp_obj = self.env['res.company']
        currency_obj =self.env['res.currency']
        thb_curr_id = currency_obj.search([('name','=','THB')]).id
        mmk_curr_id = currency_obj.search([('name','=','MMK')]).id
        usd_curr_id = currency_obj.search([('name','=','USD')]).id
        print thb_curr_id, mmk_curr_id, usd_curr_id
        if thb_curr_id or mmk_curr_id or usd_curr_id:
            cur_id = comp_obj.search([('currency_id','in',(thb_curr_id, mmk_curr_id ,usd_curr_id))])
            print cur_id,"Curr"
            return cur_id.currency_id.id


    reservation_no = fields.Char('Reservation No', size=64, readonly=True)
    # date_order = fields.Datetime('Date Ordered', readonly=True, required=True,
    #                              index=True,
    #                              default=(lambda *a: time.strftime(dt)))
    date_order = fields.Datetime('Date Ordered', readonly=True, required=True,
                                 index=True,
                                 default=fields.Date.today())
    warehouse_id = fields.Many2one('stock.warehouse', 'Hotel', readonly=True,
                                   index=True,
                                   required=True, default=1,
                                   states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', 'Guest Name', readonly=True,
                                 index=True,
                                 required=True,
                                 states={'draft': [('readonly', False)]})
    pricelist_id = fields.Many2one('product.pricelist', 'Scheme',
                                   required=True, readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   help="Pricelist for current reservation.")
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address',
                                         readonly=True,
                                         states={'draft':
                                                 [('readonly', False)]},
                                         help="Invoice address for "
                                         "current reservation.")
    partner_order_id = fields.Many2one('res.partner', 'Ordering Contact',
                                       readonly=True,
                                       states={'draft':
                                               [('readonly', False)]},
                                       help="The name and address of the "
                                       "contact that requested the order "
                                       "or quotation.")
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address',
                                          readonly=True,
                                          states={'draft':
                                                  [('readonly', False)]},
                                          help="Delivery address"
                                          "for current reservation. ")
    checkin = fields.Datetime('Expected-Date-Arrival', required=True,
                              readonly=True,
                              states={'draft': [('readonly', False)]})
    checkout = fields.Datetime('Expected-Date-Departure', required=True,
                               readonly=True,
                               states={'draft': [('readonly', False)]})
    adults = fields.Integer('Adults', size=64, readonly=True,
                            states={'draft': [('readonly', False)]},
                            help='List of adults there in guest list. ')
    children = fields.Integer('Children', size=64, readonly=True,
                              states={'draft': [('readonly', False)]},
                              help='Number of children there in guest list.')
    reservation_line = fields.One2many('hotel_reservation.line', 'line_id',
                                       'Reservation Line',
                                       help='Hotel room reservation details.',
                                       readonly=True,
                                       states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('cancel', 'Cancel'), ('done', 'Done')],
                             'State', readonly=True,
                             default=lambda *a: 'draft')
    folio_id = fields.Many2many('hotel.folio', 'hotel_folio_reservation_rel',
                                'order_id', 'invoice_id', string='Folio')
    dummy = fields.Datetime('Dummy')
    # company_id = fields.Many2one("res.company",string="Company",related="order_id")
    currency_id = fields.Many2one("res.currency",string="Currency",default=_get_currency,store=True)
    agency = fields.Many2one("res.partner",domain="[('agency','=',True)]",string="Agency",store=True)
    type_payment = fields.Many2one("pay.category",string="Payment Type",store=True)
    

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        for reserv_rec in self:
            if reserv_rec.state != 'draft':
                raise ValidationError(_('You cannot delete Reservation in %s\
                state.') % (reserv_rec.state))
        return super(HotelReservation, self).unlink()

    @api.constrains('reservation_line', 'adults', 'children')
    def check_reservation_rooms(self):
        '''
        This method is used to validate the reservation_line.
        -----------------------------------------------------
        @param self: object pointer
        @return: raise a warning depending on the validation
        '''
        for reservation in self:
            cap = 0
            for rec in reservation.reservation_line:
                if len(rec.reserve) == 0:
                    raise ValidationError(_('Please Select Rooms \
                    For Reservation.'))
                for room in rec.reserve:
                    cap += room.capacity
            if (reservation.adults + reservation.children) > cap:
                raise ValidationError(_('Room Capacity Exceeded \n Please \
                                        Select Rooms According to Members \
                                        Accomodation.'))
            if reservation.adults <= 0:
                raise ValidationError(_('Adults must be more than 0'))

    @api.constrains('checkin', 'checkout')
    def check_in_out_dates(self):
        """
        When date_order is less then checkin date or
        Checkout date should be greater than the checkin date.
        """
        if self.checkout and self.checkin:
            # if quick_reservation==True:
                # if self.checkin != self.date_order:
                #     raise except_orm(_('Warning'), _('Checkin date should be \
                #     equal current date.')) 
            # else: 
            if self.checkin < self.date_order:
                raise except_orm(_('Warning'), _('Checkin date should be \
                greater than the current date.'))
            if self.checkout < self.checkin:
                raise except_orm(_('Warning'), _('Checkout date \
                should be greater than Checkin date.'))

    @api.model
    def _needaction_count(self, domain=None):
        """
         Show a count of draft state reservations on the menu badge.
         """
        return self.search_count([('state', '=', 'draft')])

    @api.onchange('checkout', 'checkin')
    def on_change_checkout(self):
        '''
        When you change checkout or checkin update dummy field
        -----------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        checkout_date = time.strftime(dt)
        checkin_date = time.strftime(dt)
        if not (checkout_date and checkin_date):
            return {'value': {}}
        delta = timedelta(days=1)
        dat_a = time.strptime(checkout_date, dt)[:5]
        addDays = datetime(*dat_a) + delta
        self.dummy = addDays.strftime(dt)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''
        When you change partner_id it will update the partner_invoice_id,
        partner_shipping_id and pricelist_id of the hotel reservation as well
        ---------------------------------------------------------------------
        @param self: object pointer
        '''
        if not self.partner_id:
            self.partner_invoice_id = False
            self.partner_shipping_id = False
            self.partner_order_id = False
        else:
            addr = self.partner_id.address_get(['delivery', 'invoice',
                                                'contact'])
            self.partner_invoice_id = addr['invoice']
            self.partner_order_id = addr['contact']
            self.partner_shipping_id = addr['delivery']
            self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.multi
    def check_overlap(self, date1, date2):
        delta = date2 - date1
        return set([date1 + timedelta(days=i) for i in range(delta.days + 1)])

    @api.multi
    def confirmed_reservation(self):
        """
        This method create a new recordset for hotel room reservation line
        ------------------------------------------------------------------
        @param self: The object pointer
        @return: new record set for hotel room reservation line.
        """
        reservation_line_obj = self.env['hotel.room.reservation.line']
        for reservation in self:
            for line_id in reservation.reservation_line:
                for room_id in line_id.reserve:
                    if room_id.room_reservation_line_ids:
                        print room_id.room_reservation_line_ids,"Heloo"
                        for reserv in room_id.room_reservation_line_ids.\
                                search([('status', '=', 'confirm')]):
                            reserv_checkin = datetime.\
                                strptime(reservation.checkin, dt)
                            reserv_checkout = datetime.\
                                strptime(reservation.checkout, dt)
                            check_in = datetime.strptime(reserv.check_in, dt)
                            check_out = datetime.strptime(reserv.check_out, dt)
                            range1 = [reserv_checkin, reserv_checkout]
                            range2 = [check_in, check_out]
                            overlap_dates = self.check_overlap(*range1) \
                                & self.check_overlap(*range2)
                            if overlap_dates:
                                print overlap_dates,"DATE"
                                overlap_dates = [datetime.
                                                 strftime(dates,
                                                          '%d/%m/%Y') for
                                                 dates in overlap_dates]
                                raise ValidationError(_('You tried to Confirm '
                                                        'reservation with room'
                                                        ' those already '
                                                        'reserved in this '
                                                        'Reservation Period. '
                                                        'Overlap Dates are '
                                                        '%s') % overlap_dates)
                            else:
                                print self.state,"State"
                                self.state = 'confirm'
                                for room_id in line_id.reserve:
                                    vals = {'room_id': room_id.id,
                                            'check_in': reservation.checkin,
                                            'check_out': reservation.checkout,
                                            'state': 'assigned',
                                            'reservation_id': reservation.id,
                                            }
                                    room_id.write({'isroom': False,
                                                   'status': 'occupied'})
                                    reservation_line_obj.create(vals)
                    else:
                        self.state = 'confirm'
                        for room_id in line_id.reserve:
                            vals = {'room_id': room_id.id,
                                    'check_in': reservation.checkin,
                                    'check_out': reservation.checkout,
                                    'state': 'assigned',
                                    'reservation_id': reservation.id,
                                    }
                            room_id.write({'isroom': False,
                                           'status': 'occupied'})
                            reservation_line_obj.create(vals)
#             self._cr.execute("select count(*) from hotel_reservation as hr "
#                              "inner join hotel_reservation_line as hrl on \
#                              hrl.line_id = hr.id "
#                              "inner join hotel_reservation_line_room_rel as \
#                              hrlrr on hrlrr.room_id = hrl.id "
#                              "where (checkin,checkout) overlaps \
#                              ( timestamp %s, timestamp %s ) "
#                              "and hr.id <> cast(%s as integer) "
#                              "and hr.state = 'confirm' "
#                              "and hrlrr.hotel_reservation_line_id in ("
#                              "select hrlrr.hotel_reservation_line_id \
#                              from hotel_reservation as hr "
#                              "inner join hotel_reservation_line as \
#                              hrl on hrl.line_id = hr.id "
#                              "inner join hotel_reservation_line_room_rel \
#                              as hrlrr on hrlrr.room_id = hrl.id "
#                              "where hr.id = cast(%s as integer) )",
#                              (reservation.checkin, reservation.checkout,
#                               str(reservation.id), str(reservation.id)))
#             res = self._cr.fetchone()
#             roomcount = res and res[0] or 0.0
#             if roomcount:
#                 raise ValidationError(_('You tried to confirm reservation \
#                 with room those already reserved in this reservation \
#                     period'))
#             else:
#                 self.state = 'confirm'
#                 for line_id in reservation.reservation_line:
#                     line_id = line_id.reserve
#                     for room_id in line_id:
#                         vals = {
#                             'room_id': room_id.id,
#                             'check_in': reservation.checkin,
#                             'check_out': reservation.checkout,
#                             'state': 'assigned',
#                             'reservation_id': reservation.id,
#                             }
#                         room_id.write({'isroom': False,
#                                          'status': 'occupied'})
#                         reservation_line_obj.create(vals)
        return True

    @api.multi
    def cancel_reservation(self):
        """
        This method cancel recordset for hotel room reservation line
        ------------------------------------------------------------------
        @param self: The object pointer
        @return: cancel record set for hotel room reservation line.
        """
        room_res_line_obj = self.env['hotel.room.reservation.line']
        hotel_res_line_obj = self.env['hotel_reservation.line']
        self.state = 'cancel'
        room_reservation_line = room_res_line_obj.search([('reservation_id',
                                                           'in', self.ids)])
        room_reservation_line.write({'state': 'unassigned'})
        reservation_lines = hotel_res_line_obj.search([('line_id',
                                                        'in', self.ids)])
        for reservation_line in reservation_lines:
            reservation_line.reserve.write({'isroom': True,
                                            'status': 'available'})
        return True

    @api.multi
    def set_to_draft_reservation(self):
        self.state = 'draft'
        return True

    @api.multi
    def send_reservation_maill(self):
        '''
        This function opens a window to compose an email,
        template message loaded by default.
        @param self: object pointer
        '''
        assert len(self._ids) == 1, 'This is for a single id at a time.'
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = (ir_model_data.get_object_reference
                           ('hotel_reservation',
                            'email_template_hotel_reservation')[1])
        except ValueError:
            template_id = False
        try:
            compose_form_id = (ir_model_data.get_object_reference
                               ('mail',
                                'email_compose_message_wizard_form')[1])
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'hotel.reservation',
            'default_res_id': self._ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_send': True,
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
            'force_send': True
        }

    @api.multi
    def create_folio(self):
        """
        This method is for create new hotel folio.
        -----------------------------------------
        @param self: The object pointer
        @return: new record set for hotel folio.
        """
        hotel_folio_obj = self.env['hotel.folio']
        room_obj = self.env['hotel.room']
        payment_obj =self.env['payment.type']
        tm_delta = timedelta(days=1)
        tm_dt = timedelta(hours=6,minutes=30)
        partner_obj = self.env['res.partner']
        partner_line_obj = self.env['res.partner.line']
        for reservation in self:
            folio_lines = []
            checkin_date = reservation['checkin']
            if self._context.get('tz', False):
                    timezone = pytz.timezone(self._context.get('tz', False))
            else:
                timezone = pytz.timezone('UTC')
            che_in_obj = datetime.strptime(checkin_date, dt)\
                .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            temp_date = che_in_obj
            checkin = temp_date
            checkin_time_dt = temp_date - tm_dt
            checkout_date = temp_date + tm_delta 
            checkin_time = datetime.strftime(checkin,'%Y-%m-%d %H:%M:%S')
            in_check = datetime.strftime(checkin,'%Y-%m-%d 12:00:00')
            print checkin_time,"normal",in_check,"c in"
            print checkin_time_dt,"cindt"
            if checkin_time < in_check:
                checkin_date = datetime.strftime(checkin_time_dt,'%Y-%m-%d %H:%M:%S')
                checkout_date = datetime.strftime(checkin,'%Y-%m-%d 05:30:00')
                print checkout_date,"checkkkkkkkkkkkkkkkout"
            else:
                print reservation['checkout'],"Checkout"
                checkin_date =datetime.strftime(checkin_time_dt,'%Y-%m-%d %H:%M:%S')
                checkout_date = datetime.strftime(checkout_date,'%Y-%m-%d 05:30:00')
                print checkout_date,"checkkkkkkkkkkkkout"
                print checkout_date,"CheckOut"
            if not self.checkin < self.checkout:
                raise except_orm(_('Error'),
                                 _('Checkout date should be greater \
                                 than the Checkin date.'))
            duration_vals = (self.onchange_check_dates
                             (checkin_date=checkin_date,
                              checkout_date=checkout_date, duration=False))
            duration = duration_vals.get('duration') or 0.0
            for line in reservation.reservation_line:
                for r in line.reserve:
                    room_ids = room_obj.search([('product_id','=',r.product_id.id)])
                    print room_ids,"room"
                    folio_vals = {
                        'date_order': reservation.date_order,
                        'warehouse_id': reservation.warehouse_id.id,
                        'partner_id': reservation.partner_id.id,
                        'pricelist_id': reservation.pricelist_id.id,
                        'partner_invoice_id': reservation.partner_invoice_id.id,
                        'partner_shipping_id': reservation.partner_shipping_id.id,
                        'checkin_date': checkin_date,
                        'checkout_date': checkout_date,
                        'currency':reservation.currency_id.id,
                        'agency':reservation.agency.id,
                        'type_payment':reservation.type_payment.id,
                        'duration': duration,
                        'room_ids':room_ids.id,
                        'reservation_id': reservation.id,
                        'service_lines': reservation['folio_id']
                    }
                    for line in reservation.reservation_line:
                        for r in line.reserve:
                            room_ids = room_obj.search([('product_id','=',r.product_id.id)])
                            print room_ids,"room"
                            if self.agency:
                                partner_line_ids = partner_line_obj.search([('partner_line_id','=',self.agency.id),('room_type','=',room_ids.categ_id.id),('currency','=',self.currency_id.id)])
                                print partner_line_ids.price,"price"
                                price=partner_line_ids.price
                            else:
                                pay_ids = payment_obj.search([('room_charges','=',room_ids.id),('currency','=',reservation.currency_id.id)])
                                print pay_ids.price,"Pays"
                                price = pay_ids.price
                            print  checkin_date,"Check in"
                            print checkout_date,"Check Out"
                            folio_lines.append((0, 0, {
                                'checkin_date': checkin_date,
                                'checkout_date': checkout_date,
                                'product_id': r.product_id and r.product_id.id,
                                'name': reservation['reservation_no'],
                                'price_unit':price,
                                'currency':reservation.currency_id.id,
                                'product_uom_qty': duration,
                                'is_reserved': True}))
                            res_obj = room_obj.browse([r.id])
                            res_obj.write({'status': 'occupied', 'isroom': False})
                    folio_vals.update({'room_lines': folio_lines})
                    folio = hotel_folio_obj.create(folio_vals)
                    if folio:
                        for rm_line in folio.room_lines:
                            rm_line.product_id_change()
                    self._cr.execute('insert into hotel_folio_reservation_rel'
                                     '(order_id, invoice_id) values (%s,%s)',
                                     (reservation.id, folio.id))
                    self.state = 'done'
                return True

    @api.multi
    def onchange_check_dates(self, checkin_date=False, checkout_date=False,
                             duration=False):
        '''
        This method gives the duration between check in checkout if
        customer will leave only for some hour it would be considers
        as a whole day. If customer will checkin checkout for more or equal
        hours, which configured in company as additional hours than it would
        be consider as full days
        --------------------------------------------------------------------
        @param self: object pointer
        @return: Duration and checkout_date
        '''
        value = {}
        configured_addition_hours = 0
        wc_id = self.warehouse_id
        whcomp_id = wc_id or wc_id.company_id
        if whcomp_id:
            configured_addition_hours = wc_id.company_id.additional_hours
        duration = 0
        if checkin_date and checkout_date:
            print checkin_date,checkout_date,"tdate"
            chkin_dt = datetime.strptime(checkin_date, dt)
            chkout_dt = datetime.strptime(checkout_date, dt)
            dur = chkout_dt - chkin_dt
            duration = dur.days + 1
            if configured_addition_hours > 0:
                additional_hours = abs((dur.seconds / 60))
                if additional_hours <= abs(configured_addition_hours * 60):
                    duration -= 1
        value.update({'duration': duration})
        return value

    @api.model
    def create(self, vals):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        if not vals:
            vals = {}
        if self._context is None:
            self._context = {}
        vals['reservation_no'] = self.env['ir.sequence'
                                          ].get('hotel.reservation')
        return super(HotelReservation, self).create(vals)


class HotelReservationLine(models.Model):

    _name = "hotel_reservation.line"
    _description = "Reservation Line"

    name = fields.Char('Name', size=64)
    line_id = fields.Many2one('hotel.reservation')
    reserve = fields.Many2many('hotel.room',
                               'hotel_reservation_line_room_rel',
                               'hotel_reservation_line_id', 'room_id',
                               domain="[('isroom','=',True),\
                               ('categ_id','=',categ_id)]")
    categ_id = fields.Many2one('hotel.room.type', 'Room Type')

    @api.onchange('categ_id')
    def on_change_categ(self):
        '''
        When you change categ_id it check checkin and checkout are
        filled or not if not then raise warning
        -----------------------------------------------------------
        @param self: object pointer
        '''
        hotel_room_obj = self.env['hotel.room']
        hotel_room_ids = hotel_room_obj.search([('categ_id', '=',
                                                 self.categ_id.id)])
        room_ids = []
        if not self.line_id.checkin:
            raise except_orm(_('Warning'),
                             _('Before choosing a room,\n You have to select \
                             a Check in date or a Check out date in \
                             the reservation form.'))
        for room in hotel_room_ids:
            assigned = False
            for line in room.room_reservation_line_ids:
                if line.status != 'cancel':
                    if(self.line_id.checkin <= line.check_in <=
                        self.line_id.checkout) or (self.line_id.checkin <=
                                                   line.check_out <=
                                                   self.line_id.checkout):
                        assigned = True
                    elif(line.check_in <= self.line_id.checkin <=
                         line.check_out) or (line.check_in <=
                                             self.line_id.checkout <=
                                             line.check_out):
                        assigned = True
            for rm_line in room.room_line_ids:
                if rm_line.status != 'cancel':
                    if(self.line_id.checkin <= rm_line.check_in <=
                       self.line_id.checkout) or (self.line_id.checkin <=
                                                  rm_line.check_out <=
                                                  self.line_id.checkout):
                        assigned = True
                    elif(rm_line.check_in <= self.line_id.checkin <=
                         rm_line.check_out) or (rm_line.check_in <=
                                                self.line_id.checkout <=
                                                rm_line.check_out):
                        assigned = True
            if not assigned:
                room_ids.append(room.id)
        domain = {'reserve': [('id', 'in', room_ids)]}
        return {'domain': domain}

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        hotel_room_reserv_line_obj = self.env['hotel.room.reservation.line']
        for reserv_rec in self:
            for rec in reserv_rec.reserve:
                hres_arg = [('room_id', '=', rec.id),
                            ('reservation_id', '=', reserv_rec.line_id.id)]
                myobj = hotel_room_reserv_line_obj.search(hres_arg)
                if myobj.ids:
                    rec.write({'isroom': True, 'status': 'available'})
                    myobj.unlink()
        return super(HotelReservationLine, self).unlink()


class HotelRoomReservationLine(models.Model):

    _name = 'hotel.room.reservation.line'
    _description = 'Hotel Room Reservation'
    _rec_name = 'room_id'

    room_id = fields.Many2one('hotel.room', string='Room id')
    check_in = fields.Datetime('Check In Date', required=True)
    check_out = fields.Datetime('Check Out Date', required=True)
    state = fields.Selection([('assigned', 'Assigned'),
                              ('unassigned', 'Unassigned')], 'Room Status')
    reservation_id = fields.Many2one('hotel.reservation',
                                     string='Reservation')
    status = fields.Selection(string='state', related='reservation_id.state')


class HotelRoom(models.Model):

    _inherit = 'hotel.room'
    _description = 'Hotel Room'

    room_reservation_line_ids = fields.One2many('hotel.room.reservation.line',
                                                'room_id',
                                                string='Room Reserve Line')

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        for room in self:
            for reserv_line in room.room_reservation_line_ids:
                if reserv_line.status == 'confirm':
                    raise ValidationError(_('User is not able to delete the \
                                            room after the room in %s state \
                                            in reservation')
                                          % (reserv_line.status))
        return super(HotelRoom, self).unlink()

    @api.model
    def cron_room_line(self):
        """
        This method is for scheduler
        every 1min scheduler will call this method and check Status of
        room is occupied or available
        --------------------------------------------------------------
        @param self: The object pointer
        @return: update status of hotel room reservation line
        """
        reservation_line_obj = self.env['hotel.room.reservation.line']
        folio_room_line_obj = self.env['folio.room.line']
        now = datetime.datetime.now()
        curr_date = now.strftime(dt)
        for room in self.search([]):
            reserv_line_ids = [reservation_line.ids for
                               reservation_line in
                               room.room_reservation_line_ids]
            reserv_args = [('id', 'in', reserv_line_ids),
                           ('check_in', '<=', curr_date),
                           ('check_out', '>=', curr_date)]
            reservation_line_ids = reservation_line_obj.search(reserv_args)
            rooms_ids = [room_line.ids for room_line in room.room_line_ids]
            rom_args = [('id', 'in', rooms_ids),
                        ('check_in', '<=', curr_date),
                        ('check_out', '>=', curr_date)]
            room_line_ids = folio_room_line_obj.search(rom_args)
            status = {'isroom': True, 'color': 5}
            if reservation_line_ids.ids:
                status = {'isroom': False, 'color': 2}
            room.write(status)
            if room_line_ids.ids:
                status = {'isroom': False, 'color': 2}
            room.write(status)
            if reservation_line_ids.ids and room_line_ids.ids:
                raise except_orm(_('Wrong Entry'),
                                 _('Please Check Rooms Status \
                                 for %s.' % (room.name)))
        return True


class RoomReservationSummary(models.Model):

    _name = 'room.reservation.summary'
    _description = 'Room reservation summary'

    name = fields.Char('Reservation Summary', default='Reservations Summary',
                       invisible=True)
    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')
    summary_header = fields.Text('Summary Header')
    room_summary = fields.Text('Room Summary')

    @api.model
    def default_get(self, fields):
        """
        To get default values for the object.
        @param self: The object pointer.
        @param fields: List of fields for which we want default values
        @return: A dictionary which of fields with values.
        """
        if self._context is None:
            self._context = {}
        res = super(RoomReservationSummary, self).default_get(fields)
        # Added default datetime as today and date to as today + 30.
        from_dt = datetime.today()
        dt_from = from_dt.strftime(dt)
        to_dt = from_dt + relativedelta(days=30)
        dt_to = to_dt.strftime(dt)
        res.update({'date_from': dt_from, 'date_to': dt_to})

        if not self.date_from and self.date_to:
            date_today = datetime.datetime.today()
            first_day = datetime.datetime(date_today.year,
                                          date_today.month, 1, 0, 0, 0)
            first_temp_day = first_day + relativedelta(months=1)
            last_temp_day = first_temp_day - relativedelta(days=1)
            last_day = datetime.datetime(last_temp_day.year,
                                         last_temp_day.month,
                                         last_temp_day.day, 23, 59, 59)
            date_froms = first_day.strftime(dt)
            date_ends = last_day.strftime(dt)
            res.update({'date_from': date_froms, 'date_to': date_ends})
        return res

    @api.multi
    def room_reservation(self):
        '''
        @param self: object pointer
        '''
        mod_obj = self.env['ir.model.data']
        if self._context is None:
            self._context = {}
        model_data_ids = mod_obj.search([('model', '=', 'ir.ui.view'),
                                         ('name', '=',
                                          'view_hotel_reservation_form')])
        resource_id = model_data_ids.read(fields=['res_id'])[0]['res_id']
        return {'name': _('Reconcile Write-Off'),
                'context': self._context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'hotel.reservation',
                'views': [(resource_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                }

    @api.onchange('date_from', 'date_to')
    def get_room_summary(self):
        '''
        @param self: object pointer
         '''
        res = {}
        all_detail = []
        room_obj = self.env['hotel.room']
        reservation_line_obj = self.env['hotel.room.reservation.line']
        folio_room_line_obj = self.env['folio.room.line']
        hotel_folio_line_obj = self.env['hotel.folio.line']
        user_obj = self.env['res.users']
        date_range_list = []
        main_header = []
        summary_header_list = ['Rooms']
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise except_orm(_('User Error!'),
                                 _('Please Check Time period Date \
                                 From can\'t be greater than Date To !'))
            if self._context.get('tz', False):
                timezone = pytz.timezone(self._context.get('tz', False))
            else:
                timezone = pytz.timezone('UTC')
            d_frm_obj = datetime.strptime(self.date_from, dt)\
                .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            d_to_obj = datetime.strptime(self.date_to, dt)\
                .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            temp_date = d_frm_obj
            while(temp_date <= d_to_obj):
                val = ''
                val = (str(temp_date.strftime("%a")) + ' ' +
                       str(temp_date.strftime("%b")) + ' ' +
                       str(temp_date.strftime("%d")))
                summary_header_list.append(val)
                date_range_list.append(temp_date.strftime
                                       (dt))
                temp_date = temp_date + timedelta(days=1)
            all_detail.append(summary_header_list)
            room_ids = room_obj.search([])
            all_room_detail = []
            for room in room_ids:
                room_detail = {}

                room_list_stats = []
                room_detail.update({'name': room.name or ''})
                if not room.room_reservation_line_ids and \
                   not room.room_line_ids:
                    for chk_date in date_range_list:
                        room_list_stats.append({'state': 'Free',
                                                'date': chk_date,
                                                'room_id': room.id})
                else:
                    for chk_date in date_range_list:
                        ch_dt = chk_date[:10] + ' 23:59:59'
                        ttime = datetime.strptime(ch_dt, dt)
                        c = ttime.replace(tzinfo=timezone).\
                            astimezone(pytz.timezone('UTC'))
                        chk_date = c.strftime(dt)
                         # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 start #1


                        reserline_ids = room.room_reservation_line_ids.ids

                        reservline_ids = (hotel_folio_line_obj.search
                                          ([('product_id', 'in', room.product_id.ids),
                                            ('checkin_date', '<=', chk_date),
                                            ('checkout_date', '>=', chk_date),
                                            ('state', 'in', ['sale', 'done']),
                                            # ('status', '=', 'done')
                                            ]))

                        draft_folio_ids = (hotel_folio_line_obj.search
                                          ([('product_id', 'in', room.product_id.ids),
                                            ('checkin_date', '<=', chk_date),
                                            ('checkout_date', '>=', chk_date),
                                            ('state', '=', 'draft'),
                                            # ('status', '=', 'done')
                                            ]))

                        reservline_new_ids = (reservation_line_obj.search
                                          ([('id', 'in', reserline_ids),
                                            ('check_in', '<=', chk_date),
                                            ('check_out', '>=', chk_date),
                                            ('state', '=', 'assigned'),
                                            ('status', '=', 'confirm')
                                            ]))

                        occupied_ids = room.room_line_ids.ids
                        folio_occupied_ids = (folio_room_line_obj.search
                                          ([('id', 'in', occupied_ids),
                                            ('check_in', '<=', chk_date),
                                            ('check_out', '>=', chk_date),
                                            ('status', '=',['sale', 'done'])
                                            ]))

                        folio_occupy_ids = (folio_room_line_obj.search
                                              ([('id', 'in', occupied_ids),
                                                ('check_in', '<=', chk_date),
                                                ('check_out', '>=', chk_date),
                                                ('status', 'in', ['draft'])
                                                ]))

#                         if not reservline_ids and not reservline_new_ids:
#                             # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 end #
#                         # if not reservline_ids and not reservline_new_ids:
#                         # reservline_ids = (reservation_line_obj.search
#                         #                   ([('id', 'in', reserline_ids),
#                         #                     ('check_in', '<=', chk_date),
#                         #                     ('check_out', '>=', chk_date),
#                         #                     ('state', '=', 'assigned')
#                         #                     ]))
#                         # if not reservline_ids:
#                             sdt = dt
#                             chk_date = datetime.strptime(chk_date, sdt)
#                             chk_date = datetime.\
#                                 strftime(chk_date - timedelta(days=1), sdt)
#                             reservline_ids = (reservation_line_obj.search
#                                               ([('id', 'in', reserline_ids),
#                                                 ('check_in', '<=', chk_date),
#                                                 ('check_out', '>=', chk_date),
#                                                 ('state', '=', 'assigned')]))
#                             for res_room in reservline_ids:
#                                 rrci = res_room.check_in
#                                 rrco = res_room.check_out
#                                 cid = datetime.strptime(rrci, dt)
#                                 cod = datetime.strptime(rrco, dt)
#                                 dur = cod - cid
#                                 if room_list_stats:
#                                     count = 0
#                                     for rlist in room_list_stats:
#                                         cidst = datetime.strftime(cid, dt)
#                                         codst = datetime.strftime(cod, dt)
#                                         rm_id = res_room.room_id.id
#                                         ci = rlist.get('date') >= cidst
#                                         co = rlist.get('date') <= codst
#                                         rm = rlist.get('room_id') == rm_id
#                                         st = rlist.get('state') == 'Reserved'
#                                         if ci and co and rm and st:
#                                             count += 1
#                                     if count - dur.days == 0:
#                                         c_id1 = user_obj.browse(self._uid)
#                                         c_id = c_id1.company_id
#                                         con_add = 0
#                                         amin = 0.0
#                                         if c_id:
#                                             con_add = c_id.additional_hours
# #                                        When configured_addition_hours is
# #                                        greater than zero then we calculate
# #                                        additional minutes
#                                         if con_add > 0:
#                                             amin = abs(con_add * 60)
#                                         hr_dur = abs((dur.seconds / 60))
# #                                        When additional minutes is greater
# #                                        than zero then check duration with
# #                                        extra minutes and give the room
# #                                        reservation status is reserved or
# #                                        free
#                                         if amin > 0:
#                                             if hr_dur >= amin:
#                                                 reservline_ids = True
#                                             else:
#                                                 reservline_ids = False
#                                         else:
#                                             if hr_dur > 0:
#                                                 reservline_ids = True
#                                             else:
#                                                 reservline_ids = False
#                                     else:
#                                         reservline_ids = False
                        fol_room_line_ids = room.room_line_ids.ids
                        chk_state = ['draft', 'cancel']
                        folio_resrv_ids = (folio_room_line_obj.search
                                           ([('id', 'in', fol_room_line_ids),
                                             ('check_in', '<=', chk_date),
                                             ('check_out', '>=', chk_date),
                                             ('status', 'not in', chk_state)
                                             ]))
                        # if reservline_ids or folio_resrv_ids:
                            # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 start #2

                        if folio_occupy_ids or draft_folio_ids:
                            room_list_stats.append({'state': 'Check In',
                                                    'date': chk_date,
                                                    'room_id': room.id,
                                                    'is_draft': 'No',
                                                    'data_model': '',
                                                    'data_id': 0})
                        elif reservline_new_ids:
                            room_list_stats.append({'state': 'Reserved',
                                                    'date': chk_date,
                                                    'room_id': room.id,
                                                    'is_draft': 'No',
                                                    'data_model': '',
                                                    'data_id': 0})
                        # elif reservline_ids or folio_resrv_ids:
                        elif reservline_ids or folio_occupied_ids:
                            room_list_stats.append({'state': 'Check Out',
                                                    'date': chk_date,
                                                    'room_id': room.id,
                                                    'is_draft': 'No',
                                                    'data_model': '',
                                                    'data_id': 0})

                            # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 end #1
                            # room_list_stats.append({'state': 'Reserved',
                            #                         'date': chk_date,
                            #                         'room_id': room.id,
                            #                         'is_draft': 'No',
                            #                         'data_model': '',
                            #                         'data_id': 0})
                        else:
                            room_list_stats.append({'state': 'Free',
                                                    'date': chk_date,
                                                    'room_id': room.id})

                room_detail.update({'value': room_list_stats})
                all_room_detail.append(room_detail)
            main_header.append({'header': summary_header_list})
            self.summary_header = str(main_header)
            self.room_summary = str(all_room_detail)
        return res
# @api.onchange('date_from', 'date_to')
#     def get_room_summary(self):
#         '''
#         @param self: object pointer
#          '''
#         res = {}
#         all_detail = []
#         room_obj = self.env['hotel.room']
#         reservation_line_obj = self.env['hotel.room.reservation.line']
#         folio_room_line_obj = self.env['folio.room.line']
#         hotel_folio_line_obj = self.env['hotel.folio.line']
#         user_obj = self.env['res.users']
#         date_range_list = []
#         main_header = []
#         summary_header_list = ['Rooms']
#         if self.date_from and self.date_to:
#             if self.date_from > self.date_to:
#                 raise except_orm(_('User Error!'),
#                                  _('Please Check Time period Date \
#                                  From can\'t be greater than Date To !'))
#             if self._context.get('tz', False):
#                 timezone = pytz.timezone(self._context.get('tz', False))
#             else:
#                 timezone = pytz.timezone('UTC')
#             d_frm_obj = datetime.strptime(self.date_from, dt)\
#                 .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
#             d_to_obj = datetime.strptime(self.date_to, dt)\
#                 .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
#             temp_date = d_frm_obj
#             while(temp_date <= d_to_obj):
#                 val = ''
#                 val = (str(temp_date.strftime("%a")) + ' ' +
#                        str(temp_date.strftime("%b")) + ' ' +
#                        str(temp_date.strftime("%d")))
#                 summary_header_list.append(val)
#                 date_range_list.append(temp_date.strftime
#                                        (dt))
#                 temp_date = temp_date + timedelta(days=1)
#             all_detail.append(summary_header_list)
#             room_ids = room_obj.search([])
#             all_room_detail = []
#             for room in room_ids:
#                 room_detail = {}

#                 room_list_stats = []
#                 room_detail.update({'name': room.name or ''})
#                 if not room.room_reservation_line_ids and \
#                    not room.room_line_ids:
#                     for chk_date in date_range_list:
#                         room_list_stats.append({'state': 'Free',
#                                                 'date': chk_date,
#                                                 'room_id': room.id})
#                 else:
#                     for chk_date in date_range_list:
#                         ch_dt = chk_date[:10] + ' 23:59:59'
#                         ttime = datetime.strptime(ch_dt, dt)
#                         c = ttime.replace(tzinfo=timezone).\
#                             astimezone(pytz.timezone('UTC'))
#                         chk_date = c.strftime(dt)
#                          # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 start #1


#                         reserline_ids = room.room_reservation_line_ids.ids

#                         reservline_ids = (hotel_folio_line_obj.search
#                                           ([('product_id', 'in', room.product_id.ids),
#                                             ('checkin_date', '<=', chk_date),
#                                             ('checkout_date', '>=', chk_date),
#                                             ('state', 'in', ['sale', 'done']),
#                                             # ('status', '=', 'done')
#                                             ]))

#                         draft_folio_ids = (hotel_folio_line_obj.search
#                                           ([('product_id', 'in', room.product_id.ids),
#                                             ('checkin_date', '<=', chk_date),
#                                             ('checkout_date', '>=', chk_date),
#                                             ('state', '=', 'draft'),
#                                             # ('status', '=', 'done')
#                                             ]))

#                         reservline_new_ids = (reservation_line_obj.search
#                                           ([('id', 'in', reserline_ids),
#                                             ('check_in', '<=', chk_date),
#                                             ('check_out', '>=', chk_date),
#                                             ('state', '=', 'assigned'),
#                                             ('status', '=', 'confirm')
#                                             ]))

#                         occupied_ids = room.room_line_ids.ids
#                         folio_occupied_ids = (folio_room_line_obj.search
#                                           ([('id', 'in', occupied_ids),
#                                             ('check_in', '<=', chk_date),
#                                             ('check_out', '>=', chk_date),
#                                             ('status', '=',['sale', 'done'])
#                                             ]))

#                         folio_occupy_ids = (folio_room_line_obj.search
#                                               ([('id', 'in', occupied_ids),
#                                                 ('check_in', '<=', chk_date),
#                                                 ('check_out', '>=', chk_date),
#                                                 ('status', 'in', ['draft'])
#                                                 ]))

# #                         if not reservline_ids and not reservline_new_ids:
# #                             # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 end #
# #                         # if not reservline_ids and not reservline_new_ids:
# #                         # reservline_ids = (reservation_line_obj.search
# #                         #                   ([('id', 'in', reserline_ids),
# #                         #                     ('check_in', '<=', chk_date),
# #                         #                     ('check_out', '>=', chk_date),
# #                         #                     ('state', '=', 'assigned')
# #                         #                     ]))
# #                         # if not reservline_ids:
# #                             sdt = dt
# #                             chk_date = datetime.strptime(chk_date, sdt)
# #                             chk_date = datetime.\
# #                                 strftime(chk_date - timedelta(days=1), sdt)
# #                             reservline_ids = (reservation_line_obj.search
# #                                               ([('id', 'in', reserline_ids),
# #                                                 ('check_in', '<=', chk_date),
# #                                                 ('check_out', '>=', chk_date),
# #                                                 ('state', '=', 'assigned')]))
# #                             for res_room in reservline_ids:
# #                                 rrci = res_room.check_in
# #                                 rrco = res_room.check_out
# #                                 cid = datetime.strptime(rrci, dt)
# #                                 cod = datetime.strptime(rrco, dt)
# #                                 dur = cod - cid
# #                                 if room_list_stats:
# #                                     count = 0
# #                                     for rlist in room_list_stats:
# #                                         cidst = datetime.strftime(cid, dt)
# #                                         codst = datetime.strftime(cod, dt)
# #                                         rm_id = res_room.room_id.id
# #                                         ci = rlist.get('date') >= cidst
# #                                         co = rlist.get('date') <= codst
# #                                         rm = rlist.get('room_id') == rm_id
# #                                         st = rlist.get('state') == 'Reserved'
# #                                         if ci and co and rm and st:
# #                                             count += 1
# #                                     if count - dur.days == 0:
# #                                         c_id1 = user_obj.browse(self._uid)
# #                                         c_id = c_id1.company_id
# #                                         con_add = 0
# #                                         amin = 0.0
# #                                         if c_id:
# #                                             con_add = c_id.additional_hours
# # #                                        When configured_addition_hours is
# # #                                        greater than zero then we calculate
# # #                                        additional minutes
# #                                         if con_add > 0:
# #                                             amin = abs(con_add * 60)
# #                                         hr_dur = abs((dur.seconds / 60))
# # #                                        When additional minutes is greater
# # #                                        than zero then check duration with
# # #                                        extra minutes and give the room
# # #                                        reservation status is reserved or
# # #                                        free
# #                                         if amin > 0:
# #                                             if hr_dur >= amin:
# #                                                 reservline_ids = True
# #                                             else:
# #                                                 reservline_ids = False
# #                                         else:
# #                                             if hr_dur > 0:
# #                                                 reservline_ids = True
# #                                             else:
# #                                                 reservline_ids = False
# #                                     else:
# #                                         reservline_ids = False
#                         fol_room_line_ids = room.room_line_ids.ids
#                         chk_state = ['draft', 'cancel']
#                         folio_resrv_ids = (folio_room_line_obj.search
#                                            ([('id', 'in', fol_room_line_ids),
#                                              ('check_in', '<=', chk_date),
#                                              ('check_out', '>=', chk_date),
#                                              ('status', 'not in', chk_state)
#                                              ]))
#                         # if reservline_ids or folio_resrv_ids:
#                             # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 start #2

#                         if folio_occupy_ids or draft_folio_ids:
#                             room_list_stats.append({'state': 'Check In',
#                                                     'date': chk_date,
#                                                     'room_id': room.id,
#                                                     'is_draft': 'No',
#                                                     'data_model': '',
#                                                     'data_id': 0})
#                         elif reservline_new_ids:
#                             room_list_stats.append({'state': 'Reserved',
#                                                     'date': chk_date,
#                                                     'room_id': room.id,
#                                                     'is_draft': 'No',
#                                                     'data_model': '',
#                                                     'data_id': 0})
#                         # elif reservline_ids or folio_resrv_ids:
#                         elif reservline_ids or folio_occupied_ids:
#                             room_list_stats.append({'state': 'Check Out',
#                                                     'date': chk_date,
#                                                     'room_id': room.id,
#                                                     'is_draft': 'No',
#                                                     'data_model': '',
#                                                     'data_id': 0})

#                             # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 end #1
#                             # room_list_stats.append({'state': 'Reserved',
#                             #                         'date': chk_date,
#                             #                         'room_id': room.id,
#                             #                         'is_draft': 'No',
#                             #                         'data_model': '',
#                             #                         'data_id': 0})
#                         else:
#                             room_list_stats.append({'state': 'Free',
#                                                     'date': chk_date,
#                                                     'room_id': room.id})

#                 room_detail.update({'value': room_list_stats})
#                 all_room_detail.append(room_detail)
#             main_header.append({'header': summary_header_list})
#             self.summary_header = str(main_header)
#             self.room_summary = str(all_room_detail)
#         return res

    @api.onchange('date_from', 'date_to')
    def get_room_summary(self):
        '''
        @param self: object pointer
         '''
        res = {}
        all_detail = []
        room_obj = self.env['hotel.room']
        reservation_line_obj = self.env['hotel.room.reservation.line']
        folio_room_line_obj = self.env['folio.room.line']
        hotel_folio_line_obj = self.env['hotel.folio.line']
        user_obj = self.env['res.users']
        date_range_list = []
        main_header = []
        summary_header_list = ['Rooms']
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise except_orm(_('User Error!'),
                                 _('Please Check Time period Date \
                                 From can\'t be greater than Date To !'))
            if self._context.get('tz', False):
                timezone = pytz.timezone(self._context.get('tz', False))
            else:
                timezone = pytz.timezone('UTC')
            d_frm_obj = datetime.strptime(self.date_from, dt)\
                .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            d_to_obj = datetime.strptime(self.date_to, dt)\
                .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            temp_date = d_frm_obj
            while(temp_date <= d_to_obj):
                val = ''
                val = (str(temp_date.strftime("%a")) + ' ' +
                       str(temp_date.strftime("%b")) + ' ' +
                       str(temp_date.strftime("%d")))
                summary_header_list.append(val)
                date_range_list.append(temp_date.strftime
                                       (dt))
                temp_date = temp_date + timedelta(days=1)
            all_detail.append(summary_header_list)
            room_ids = room_obj.search([])
            all_room_detail = []
            for room in room_ids:
                room_detail = {}

                room_list_stats = []
                room_detail.update({'name': room.name or ''})
                if not room.room_reservation_line_ids and \
                   not room.room_line_ids:
                    for chk_date in date_range_list:
                        room_list_stats.append({'state': 'Free',
                                                'date': chk_date,
                                                'room_id': room.id})
                else:
                    for chk_date in date_range_list:
                        ch_dt = chk_date[:10] + ' 23:59:59'
                        ttime = datetime.strptime(ch_dt, dt)
                        c = ttime.replace(tzinfo=timezone).\
                            astimezone(pytz.timezone('UTC'))
                        chk_date = c.strftime(dt)
                         # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 start #1


                        reserline_ids = room.room_reservation_line_ids.ids

                        reservline_ids = (hotel_folio_line_obj.search
                                          ([('product_id', 'in', room.product_id.ids),
                                            ('checkin_date', '<=', chk_date),
                                            ('checkout_date', '>=', chk_date),
                                            ('state', 'in', ['sale', 'done']),
                                            # ('status', '=', 'done')
                                            ]))

                        draft_folio_ids = (hotel_folio_line_obj.search
                                          ([('product_id', 'in', room.product_id.ids),
                                            ('checkin_date', '<=', chk_date),
                                            ('checkout_date', '>=', chk_date),
                                            ('state', '=', 'draft'),
                                            # ('status', '=', 'done')
                                            ]))

                        reservline_new_ids = (reservation_line_obj.search
                                          ([('id', 'in', reserline_ids),
                                            ('check_in', '<=', chk_date),
                                            ('check_out', '>=', chk_date),
                                            ('state', '=', 'assigned'),
                                            ('status', '=', 'confirm')
                                            ]))

                        occupied_ids = room.room_line_ids.ids
                        folio_occupied_ids = (folio_room_line_obj.search
                                          ([('id', 'in', occupied_ids),
                                            ('check_in', '<=', chk_date),
                                            ('check_out', '>=', chk_date),
                                            ('status', '=',['sale', 'done'])
                                            ]))

                        folio_occupy_ids = (folio_room_line_obj.search
                                              ([('id', 'in', occupied_ids),
                                                ('check_in', '<=', chk_date),
                                                ('check_out', '>=', chk_date),
                                                ('status', 'in', ['draft'])
                                                ]))

#                         if not reservline_ids and not reservline_new_ids:
#                             # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 end #
#                         # if not reservline_ids and not reservline_new_ids:
#                         # reservline_ids = (reservation_line_obj.search
#                         #                   ([('id', 'in', reserline_ids),
#                         #                     ('check_in', '<=', chk_date),
#                         #                     ('check_out', '>=', chk_date),
#                         #                     ('state', '=', 'assigned')
#                         #                     ]))
#                         # if not reservline_ids:
#                             sdt = dt
#                             chk_date = datetime.strptime(chk_date, sdt)
#                             chk_date = datetime.\
#                                 strftime(chk_date - timedelta(days=1), sdt)
#                             reservline_ids = (reservation_line_obj.search
#                                               ([('id', 'in', reserline_ids),
#                                                 ('check_in', '<=', chk_date),
#                                                 ('check_out', '>=', chk_date),
#                                                 ('state', '=', 'assigned')]))
#                             for res_room in reservline_ids:
#                                 rrci = res_room.check_in
#                                 rrco = res_room.check_out
#                                 cid = datetime.strptime(rrci, dt)
#                                 cod = datetime.strptime(rrco, dt)
#                                 dur = cod - cid
#                                 if room_list_stats:
#                                     count = 0
#                                     for rlist in room_list_stats:
#                                         cidst = datetime.strftime(cid, dt)
#                                         codst = datetime.strftime(cod, dt)
#                                         rm_id = res_room.room_id.id
#                                         ci = rlist.get('date') >= cidst
#                                         co = rlist.get('date') <= codst
#                                         rm = rlist.get('room_id') == rm_id
#                                         st = rlist.get('state') == 'Reserved'
#                                         if ci and co and rm and st:
#                                             count += 1
#                                     if count - dur.days == 0:
#                                         c_id1 = user_obj.browse(self._uid)
#                                         c_id = c_id1.company_id
#                                         con_add = 0
#                                         amin = 0.0
#                                         if c_id:
#                                             con_add = c_id.additional_hours
# #                                        When configured_addition_hours is
# #                                        greater than zero then we calculate
# #                                        additional minutes
#                                         if con_add > 0:
#                                             amin = abs(con_add * 60)
#                                         hr_dur = abs((dur.seconds / 60))
# #                                        When additional minutes is greater
# #                                        than zero then check duration with
# #                                        extra minutes and give the room
# #                                        reservation status is reserved or
# #                                        free
#                                         if amin > 0:
#                                             if hr_dur >= amin:
#                                                 reservline_ids = True
#                                             else:
#                                                 reservline_ids = False
#                                         else:
#                                             if hr_dur > 0:
#                                                 reservline_ids = True
#                                             else:
#                                                 reservline_ids = False
#                                     else:
#                                         reservline_ids = False
                        fol_room_line_ids = room.room_line_ids.ids
                        chk_state = ['draft', 'cancel']
                        folio_resrv_ids = (folio_room_line_obj.search
                                           ([('id', 'in', fol_room_line_ids),
                                             ('check_in', '<=', chk_date),
                                             ('check_out', '>=', chk_date),
                                             ('status', 'not in', chk_state)
                                             ]))
                        # if reservline_ids or folio_resrv_ids:
                            # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 start #2

                        if folio_occupy_ids or draft_folio_ids:
                            room_list_stats.append({'state': 'Check In',
                                                    'date': chk_date,
                                                    'room_id': room.id,
                                                    'is_draft': 'No',
                                                    'data_model': '',
                                                    'data_id': 0})
                        elif reservline_new_ids:
                            room_list_stats.append({'state': 'Reserved',
                                                    'date': chk_date,
                                                    'room_id': room.id,
                                                    'is_draft': 'No',
                                                    'data_model': '',
                                                    'data_id': 0})
                        # elif reservline_ids or folio_resrv_ids:
                        elif reservline_ids or folio_occupied_ids:
                            room_list_stats.append({'state': 'Check Out',
                                                    'date': chk_date,
                                                    'room_id': room.id,
                                                    'is_draft': 'No',
                                                    'data_model': '',
                                                    'data_id': 0})

                            # Change for add Occupied room id for folio confirmed states thantshweaung 20181029 end #1
                            # room_list_stats.append({'state': 'Reserved',
                            #                         'date': chk_date,
                            #                         'room_id': room.id,
                            #                         'is_draft': 'No',
                            #                         'data_model': '',
                            #                         'data_id': 0})
                        else:
                            room_list_stats.append({'state': 'Free',
                                                    'date': chk_date,
                                                    'room_id': room.id})

                room_detail.update({'value': room_list_stats})
                all_room_detail.append(room_detail)
            main_header.append({'header': summary_header_list})
            self.summary_header = str(main_header)
            self.room_summary = str(all_room_detail)
        return res



class QuickRoomReservation(models.TransientModel):
    _name = 'quick.room.reservation'
    _description = 'Quick Room Reservation'

    @api.model
    def _get_currency(self):
        comp_obj = self.env['res.company']
        currency_obj =self.env['res.currency']
        thb_curr_id = currency_obj.search([('name','=','THB')]).id
        mmk_curr_id = currency_obj.search([('name','=','MMK')]).id
        usd_curr_id = currency_obj.search([('name','=','USD')]).id
        print thb_curr_id, mmk_curr_id, usd_curr_id
        if thb_curr_id or mmk_curr_id or usd_curr_id:
            cur_id = comp_obj.search([('currency_id','in',(thb_curr_id, mmk_curr_id ,usd_curr_id))])
            print cur_id,"Curr"
            return cur_id.currency_id.id

    partner_id = fields.Many2one('res.partner', string="Customer",
                                 required=True)
    check_in = fields.Datetime('Check In', required=True)
    check_out = fields.Datetime('Check Out', required=True)
    room_id = fields.Many2one('hotel.room', 'Room', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Hotel', required=True)
    pricelist_id = fields.Many2one('product.pricelist', 'pricelist')
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address')
    partner_order_id = fields.Many2one('res.partner', 'Ordering Contact',
                                       required=True)
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address',
                                          required=True)
    adults = fields.Integer('Adults', size=64)
    quick_reservation = fields.Boolean("Quick",default=True)
    currency_id = fields.Many2one("res.currency",default=_get_currency,string="Currency",store=True)
    agency = fields.Many2one("res.partner",domain="[('agency','=',True)]",string="Agency",store=True)

    @api.onchange('check_out', 'check_in')
    def on_change_check_out(self):
        '''
        When you change checkout or checkin it will check whether
        Checkout date should be greater than Checkin date
        and update dummy field
        -----------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        if self.check_out and self.check_in:
            if self.check_out < self.check_in:
                raise except_orm(_('Warning'),
                                 _('Checkout date should be greater \
                                 than Checkin date.'))

    @api.onchange('partner_id')
    def onchange_partner_id_res(self):
        '''
        When you change partner_id it will update the partner_invoice_id,
        partner_shipping_id and pricelist_id of the hotel reservation as well
        ---------------------------------------------------------------------
        @param self: object pointer
        '''
        if not self.partner_id:
            self.partner_invoice_id = False
            self.partner_shipping_id = False
            self.partner_order_id = False
        else:
            addr = self.partner_id.address_get(['delivery', 'invoice',
                                                'contact'])
            self.partner_invoice_id = addr['invoice']
            self.partner_order_id = addr['contact']
            self.partner_shipping_id = addr['delivery']
            self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.model
    def default_get(self, fields):
        """
        To get default values for the object.
        @param self: The object pointer.
        @param fields: List of fields for which we want default values
        @return: A dictionary which of fields with values.
        """
        if self._context is None:
            self._context = {}
        res = super(QuickRoomReservation, self).default_get(fields)
        if self._context:
            keys = self._context.keys()
            if 'date' in keys:
                res.update({'check_in': self._context['date']})
            if 'room_id' in keys:
                roomid = self._context['room_id']
                res.update({'room_id': int(roomid)})
        return res

    @api.multi
    def room_reserve(self):
        """
        This method create a new record for hotel.reservation
        -----------------------------------------------------
        @param self: The object pointer
        @return: new record set for hotel reservation.
        """
        hotel_res_obj = self.env['hotel.reservation']
        for res in self:
            rec = (hotel_res_obj.create
                   ({'partner_id': res.partner_id.id,
                     'partner_invoice_id': res.partner_invoice_id.id,
                     'partner_order_id': res.partner_order_id.id,
                     'partner_shipping_id': res.partner_shipping_id.id,
                     'checkin': res.check_in,
                     'checkout': res.check_out,
                     'warehouse_id': res.warehouse_id.id,
                     'pricelist_id': res.pricelist_id.id,
                     'currency_id': res.currency_id.id,
                     'agency': res.agency.id,
                     'type_payment':res.type_payment.id,
                     'adults': res.adults,
                     'reservation_line': [(0, 0,
                                           {'reserve': [(6, 0,
                                                         [res.room_id.id])],
                                            'name': (res.room_id and
                                                     res.room_id.name or '')
                                            })]
                     }))
        return rec
