# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class SaleOrder(models.Model):
  _inherit = "sale.order"

  @api.multi
  def action_invoice_create(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        folio_obj = self.env['hotel.folio']
        laundry_obj = self.env['laundry.order']
        sale_order_obj = self.env['sale.order.line']
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = {}
        references = {}
        for order in self:
            print order,"Order"
            currency_ids = folio_obj.search([('order_id','=',order.id)])
            print currency_ids
            currency_id = currency_ids.currency.id
            # sale_currency_ids = laundry_obj.search([('id','=',order.id),('is_laundry','=',True)])
            # if currency_ids or sale_currency_ids.id:
            #   currency_id = currency_ids.currency.id or sale_order_ids.currency_id.id
            # print "currency_ids",currency_id
            # if currency_ids and sale_currency_ids.id:
            #   currency_id = currency_ids.curency.id
            print order.id or order.order_id,order.order_line,"order"
            group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)

            sale_order_ids = sale_order_obj.search([('order_id','=',order.id)])
            # for line in sale_order_ids.sorted(key=lambda l: l.qty_to_invoice < 0):
            for line in sale_order_ids:
            # for line in order.order_line.sorted(key=lambda l: l.qty_to_invoice < 0):
                print 'lien',line
                # if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                #     continue
                print 'group_key',group_key
                if group_key not in invoices:
                    inv_data = order._prepare_invoice()
                    inv_data['currency_id']=currency_id
                    print "INV->",inv_data
                    invoice = inv_obj.create(inv_data)
                    references[invoice] = order
                    invoices[group_key] = invoice
                elif group_key in invoices:
                    print "invocie",invoices
                    vals = {}
                    if order.name not in invoices[group_key].origin.split(', '):
                        vals['origin'] = invoices[group_key].origin + ', ' + order.name
                    if order.client_order_ref and order.client_order_ref not in invoices[group_key].name.split(', '):
                        vals['name'] = invoices[group_key].name + ', ' + order.client_order_ref
                    invoices[group_key].write(vals)
                print "hi",line.qty_to_invoice
                if line.qty_to_invoice > 0:
                    print "line",line
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
                elif line.qty_to_invoice < 0 and final:
                    print "line",line
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

  # @api.multi
  # def action_invoice_create_f(self, grouped=False, final=False):
  #       """
  #       Create the invoice associated to the SO.
  #       :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
  #                       (partner_invoice_id, currency)
  #       :param final: if True, refunds will be generated if necessary
  #       :returns: list of created invoices
  #       """
  #       print "hello"
  #       laundry_obj = self.env['laundry.order']
  #       inv_obj = self.env['account.invoice']
  #       precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
  #       invoices = {}
  #       references = {}
  #       for order in self:
  #           print order.id
  #           currency_ids = laundry_obj.search([('sale_obj','=',order.id)])
  #           currency_id = currency_ids.currency_id.id
  #           print currency_id,"currency"
  #           group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)
  #           for line in order.order_line.sorted(key=lambda l: l.qty_to_invoice < 0):
  #               # if float_is_zero(line.qty_to_invoice, precision_digits=precision):
  #               #     continue
  #               if group_key not in invoices:
  #                   inv_data = order._prepare_invoice()
  #                   inv_data['currency_id']=currency_id
  #                   invoice = inv_obj.create(inv_data)
  #                   references[invoice] = order
  #                   invoices[group_key] = invoice
  #               elif group_key in invoices:
  #                   vals = {}
  #                   if order.name not in invoices[group_key].origin.split(', '):
  #                       vals['origin'] = invoices[group_key].origin + ', ' + order.name
  #                   if order.client_order_ref and order.client_order_ref not in invoices[group_key].name.split(', '):
  #                       vals['name'] = invoices[group_key].name + ', ' + order.client_order_ref
  #                   invoices[group_key].write(vals)
  #               if line.qty_to_invoice > 0:
  #                   line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
  #               elif line.qty_to_invoice < 0 and final:
  #                   line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
  #           if references.get(invoices.get(group_key)):
  #               if order not in references[invoices[group_key]]:
  #                   references[invoice] = references[invoice] | order
  #       if not invoices:
  #           raise UserError(_('There is no invoicable line.'))

  #       for invoice in invoices.values():
  #           if not invoice.invoice_line_ids:
  #               raise UserError(_('There is no invoicable line.'))
  #           # If invoice is negative, do a refund invoice instead
  #           if invoice.amount_untaxed < 0:
  #               invoice.type = 'out_refund'
  #               for line in invoice.invoice_line_ids:
  #                   line.quantity = -line.quantity
  #           # Use additional field helper function (for account extensions)
  #           for line in invoice.invoice_line_ids:
  #               line._set_additional_fields(invoice)
  #           # Necessary to force computation of taxes. In account_invoice, they are triggered
  #           # by onchanges, which are not triggered when doing a create.
  #           invoice.compute_taxes()
  #           invoice.message_post_with_view('mail.message_origin_link',
  #               values={'self': invoice, 'origin': references[invoice]},
  #               subtype_id=self.env.ref('mail.mt_note').id)
  #       return [inv.id for inv in invoices.values()]



  @api.multi
  def action_view_invoice_1(self,val):
      print"taxxxxxxx"
      invoice_obj = self.env['account.invoice']
      invoice_ids = self.mapped('invoice_ids')
      inv = []
      for loop in invoice_ids:
        inv.append(loop.id)
      invoice = sorted(inv,reverse=True)[0]
      invoice_id =  invoice_obj.search([('id','=',invoice)])
      imd = self.env['ir.model.data']
      action = imd.xmlid_to_object('account.action_invoice_tree1')
      list_view_id = imd.xmlid_to_res_id('account.invoice_tree')
      form_view_id = imd.xmlid_to_res_id('account.invoice_form')
      result = {
          'name': action.name,
          'help': action.help,
          'type': action.type,
          'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'], [False, 'calendar'], [False, 'pivot']],
          'target': action.target,
          'context': action.context,
          'res_model': action.res_model,
      }
      if len([invoice_id.id]) > 1:
          result['domain'] = "[('id','in',%s)]" % invoice_ids.ids
      elif len([invoice_id.id]) == 1:
          result['views'] = [(form_view_id, 'form')]
          result['res_id'] = invoice_id.id
      else:
          result = {'type': 'ir.actions.act_window_close'}
      return result

  @api.multi
  def action_invoice_create_2(self, grouped=False, final=False):
      """
      Create the invoice associated to the SO.
      :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                      (partner_invoice_id, currency)
      :param final: if True, refunds will be generated if necessary
      :returns: list of created invoices
      """
      # add currency for invoice from folio currency by aungmyoswe 20180930
      folio_obj = self.env['hotel.folio']
      sale_order_obj = self.env['sale.order.line']
      inv_obj = self.env['account.invoice']
      precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
      invoices = {}
      references = {}
      for order in self:
          currency_ids = folio_obj.search([('order_id','=',order.id)])
          currency_id = currency_ids.currency.id
          group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)
          sale_order_ids = sale_order_obj.search([('order_id','=',order.id),('is_check','=',True)])
          # for line in sale_order_ids.sorted(key=lambda l: l.qty_to_invoice < 0):
          for line in sale_order_ids:
              if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                  continue
              if group_key not in invoices:
                  inv_data = order._prepare_invoice()
                  print currency_id,"currencyIi"
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
                  print line,"lllllllllll"
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


  @api.multi
  def action_invoice_create_3(self, grouped=False, final=False):
    """
    Create the invoice associated to the SO.
    :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                    (partner_invoice_id, currency)
    :param final: if True, refunds will be generated if necessary
    :returns: list of created invoices
     """
    # add currency for invoice from folio currency by aungmyoswe 20180930
    folio_obj = self.env['hotel.folio']
    print "hello9",self.id
    sale_line_obj = self.env['sale.order.line']
    inv_obj = self.env['account.invoice']
    precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    invoices = {}
    references = {}
    for order in self:
        currency_ids = folio_obj.search([('order_id','=',order.id)])
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



