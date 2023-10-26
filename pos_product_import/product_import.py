from odoo import api, fields, models, tools, _
from xlrd import open_workbook
from odoo.tools.translate import _
import xlrd
import base64
from odoo.exceptions import except_orm
import logging
from datetime import datetime
from decimal import Decimal
from odoo.fields import Char
# from pip.commands.show import print_results
_logger = logging.getLogger(__name__)
import sys
reload(sys)
sys.setdefaultencoding('utf8')

header_fields = ['name','floor_id','isroom','categ_id','capacity','kyat','thb','usd']

header_indexes = {}

class ProductImport(models.Model):
    _name = "master_import.product"

    name = fields.Char('Description', required=True)
    import_date = fields.Date('Import Date', readonly=True, default=datetime.today())
    import_fname = fields.Char('Filename', size=128, required=True)
    import_file = fields.Binary('File', required=True)
    product_type = fields.Selection([('service', 'service'),('product', 'product')], 'Product Type', default='product')
    note = fields.Text('Log')
    company_id = fields.Many2one('res.company', 'Company', required=False)
    state = fields.Selection([('draft', 'Draft'),('completed', 'Completed'),('error', 'Error'),], 'States', default='draft')

    err_log = ''
    total_record = 0
    
    def _check_file_extension(self):
        for import_file in self.browse(self.ids):
            return import_file.import_fname.lower().endswith('.xls')  or import_file.import_fname.lower().endswith('.xlsx')


    _constraints = [(_check_file_extension, "Please import microsoft excel (.xlsx or .xls) file!", ['import_fname'])]

    # ## Load excel data file
    def get_excel_datas(self, sheets):
        result = []
        for s in sheets:
            # # header row
            headers = []
            header_row = 0
            for hcol in range(0, s.ncols):
                headers.append(s.cell(header_row, hcol).value)
                            
            result.append(headers)
            
            # # value rows
            for row in range(header_row + 1, s.nrows):
                values = []
                for col in range(0, s.ncols):
                    values.append(s.cell(row, col).value)
                result.append(values)
            self.total_record = len(result) -3
        return result
    
    # ## Check excel row headers with header_fields and define header indexes for database fields
    def get_headers(self, line):
        if line[0].strip().lower() not in header_fields:
            raise orm.except_orm(_('Error :'), _("Error while processing the header line %s.\\n\nPlease check your Excel separator as well as the column header fields") % line)
        else:
            # ## set header_fields to header_index with value -1
            for header in header_fields:
                header_indexes[header] = -1  
                     
            col_count = 0
            for ind in range(len(line)):
                if line[ind] == '':
                    col_count = ind
                    break
                elif ind == len(line) - 1:
                    col_count = ind + 1
                    break
            
            for i in range(col_count):                
                header = line[i].strip().lower()
                if header not in header_fields:
                    self.err_log += '\n' + _("Invalid Excel File, Header Field '%s' is not supported !") % header
                else:
                    header_indexes[header] = i
                                
            for header in header_fields:
                if header_indexes[header] < 0:                    
                    self.err_log += '\n' + _("Invalid Excel file, Header '%s' is missing !") % header
                    
                    
                    
    def check_date_value(self, date_value, message):
        result_date = None
        try:
            data_time = float(date_value)
            result = xlrd.xldate.xldate_as_tuple(data_time, 0)
            a = str(result[0]) + '/' + str(result[1]) + '/' + str(result[2]) + ' ' + str(result[3]) + ':' + str(result[4]) + ':' + str(result[5])
     
            result_date = datetime.strptime(a, '%Y/%m/%d %H:%M:%S').date()
        except Exception, e:
            try:
                str_date = str(date_value) + ' 00:00:00'
                print str_date
                result_date = datetime.strptime(str_date, '%d.%m.%Y %H:%M:%S').date()
                print '1'
            except Exception, e:
                try:
                    str_date = str(date_value) + ' 00:00:00'
                    result_date = datetime.strptime(str_date, '%Y.%m.%d %H:%M:%S').date()
                    print '2'
                except Exception, e:
                    try:
                        str_date = str(date_value) + ' 00:00:00'
                        result_date = datetime.strptime(str_date, '%d.%m.%Y %H:%M:%S').date()
                        print '3'
                    except Exception, e:
                        try:
                          str_date = str(date_value) + ' 00:00:00'
                          result_date = datetime.strptime(str_date, '%d-%m-%y %H:%M:%S').date()
                          print '4'
                        except Exception, e:
                          return None             
                          print '5'         
