# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp

class ProductProduct(models.Model):
    _inherit = 'product.product'

    currency_id = fields.Many2one("res.currency",string="Currency",related ="product_tmpl_id.currency_id",store=True,readonly=False)
    laundry_ttt = fields.Many2one("hotel.laundry.function",related="product_tmpl_id.laundry_type",string='Laundry',store=True)
    burmese_name = fields.Char(string="Burmese Name",related="product_tmpl_id.burmese_name",store=True,readonly=False)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    burmese_name = fields.Char(string="Burmese Name",store=True,readonly=False)
    currency_id = fields.Many2one("res.currency",string="Currency",store=True,readonly=False)
    product_price_line = fields.One2many("pricelist.line",'line_id',string="PriceList")
    # company_currency = fields.Many2one("res.currency",related="company_id.currency_id",store=True,readonly=False)
    # list_price = fields.Float('Sale Price', compute="_default_price",store=True)

    @api.depends('product_id')
    def get_laundry_type(self):
    	product_obj = self.env['hotel.laundry']
    	product_ids = product_obj.search([('product_id','=',product_id)])
        if product_ids:
        	self.laundry_type=product_ids.categ_id

    laundry_type = fields.Many2one("hotel.laundry.function",string="Laundry",store=True)

class PriceList(models.Model):
    _name = "pricelist.line"
    
    line_id = fields.Many2one("product.template",string="Product")
    currency = fields.Many2one("res.currency",string="Curreny",store=True)
    price = fields.Float(string="Price",store=True)