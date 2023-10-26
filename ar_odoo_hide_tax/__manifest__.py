# -*- coding: utf-8 -*-
{
    'name': "Disable Tax",

    'summary': """
        Disable Tax from Sales module, Purchase module and Accounting module""",

    'description': """
        Long description of module's purpose
    """,

    'author': "ARODOO.COM",
    'website': "http://www.arodoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale','hotel', 'account', 'purchase'],

    # always loaded
    'data': [
        'views/sale_view.xml',
        'views/account_view.xml',
        'views/purchase_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}