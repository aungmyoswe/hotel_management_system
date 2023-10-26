import time
from datetime import datetime, timedelta
from dateutil import relativedelta
from calendar import monthrange
import babel
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo.addons import decimal_precision as dp

class CurrencyExchange(models.Model):
    _name = 'res.currency.exchange'

    name = fields.Char(string='Description' ,store=True)
    from_currency = fields.Many2one('res.currency','From Currency', required=True)
    from_amount = fields.Float(string='Amount', default=1)
    to_currency = fields.Many2one('res.currency','To Currency', required=True)
    to_amount = fields.Float(string='Amount', default=1)
    active = fields.Boolean(string='Active', default=True)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    @api.model
    def create(self, vals):
        print "CREATING THE EXCHANGE"
        from_id = self.env['res.currency'].search([('id','=',vals['from_currency'])]).name
        to_id = self.env['res.currency'].search([('id','=',vals['to_currency'])]).name
        month = datetime.strptime(vals['start_date'], '%Y-%m-%d').strftime('%B')
        print month
        vals['name'] = str(from_id) +' TO '+ str(to_id) + ' FOR ' + str(month.upper())
        return super(CurrencyExchange, self).create(vals)


