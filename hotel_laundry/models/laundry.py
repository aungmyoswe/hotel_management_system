from odoo import models, fields, api

class HotelLaundry(models.Model):
    _name = "hotel.laundry"    
   
    product_id = fields.Many2one('product.product', 'Product_id',
                                 required=True, delegate=True,
                                 ondelete='cascade')
    categ_id=fields.Many2one('hotel.laundry.function', 'Laundry Type', required = True, store=True)
    charges_line = fields.One2many('payment.type','laundry_charges',string="La Charges",store=True,required=True)

    @api.model
    def create(self,vals):
    	product_id = vals['product_id']
    	categ_id = vals['categ_id']
    	print product_id,"product"
    	product_obj = self.env['product.product']
    	pro_tmpls = self.env['product.template']
    	product_ids = product_obj.search([('id','=',product_id)])
    	if product_ids:
    		product_ids.laundry_type=categ_id
    		product_ids.islaundry = True
    		# for loop in product_ids:
    		# 	product_obj.write({'laundry_type':self.categ_id.id})
    			
    	return super(HotelLaundry, self).create(vals)

class ProductProduct(models.Model):
    _inherit = "product.product"

    islaundry = fields.Boolean('Is Laundry id',store=True)
    laundry_type = fields.Many2one('hotel.laundry.function',string='Laundry Type', required = True, store=True)

class PaymentType(models.Model):
    _inherit = 'payment.type'

    laundry_charges = fields.Many2one('hotel.laundry',sting ="Laundry Charge Type",store=True)