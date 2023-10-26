# -*- coding: utf-8 -*-
from odoo import http

# class ArOdooHideTax(http.Controller):
#     @http.route('/ar_odoo_hide_tax/ar_odoo_hide_tax/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ar_odoo_hide_tax/ar_odoo_hide_tax/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ar_odoo_hide_tax.listing', {
#             'root': '/ar_odoo_hide_tax/ar_odoo_hide_tax',
#             'objects': http.request.env['ar_odoo_hide_tax.ar_odoo_hide_tax'].search([]),
#         })

#     @http.route('/ar_odoo_hide_tax/ar_odoo_hide_tax/objects/<model("ar_odoo_hide_tax.ar_odoo_hide_tax"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ar_odoo_hide_tax.object', {
#             'object': obj
#         })