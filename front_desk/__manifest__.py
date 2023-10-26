{
    'name': 'Front Desk',
    'version': '0.1',
    'license': 'AGPL-3',
    'author': 'Infinite Business Solution Co.,Ltd',
    'website': 'www.ibizmyanmar.com',
    'category' : 'res.partner',
    'description': """

Front Desk
=================================================
This module will add Front Desk

    """,
    'depends': ['base','hotel','partner_extension'],
    'data' : [
    'views/hotel_front_task_view.xml'],
    'application': True,
}
