# -*- coding: utf-8 -*-

from odoo import models, fields, api

# class ar_odoo_hide_tax(models.Model):
#     _name = 'ar_odoo_hide_tax.ar_odoo_hide_tax'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100