import time
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HotelFolio(models.Model):
    _inherit = 'hotel.folio'

    laundry_id = fields.One2many('laundry.order', 'folio_id', string='Laundry Order')


class LaundryManagement(models.Model):
    _name = 'laundry.order'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Laundry Order"
    _order = 'order_date desc, id desc'

    #2018 10 30, thureinsoe, get filter for room
    @api.multi
    def get_rooms(self):
        room = []
        domain = None
        folio_ids = self.env['hotel.folio'].search([('state','=','draft')])
        if folio_ids:
            for folio in folio_ids:
                for rm in folio.room_lines:
                    room.append(rm.product_id.id)
        domain = "[('id','in',"+str(room)+")]"
        return domain

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('laundry.order')
        return super(LaundryManagement, self).create(vals)

    @api.multi
    @api.depends('order_lines')
    def get_total(self):
        total = 0
        for obj in self:
            for each in obj.order_lines:
                total += each.amount
            obj.total_amount = total

    @api.multi
    def confirm_order(self):
        self.state = 'order'
        print self.partner_id.id,
        print self.partner_invoice_id.id,"partner"
        sale_obj = self.env['sale.order'].create({'partner_id': self.partner_id.id,
                                                  'partner_invoice_id': self.partner_invoice_id.id,
                                                  'partner_shipping_id': self.partner_shipping_id.id})
        self.sale_obj = sale_obj
        product_id = self.env.ref('laundry_management.laundry_service')
        self.env['sale.order.line'].create({'product_id': product_id.id,
                                            'name': 'Laundry Service',
                                            'price_unit': self.total_amount,
                                            'order_id': sale_obj.id
                                            })
        for each in self:
            for obj in each.order_lines:
                self.env['washing.washing'].create({'name': obj.product_id.name + '-Washing',
                                                    'user_id': obj.washing_type.assigned_person.id,
                                                    'description': obj.description,
                                                    'laundry_obj': obj.id,
                                                    'state': 'draft',
                                                    'washing_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

    @api.multi
    def create_invoice(self):
        if self.sale_obj.state in ['draft', 'sent']:
            self.sale_obj.action_confirm()
        # self.state = 'invoice'
        self.invoice_status = self.sale_obj.invoice_status
        vals={
            'name': 'Create Invoice',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.advance.payment.inv',
            'type': 'ir.actions.act_window',
            'context': {'laundry_sale_obj': self.sale_obj.id,'active_id': self.id},
            'target': 'new'
        }
        res = self.env['sale.advance.payment.inv'].create(vals)
        res.create_invoices_laundry()
        return res

    # @api.multi
    # def _create_invoice_laundry(self):
    #     if 
    # @api.onchange('partner_id')
    # def onchange_partner_id(self):
    #     '''
    #     When you change partner_id it will update the partner_invoice_id,
    #     partner_shipping_id and pricelist_id of the hotel folio as well
    #     ---------------------------------------------------------------
    #     @param self: object pointer
    #     '''
    #     if self.partner_id:
    #         partner_rec = self.env['res.partner'].browse(self.partner_id.id)
    #         order_ids = [laundry.order_obj.id for laundry in self]
    #         if not order_ids:
    #             self.partner_invoice_id = partner_rec.id
    #             self.partner_shipping_id = partner_rec.id
    #             self.pricelist_id = partner_rec.property_product_pricelist.id
    #             raise _('Not Any Order For  %s ' % (partner_rec.name))
    #         else:
    #             self.partner_invoice_id = partner_rec.id
    #             self.partner_shipping_id = partner_rec.id
    #             self.pricelist_id = partner_rec.property_product_pricelist.id

    @api.multi
    def return_dress(self):
        self.state = 'return'

    @api.multi
    def cancel_order(self):
        self.state = 'cancel'

    @api.multi
    def _invoice_count(self):
        wrk_ordr_ids = self.env['account.invoice'].search([('origin', '=', self.sale_obj.name)])
        print len(wrk_ordr_ids)
        self.invoice_count = len(wrk_ordr_ids)

    @api.multi
    def _work_count(self):
        wrk_ordr_ids = self.env['washing.washing'].search([('laundry_obj.laundry_obj.id', '=', self.id)])
        print len(wrk_ordr_ids)
        self.work_count = len(wrk_ordr_ids)

    @api.multi
    def action_view_laundry_works(self):
        work_obj = self.env['washing.washing'].search([('laundry_obj.laundry_obj.id', '=', self.id)])
        work_ids = []
        for each in work_obj:
            work_ids.append(each.id)
        view_id = self.env.ref('laundry_management.washing_form_view').id
        if work_ids:
            if len(work_ids) <= 1:
                value = {
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'washing.washing',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name': _('Works'),
                    'res_id': work_ids and work_ids[0]
                }
            else:
                value = {
                    'domain': str([('id', 'in', work_ids)]),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'washing.washing',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name': _('Works'),
                    'res_id': work_ids
                }

            return value

    @api.multi
    def action_view_invoice(self):
        inv_obj = self.env['account.invoice'].search([('origin', '=', self.sale_obj.name)])
        inv_ids = []
        for each in inv_obj:
            inv_ids.append(each.id)
        view_id = self.env.ref('account.invoice_form').id
        if inv_ids:
            if len(inv_ids) <= 1:
                value = {
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name': _('Invoice'),
                    'res_id': inv_ids and inv_ids[0]
                }
            else:
                value = {
                    'domain': str([('id', 'in', inv_ids)]),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'account.invoice',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name': _('Invoice'),
                    'res_id': inv_ids
                }

            return value

    name = fields.Char(string="Label", copy=False)
    invoice_status = fields.Selection([
        ('upselling', 'Upselling Opportunity'),
        ('invoiced', 'Fully Invoiced'),
        ('to invoice', 'To Invoice'),
        ('no', 'Nothing to Invoice')
    ], string='Invoice Status', invisible=1, related='sale_obj.invoice_status', store=True)
    sale_obj = fields.Many2one('sale.order', invisible=1)
    invoice_count = fields.Integer(compute='_invoice_count', string='# Invoice')
    work_count = fields.Integer(compute='_work_count', string='# Works')
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True,
                                 states={'draft': [('readonly', False)], 'order': [('readonly', False)]}, required=True,
                                 change_default=True, index=True, track_visibility='always')
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True,
                                         states={'draft': [('readonly', False)], 'order': [('readonly', False)]},
                                         help="Invoice address for current sales order.")
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True,
                                          states={'draft': [('readonly', False)], 'order': [('readonly', False)]},
                                          help="Delivery address for current sales order.")
    order_date = fields.Datetime(string="Date", default=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    laundry_person = fields.Many2one('res.users', string='Laundry Person', required=1)
    order_lines = fields.One2many('laundry.order.line', 'laundry_obj', required=1, ondelete='cascade')
    total_amount = fields.Float(compute='get_total', string='Total', store=1)
    currency_id = fields.Many2one("res.currency", string="Currency", default=lambda self: self.env.user.company_id.currency_id.id)          #2018 10 30, thureinsoe,get default currency from company
    note = fields.Text(string='Terms and conditions')
    room_id = fields.Many2one('product.product',string= "Room No",domain=get_rooms, store=True)     #2018 10 30, thureinsoe, get filter for room
    state = fields.Selection([
        ('draft', 'Draft'),
        ('order', 'Laundry Order'),
        ('process', 'Processing'),
        ('done', 'Done'),
        ('return', 'Returned'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    folio_id = fields.Many2one('hotel.folio', string='Folio')           #2018 10 30, thureinsoe,get folio id from room selection
    # is_laundry = fields.Boolean("Laundry",default=True,store=True)
    #2018 10 30, thureinsoe,get folio id from room selection
    @api.onchange('room_id')
    def get_folio_form_room(self):
        value = []
        if self.room_id:
            folio_line_ids = self.env['hotel.folio.line'].search([('product_id','=',self.room_id.id)])
            for folio in folio_line_ids:
                if folio.folio_id.state == 'draft':
                    value.append(folio.folio_id.id)
            folio_ids = self.env['hotel.folio'].search([('id','=',value[0])])
            self.folio_id = value[0]
            self.partner_id = folio_ids.partner_id

    #2018 10 30, thureinsoe,currency onchange
    @api.onchange('currency_id')
    def on_change_currency(self):
        if not self.currency_id:
            return None
        for line in self.order_lines:
            laundry_ids = self.env['hotel.laundry'].search([('product_id','=',line.product_id.id)])
            payment_ids = self.env['payment.type'].search([('currency','=',self.currency_id.id),('laundry_charges','=',laundry_ids.id)])
            if payment_ids:
                line.price = payment_ids.price



class LaundryManagementLine(models.Model):
    _name = 'laundry.order.line'

    @api.depends('washing_type', 'extra_work', 'qty','price')
    def get_amount(self):
        for obj in self:
            total = obj.washing_type.amount*obj.qty
            for each in obj.extra_work:
                total += each.amount*obj.qty
            obj.amount = total +(obj.qty*obj.price)

    laundry = fields.Many2one('hotel.laundry.function',store=True)
    product_id = fields.Many2one('product.product', string='Dress',domain="[('islaundry','=',True),('laundry_ttt','=',laundry)]",store=True)
    qty = fields.Integer(string='No of items', required=True)
    description = fields.Text(string='Description')
    washing_type = fields.Many2one('washing.type', string='Washing Type', required=True)
    extra_work = fields.Many2many('washing.work', string='Extra Work',store=True)
    price = fields.Float('Unit Price',store=True)
    amount = fields.Float(compute='get_amount', string='Amount')
    laundry_obj = fields.Many2one('laundry.order', invisible=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('wash', 'Washing'),
        ('extra_work', 'Make Over'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, default='draft')

    @api.onchange('product_id')
    def product_id_change(self):
        if self.product_id:
            laundry_ids = self.env['hotel.laundry'].search([('product_id','=',self.product_id.id)])
            payment_ids = self.env['payment.type'].search([('currency','=',self.laundry_obj.currency_id.id),('laundry_charges','=',laundry_ids.id)])
            self.price = payment_ids.price
            #self.laundry = self.product_id.laundry_ttt



class WashingType(models.Model):
    _name = 'washing.type'

    name = fields.Char(string='Name', required=1)
    assigned_person = fields.Many2one('res.users', string='Assigned Person', required=1)
    amount = fields.Float(string='Service Charge', required=1)


class ExtraWork(models.Model):
    _name = 'washing.work'

    name = fields.Char(string='Name', required=1)
    assigned_person = fields.Many2one('res.users', string='Assigned Person', required=1)
    amount = fields.Float(string='Service Charge', required=1)


class Washing(models.Model):
    _name = 'washing.washing'

    @api.multi
    def start_wash(self):
        if not self.laundry_works:
            self.laundry_obj.state = 'wash'
            self.laundry_obj.laundry_obj.state = 'process'
        for each in self:
            for obj in each.product_line:
                self.env['sale.order.line'].create({'product_id': obj.product_id.id,
                                                    'name': obj.name,
                                                    'price_unit': obj.price_unit,
                                                    'order_id': each.laundry_obj.laundry_obj.sale_obj.id,
                                                    'product_uom_qty': obj.quantity,
                                                    'product_uom': obj.uom_id.id,
                                                    })
        self.state = 'process'

    @api.multi
    def set_to_done(self):
        self.state = 'done'
        f = 0
        if not self.laundry_works:
            if self.laundry_obj.extra_work:
                for each in self.laundry_obj.extra_work:
                    self.create({'name': each.name,
                                 'user_id': each.assigned_person.id,
                                 'description': self.laundry_obj.description,
                                 'laundry_obj': self.laundry_obj.id,
                                 'state': 'draft',
                                 'laundry_works': True,
                                 'washing_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                self.laundry_obj.state = 'extra_work'
        laundry_obj = self.search([('laundry_obj.laundry_obj', '=', self.laundry_obj.laundry_obj.id)])
        for each in laundry_obj:
            if each.state != 'done' or each.state == 'cancel':
                f = 1
                break
        if f == 0:
            self.laundry_obj.laundry_obj.state = 'done'
        laundry_obj1 = self.search([('laundry_obj', '=', self.laundry_obj.id)])
        f1 = 0
        for each in laundry_obj1:
            if each.state != 'done' or each.state == 'cancel':
                f1 = 1
                break
        if f1 == 0:
            self.laundry_obj.state = 'done'

    @api.multi
    @api.depends('product_line')
    def get_total(self):
        total = 0
        for obj in self:
            for each in obj.product_line:
                total += each.subtotal
            obj.total_amount = total

    name = fields.Char(string='Work')
    laundry_works = fields.Boolean(default=False, invisible=1)
    user_id = fields.Many2one('res.users', string='Assigned Person')
    washing_date = fields.Datetime(string='Date')
    description = fields.Text(string='Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('process', 'Process'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, default='draft')
    laundry_obj = fields.Many2one('laundry.order.line', invisible=1)
    product_line = fields.One2many('wash.order.line', 'wash_obj', string='Products', ondelete='cascade')
    total_amount = fields.Float(compute='get_total', string='Grand Total')


class SaleOrderInherit(models.Model):
    _name = 'wash.order.line'

    @api.depends('price_unit', 'quantity')
    def compute_amount(self):
        total = 0
        for obj in self:
            total += obj.price_unit * obj.quantity
        obj.subtotal = total

    wash_obj = fields.Many2one('washing.washing', string='Order Reference', ondelete='cascade')
    name = fields.Text(string='Description', required=True)
    uom_id = fields.Many2one('product.uom', 'Unit of Measure ', required=True)
    quantity = fields.Integer(string='Quantity')
    product_id = fields.Many2one('product.product', string='Product')
    price_unit = fields.Float('Unit Price', default=0.0, related='product_id.list_price')
    subtotal = fields.Float(compute='compute_amount', string='Subtotal', readonly=True, store=True)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_invoice_create_laundry(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
         """
        # add currency for invoice from folio currency by aungmyoswe 20180930
        laundry_obj = self.env['laundry.order']
        print "hello9",self
        sale_line_obj = self.env['sale.order.line']
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = {}
        references = {}
        for order in self:
            currency_ids = laundry_obj.search([('sale_obj','=',order.id)])
            currency_id = currency_ids.currency.id
            print currency_id,"curenchy"
            group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)
            sale_order_ids = sale_line_obj.search([('order_id','=',order.id),('is_check','=',False)])
            for line in sale_order_ids.sorted(key=lambda l: l.qty_to_invoice < 0):
                if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                if group_key not in invoices:
                  inv_data = order._prepare_invoice()
                  inv_data['currency_id']=currency_id
                  invoice = inv_obj.create(inv_data)
                  references[invoice] = order
                  invoices[group_key] = invoice
                elif group_key in invoices:
                  vals = {}
                  if order.name not in invoices[group_key].origin.split(', '):
                      vals['origin'] = invoices[group_key].origin + ', ' + order.name
                  if order.client_order_ref and order.client_order_ref not in invoices[group_key].name.split(', '):
                      vals['name'] = invoices[group_key].name + ', ' + order.client_order_ref
                  invoices[group_key].write(vals)
                if line.qty_to_invoice > 0:
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
                elif line.qty_to_invoice < 0 and final:  
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
            if references.get(invoices.get(group_key)):
                if order not in references[invoices[group_key]]:
                    references[invoice] = references[invoice] | order
        if not invoices:
            raise UserError(_('There is no invoicable line.'))
        for invoice in invoices.values():
            if not invoice.invoice_line_ids:
                raise UserError(_('There is no invoicable line.'))
            # If invoice is negative, do a refund invoice instead
            if invoice.amount_untaxed < 0:
                invoice.type = 'out_refund'
                for line in invoice.invoice_line_ids:
                    line.quantity = -line.quantity
            # Use additional field helper function (for account extensions)
            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)
            # Necessary to force computation of taxes. In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()
            invoice.message_post_with_view('mail.message_origin_link',
                values={'self': invoice, 'origin': references[invoice]},
                subtype_id=self.env.ref('mail.mt_note').id)
        return [inv.id for inv in invoices.values()]
        
class LaundryManagementInvoice(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    @api.multi
    def create_invoices_laundry(self):
        res = None
        ctx = self.env.context.copy()
        print self._context
        print "ctx",self._context.get('current_id')
        action = self._context.get('params').get('action')
        # active_id = self._context.get('action').get('res_model')
        # print active_id,"active_id"
        # print active_id,"id"
        # print action_id.model,"Model"
        print action_id,"Action"
        order_line = []
        sale_obj = self.env['sale.order']
        sale_line_obj = self.env['sale.order.line']
        laundry_obj=self.env['laundry.order']
        service_obj=self.env['hotel.service.line']
        sale_order_ids = None 
        sale_order_ids1 = None
        print 
        if action_id.model == 'laundry.order':
            laundry_orders = self.env['laundry.order']
            laundry = laundry_orders.browse(self._context.get('current_id'))
            print laundry,"Laundry"
            # context = self._context
            # if context.get('laundry_sale_obj'):
            #     sale_orders = self.env['sale.order'].browse(context.get('laundry_sale_obj'))
            # else:
            #     sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
            # print "sale",sale_orders
            # print ""
            for ldy in laundry.sale_obj:
                sale_orders = self.env['sale.order'].search([('id','=',ldy.sale_obj.id)]) 
                print sale_orders,"order"
            if self.advance_payment_method == 'delivered':
                sale_orders.action_invoice_create_laundry()
            elif self.advance_payment_method == 'all':
                sale_orders.action_invoice_create_laundry(final=True)
            else:
                # Create deposit product if necessary
                if not self.product_id:
                    vals = self._prepare_deposit_product()
                    self.product_id = self.env['product.product'].create(vals)
                    self.env['ir.values'].sudo().set_default('sale.config.settings', 'deposit_product_id_setting',
                                                             self.product_id.id)

                sale_line_obj = self.env['sale.order.line']
                for order in sale_orders:
                    if self.advance_payment_method == 'percentage':
                        amount = order.amount_untaxed * self.amount / 100
                    else:
                        amount = self.amount
                    if self.product_id.invoice_policy != 'order':
                        raise UserError(_(
                            'The product used to invoice a down payment should have an invoice policy set to "Ordered'
                            ' quantities". Please update your deposit product to be able to create a deposit invoice.'))
                    if self.product_id.type != 'service':
                        raise UserError(_(
                            "The product used to invoice a down payment should be of type 'Service'. Please use another "
                            "product or update this product."))
                    taxes = self.product_id.taxes_id.filtered(
                        lambda r: not order.company_id or r.company_id == order.company_id)
                    if order.fiscal_position_id and taxes:
                        tax_ids = order.fiscal_position_id.map_tax(taxes).ids
                    else:
                        tax_ids = taxes.ids
                    so_line = sale_line_obj.create({
                        'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                        'price_unit': amount,
                        'product_uom_qty': 0.0,
                        'order_id': order.id,
                        'discount': 0.0,
                        'product_uom': self.product_id.uom_id.id,
                        'product_id': self.product_id.id,
                        'tax_id': [(6, 0, tax_ids)],
                    })
                    self._create_invoice(order, so_line, amount)
            if self._context.get('open_invoices', False):
                return sale_orders.action_view_invoice()
            return {'type': 'ir.actions.act_window_close'}

    

    
class HotelLaundryFunction(models.Model):
    _name = "hotel.laundry.function"

    name = fields.Char('Name', size=64, required=True)
    laundry_id = fields.Many2one('hotel.laundry.function', 'Category')
    child_id = fields.One2many('hotel.laundry.function', 'laundry_id',
                               'Child Categories')
    