#                             raise orm.except_orm(_('Error :'), _("Error while processing Excel Columns.\
#                          \n\nPlease check your " + message + " !"))                        
        return result_date
    
    def import_data(self):
        htl_product_product = self.env['product.product']
        htl_product_template = self.env['product.template']
        # htl_product_uom_categ = self.env['product.uom.categ']
        htl_floor_obj = self.env['hotel.floor']
        htl_room_cat_obj = self.env['hotel.room.type']
        # htll_res_partner = self.env['res.partner']
        htl_payment_type = self.env['payment.type']
        htl_room_obj = self.env['hotel.room']
        htl_currency_obj = self.env['res.currency']
        import_file = self.import_file
        product_type = self.product_type
#         uo_id = 0
#         if product_type.lower() == 'service':
#             uo_id = '5'
#         else:
#             uo_id = '1'
     

        header_line = True

        lines = base64.decodestring(import_file)
        wb = open_workbook(file_contents=lines)
        excel_rows = self.get_excel_datas(wb.sheets())
        all_data = []
        value = {}
        product_type = 'product'
        name = pack_size = None
        create_count = 0
        update_count = 0
        skipped_count = 0
        for line in excel_rows:
            if not line or line and line[0] and line[0] in ['', '#']:
                continue
            
            if header_line:
                self.get_headers(line)
                header_line = False                           
            elif line and line[0] and line[0] not in ['#', '']:
                import_vals = {}
                # ## Fill excel row data into list to import to database
                for header in header_fields:
                    import_vals[header] = line[header_indexes[header]]
                print line
                all_data.append(import_vals)
       
        if self.err_log <> '':
            import_id = self.ids[0]
            err = self.err_log
            #self.write(self.ids[0], {'note': ''})
            self.write({'note': err,'state': 'error'})
        else:
            for data in all_data:
                
                #template_id= inc_acc_id = exp_acc_id = None
                comp_id = supplier_id = None
                unit_categ_id = 1

                
                # unit_price = data['unit_price'] 
                # exp_date = str(data['exp_date']).strip()
                # supplier = str(data['supplier']).strip()
                # unit_category = str(data['uom_category']).strip()
                # price_calculation=data['price_calculation']
                #  scheme=str(data['scheme']).strip()
                name_template = str(data['name']).strip()
                name = str(name_template.split('.')[0])
                print "-------------------------name template---------------------------"
                print name_template
                print product_type
                floor_id = str(data['floor_id'])
                categ_id = str(data['categ_id'])
                isroom= data['isroom']
                capacity= int(data['capacity'])
                kyat_price = int(data['kyat'])
                thb_price = int(data['thb'])
                usd_price = int(data['usd'])
                product_type = self.product_type

                if floor_id:
                    print "hello"
                    floor_ids = htl_floor_obj.search([('name','=',floor_id)])
                    if floor_ids:
                        floor = floor_ids.id
                    else:
                        floor = htl_floor_obj.create({'name': floor_id}).id
                if categ_id:
                    print "hi"
                    categ_ids = htl_room_cat_obj.search([('name','=',categ_id)])
                    if not categ_ids:
                        categ = htl_room_cat_obj.create({'name': categ_id}).id    
                    else:
                        htl_room_cat_obj.write({'name': categ_id})
                        categ = categ_ids.id
                if name and product_type:
                    print "helo",categ
                    print 'name',name
                    product_tmp_ids = htl_product_template.search([('name','=',name),('categ_id','=',1)])
                    print product_tmp_ids,"Od"
                    if not product_tmp_ids:
                        if product_type == 'product':
                            vals={'name': name,
                                'type':'consu',
                                'categ_id':1}
                            product_tmp_id = htl_product_template.create(vals).id
                        if product_type == 'service':
                            vals={'name': name,
                                'type':'service',
                                'categ_id':1}
                            product_tmp_id = htl_product_template.create(vals).id
                    else:
                        if product_type == 'product':
                            vals={'name': name,
                                    'type':'consu',
                                    'categ_id':1}
                            htl_product_template.write(vals)
                        if product_type == 'service':
                            vals={'name': name,
                                'type':'service',
                                'categ_id':1}
                            htl_product_template.write(vals)
                        product_tmp_id = product_tmp_ids.id
                print"hellllllllll"    
                if product_tmp_id:
                    print "hilo"
                    product_ids = htl_product_product.search([('product_tmpl_id','=',product_tmp_id)])
                    if not product_ids:
                        vals={'product_tmpl_id': product_tmp_id,
                            'isroom':isroom}
                        product_id = htl_product_product.create(vals).id
                    else:
                        vals={'product_tmpl_id': product_tmp_id,
                            'isroom':isroom}
                        htl_product_product.write(vals)
                        product_id = product_ids.id                        

                if product_id and floor_id and categ_id:
                    print "lohi"
                    room_ids = htl_room_obj.search([('product_id','=',product_id),('floor_id','=',floor),('categ_id','=',categ)])
                    print "name is exit , ", room_ids
                    if not room_ids:
                        room_val = {
                            'product_id': product_id,
                            'floor_id' : floor,
                            'categ_id':categ,
                            'capacity':capacity,
                            'status': 'available'
                        }
                        rooms = htl_room_obj.create(room_val)
                        create_count += 1
                    else:
                        print "name is exit , ",room_ids
                        room_val = {
                            'product_id': product_id,
                            'floor_id' : floor,
                            'categ_id':categ,
                            'capacity':capacity,
                            'status': 'available'}
                        htl_room_obj.write(room_val)
                        rooms = room_ids
                        print "Product is Updated...."
                        update_count += 1
                if rooms and kyat_price or usd_price or thb_price:
                    if kyat_price:
                        currency_id = htl_currency_obj.search([('name','=','MMK')])    
                        saleprice_ids = htl_payment_type.search([('room_charges','=',rooms.id),
                            ('currency','=',currency_id.id),('price','=',kyat_price)]) 
                        if not saleprice_ids:
                            vals={'room_charges':rooms.id,
                                'currency': currency_id.id,
                                'price': kyat_price}
                            htl_payment_type.create(vals) 
                        else:
                            vals={'room_charges':rooms.id,
                                'currency': currency_id.id,
                                'price': kyat_price}
                            htl_payment_type.write(vals)
                    if thb_price:
                        currency_id = htl_currency_obj.search([('name','=','THB')])    
                        saleprice_ids = htl_payment_type.search([('room_charges','=',rooms.id),
                            ('currency','=',currency_id.id),('price','=',thb_price)]) 
                        if not saleprice_ids:
                            vals={'room_charges':rooms.id,
                                'currency': currency_id.id,
                                'price': thb_price}
                            htl_payment_type.create(vals) 
                        else:
                            vals={'room_charges':rooms.id,
                                'currency': currency_id.id,
                                'price': thb_price}
                            htl_payment_type.write(vals)
                    if usd_price:
                        currency_id = htl_currency_obj.search([('name','=','USD')])    
                        saleprice_ids = htl_payment_type.search([('room_charges','=',rooms.id),
                            ('currency','=',currency_id.id),('price','=',usd_price)]) 
                        if not saleprice_ids:
                            vals={'room_charges':rooms.id,
                                'currency': currency_id.id,
                                'price': usd_price}
                            htl_payment_type.create(vals) 
                        else:
                            vals={'room_charges':rooms.id,
                                'currency': currency_id,
                                'price': usd_price}
                            htl_payment_type.write(vals)
                else:
                        skipped_count += 1
                        print 'skipped'        
                        print name

                current = create_count + update_count + skipped_count                    
                print current,'/',self.total_record,'[',name,']'
        
                      
            message = 'Import Success at ' + str(datetime.strptime(datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                      '%Y-%m-%d %H:%M:%S'))+ '\n' + str(self.total_record)+' records imported' +'\
                      \n' + str(create_count) + ' created\n' + str(update_count) + ' updated\n' + str(skipped_count) + ' skipped'
            self.write({'state': 'completed','note': message})
            