class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.model
    def _get_advance_payment(self):
        ctx = self.env.context.copy()
        if self._context.get('active_model') == 'hotel.folio':
            hotel_fol = self.env['hotel.folio']
            hotel = hotel_fol.browse(self._context.get('active_ids',
                                                       []))
            ctx.update({'active_ids': [hotel.order_id.id],
                        'active_id': hotel.order_id.id})
        return super(SaleAdvancePaymentInv,
                     self.with_context(ctx))._get_advance_payment_method()
    advance_payment_method = fields.Selection([('delivered',
                                                'Invoiceable lines'),
                                               ('all',
                                                'Invoiceable lines\
                                                (deduct down payments)'),
                                               ('percentage',
                                                'Down payment (percentage)'),
                                               ('fixed',
                                                'Down payment (fixed\
                                                amount)')],
                                              string='What do you want\
                                              to invoice?',
                                              default=_get_advance_payment,
                                              required=True)

    @api.multi
    def create_invoices(self):
        res = None
        ctx = self.env.context.copy()
        order_line = []
        sale_obj = self.env['sale.order']
        sale_line_obj = self.env['sale.order.line']
        folio_obj=self.env['hotel.folio']
        folio_line_obj=self.env['hotel.folio.line']
        service_obj=self.env['hotel.service.line']
        sale_order_ids = None 
        sale_order_ids1 = None
        print "he"
        if self._context.get('active_model') == 'hotel.folio':
            hotel_fol = self.env['hotel.folio']
            hotel = hotel_fol.browse(self._context.get('active_ids',
                                                       []))
            for order in hotel.order_id:
              sale_orders = self.env['sale.order'].browse(hotel.order_id.id)
              order_ids = sale_line_obj.search([('order_id','=',order.id),('state','=','sale'),('is_check','=',True)])
              if not order_ids:
                sale_order_ids1 = sale_line_obj.search([('order_id','=',order.id),('state','=','draft')])
                if hotel.state == 'draft' and hotel.uncheck == False:
                  for room in hotel.room_lines:
                      folio_line_ids = folio_line_obj.search([('id','=',room.id),('is_check','=',True)])
                      if folio_line_ids: 
                        for loop in folio_line_ids:
                          loop.state = 'sale'
                          loop.is_check = True
                          order_line_ids = sale_line_obj.search([('id','=',loop.order_line_id.id)])
                          for line in order_line_ids:
                            line.is_check=loop.is_check
                            line.state ='sale'
                  for service in hotel.service_lines:
                      service_line_ids = service_obj.search([('id','=',service.id),('is_check','=',True)])
                      if service_line_ids:
                          for loop in service_line_ids:
                              loop.state ='sale'
                              sale_order_ids = sale_line_obj.search([('id','=',loop.service_line_id.id)])
                              for line in sale_order_ids:
                                line.is_check = True
                                line.state = 'sale'
                  order.state = 'sale'
                  fo = folio_obj.browse(hotel.id)
                  res = fo._invoices()
                  for status in hotel.order_id:
                    status.state = 'draft'
                  line_status_id = sale_line_obj.search([('order_id','=',order.id),('is_check','=',True)])
                  if line_status_id:
                    for line_status in line_status_id:
                      line_status.state = 'sale'
                  if self._context.get('open_invoices', False):
                      res = sale_orders.action_view_invoice_1(res) 
                  return res
              if order_ids:
                sale_order_ids1 = sale_line_obj.search([('order_id','=',order.id),('state','=','draft')])
                if hotel.state == 'draft' and hotel.uncheck == False:
                  for room in hotel.room_lines:
                    folio_line_ids = folio_line_obj.search([('id','=',room.id),('is_check','=',True),('state','=','draft')])
                    if folio_line_ids: 
                      for loop in folio_line_ids:
                        loop.state = 'sale'
                        loop.is_check = True
                        order_line_ids = sale_line_obj.search([('id','=',loop.order_line_id.id)])
                        for line in order_line_ids:
                          line.is_check=loop.is_check
                          line.state ='sale'
                  for service in hotel.service_lines:
                      service_line_ids = service_obj.search([('id','=',service.id),('is_check','=',True),('state','=','draft')])
                      if service_line_ids:
                          for loop in service_line_ids:
                              loop.state ='sale'
                              sale_order_ids = sale_line_obj.search([('id','=',loop.service_line_id.id)])
                              for line in sale_order_ids:
                                line.is_check = True
                                line.state = 'sale'
                  order.state = 'sale'
                  fo = folio_obj.browse(hotel.id)
                  res = fo._invoices()
                  for status in hotel.order_id:
                    status.state = 'draft'
                  line_status_id = sale_line_obj.search([('order_id','=',order.id),('is_check','=',True),('state','=','draft')])
                  if line_status_id:
                    for line_status in line_status_id:
                      line_status.state = 'sale'
                  if self._context.get('open_invoices', False):
                      res = sale_orders.action_view_invoice_1(res)    
                  return res
              if hotel.uncheck == True and hotel.state == 'draft':
                for room in hotel.room_lines:
                  folio_line_ids = folio_line_obj.search([('id','=',room.id),('is_check','=',False)])
                  if folio_line_ids: 
                    for loop in folio_line_ids:
                      loop.state = 'sale'
                      loop.is_check = False
                      order_line_ids = sale_line_obj.search([('id','=',loop.order_line_id.id)])
                      for line in order_line_ids:
                        line.is_check=loop.is_check
                        line.state ='sale'
                for service in hotel.service_lines:
                  service_line_ids = service_obj.search([('id','=',service.id),('is_check','=',False)])
                  if service_line_ids:
                      for loop in service_line_ids:
                          loop.state ='sale'
                          loop.is_check = False
                          sale_order_ids = sale_line_obj.search([('id','=',loop.service_line_id.id)])
                          for line in sale_order_ids:
                            line.is_check = loop.is_check
                            line.state = 'sale'
                order.state = 'sale'
                fo = folio_obj.browse(hotel.id)
                res = fo._invoices_2()
                if self._context.get('open_invoices', False):
                      res = sale_orders.action_view_invoice_1(res)                
              if hotel.uncheck == False and hotel.state=='sale':
                ctx.update({'active_ids': [hotel.order_id.id],
                            'active_id': hotel.order_id.id,
                            'folio_id': hotel.id})
                res = super(SaleAdvancePaymentInv,self.with_context(ctx)).create_invoices()
                return res
              else:
                continue
        return res

    @api.multi
    def create_invoices_2(self):
        ctx = self.env.context.copy()
        if self._context.get('active_model') == 'hotel.folio':
            hotel_fol = self.env['hotel.folio']
            hotel = hotel_fol.browse(self._context.get('active_ids',
                                                       []))
            if hotel:
              ctx.update({'active_ids': [hotel.order_id.id],
                          'active_id': hotel.order_id.id,
                          'folio_id': hotel.id})

            sale_orders = self.env['sale.order'].browse(hotel.order_id.id)
            if self.advance_payment_method == 'delivered':
                sale_orders.action_invoice_create_2()
            elif self.advance_payment_method == 'all':
                sale_orders.action_invoice_create_2(final=True)
            else:
                # Create deposit product if necessary
                if not self.product_id:
                    vals = self._prepare_deposit_product()
                    self.product_id = self.env['product.product'].create(vals)
                    self.env['ir.values'].sudo().set_default('sale.config.settings', 'deposit_product_id_setting', self.product_id.id)

                sale_line_obj = self.env['sale.order.line']
                for order in sale_orders:
                    if self.advance_payment_method == 'percentage':
                        amount = order.amount_untaxed * self.amount / 100
                    else:
                        amount = self.amount
                    if self.product_id.invoice_policy != 'order':
                        raise UserError(_('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                    if self.product_id.type != 'service':
                        raise UserError(_("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                    so_line = sale_line_obj.create({
                        'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                        'price_unit': amount,
                        'product_uom_qty': 0.0,
                        'order_id': order.id,
                        'discount': 0.0,
                        'product_uom': self.product_id.uom_id.id,
                        'product_id': self.product_id.id,
                        'tax_id': [(6, 0, self.product_id.taxes_id.ids)],
                    })
                    print"orderLine"
                    self._create_invoice(order, so_line, amount)
            return {'type': 'ir.actions.act_window_close'}


    @api.multi
    def create_invoices_3(self):
        ctx = self.env.context.copy()
        if self._context.get('active_model') == 'hotel.folio':
            hotel_fol = self.env['hotel.folio']
            hotel = hotel_fol.browse(self._context.get('active_ids',
                                                       []))

        print "orderline",hotel.order_id
        if hotel:
          ctx.update({'active_ids': [hotel.order_id.id],
                      'active_id': hotel.order_id.id,
                      'folio_id': hotel.id})

        sale_orders = self.env['sale.order'].browse(hotel.order_id.id)

        print "Sale Order",sale_orders

        if self.advance_payment_method == 'delivered':
            sale_orders.action_invoice_create_3()
        elif self.advance_payment_method == 'all':
            sale_orders.action_invoice_create_3(final=True)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'deposit_product_id_setting', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError(_('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                so_line = sale_line_obj.create({
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'tax_id': [(6, 0, self.product_id.taxes_id.ids)],
                })
                self._create_invoice(order, so_line, amount)
        # if self._context.get('open_invoices', False):
        #     return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}

class AccountInvoice(models.Model):
    _inherit = "account.invoice"


    @api.multi
    def invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        # self.ensure_one()
        # self.sent = True
        # return self.env['report'].get_action(self, 'account.report_invoice')
        print "self",self.id   
        url = 'http://192.168.200.20:8080/birt/frameset?__report=Shwe_Bu_Thee_Report.rptdesign&invoice=' + str(self.id) +'&user='+str(self.env.user.id)
        if not url:
           print "Hello"
       
        if url:
            return {
                'type' : 'ir.actions.act_url',
                'url'  : url,
                'target': 'new',
            }
        return True
