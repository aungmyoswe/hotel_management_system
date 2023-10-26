# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2017 Infinite Business Solution (www.ibizmyanmar.com). All rights reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Odoo Master Data Import',
    'category': 'Master',
    'version': '0.1',
    'author': 'Infinite Business Solution Co.,Ltd',
    'website': 'www.ibizmyanmar.com',
    'summary': 'Master Data Import',
    'data': ['master_import.xml'],
    'application': 'True',
    'depends': ['base', 'base_import','product'],
    'description':  """
Module of Master Data Excel Import
==================================

Master data import module that covers:
--------------------------------------
    * Product Master Data
    * Customer Master Data
    * Supplier Master Data

Can use all versions of excel file such as .xls and .xlsx.
"""
}