odoo.define('hotel_pos_restaurant.folio', function (require) {
	"use strict";

    var screens = require('point_of_sale.screens');
    var gui = require('point_of_sale.gui');
    var popup = require('point_of_sale.popups');
    var model = require('point_of_sale.models');
    var models = model.PosModel.prototype.models;
    var widget, folio_id;

    models.push({
        model: 'hotel.folio',
        fields: [],
        loaded: function(self, folios){ self.folios = folios; },
    },
    {
        model: 'folio.room.line',
        fields: [],
        loaded: function(self, folio_room_line){ self.folio_room_line = folio_room_line; },
    },
    {
        model: 'hotel.folio.line',
        fields: [],
        loaded: function(self, hotel_folio_line){ self.hotel_folio_line = hotel_folio_line; },
    },
    {
        model: 'hotel.room',
        fields: [],
        loaded: function(self, hotel_room){ self.hotel_room = hotel_room; },
    },
    {
        model: 'pos.order',
        fields: [],
        loaded: function(self, pos_order){ self.pos_order = pos_order; },
    });

    var HotelPosWidget = popup.extend({
        template: 'SetFolioForPOS',
        init: function() {
            this._super();
            self = this;
            this.title = 'Hotel Folio Room List';
            this.room_index = 1;
            this.hotel_folio_line = posmodel.hotel_folio_line;
        },
        show: function(options) {

            var flgUom = false;
            this.renderElement();

            // Change color of odd rows in table for initial state
            this.$('.room-list-contents tr:odd').css({
                "background-color":"#EEE"
            });
            // Change color of even rows in table for initial state
            this.$('.room-list-contents tr:even').css({
                "background-color":"#FFF"
            });

            this.$('.room-list-contents tr').click(function(){

                flgUom = true;
                // Reset original color of odd rows in table
                $('.room-list-contents tr:odd').css({
                    "background-color":"#EEE",
                    "color":"#555"
                });

                // Reset original color of even rows in table
                $('.room-list-contents tr:even').css({
                    "background-color":"#FFF",
                    "color":"#555"
                });

                $('.room-list-contents tr').removeClass("selected-room");

                // Set selected row color
                $(this).closest('tr').css({
                    "background":'rgba(110, 200, 159, 1)',
                    "color":"#FFF"}).addClass("selected-room");

            });
        },
        // called before hide, when a popup is closed.
        // extend this if you want a custom action when the
        // popup is closed.
        close: function(){
            if (widget.pos.barcode_reader) {
                widget.pos.barcode_reader.restore_callbacks();
            }
        },
        // what happens when we click cancel
        // ( it should close the popup and do nothing )
        click_cancel: function(){
            widget.gui.close_popup()
        },

        // what happens when we confirm the action
        click_confirm: function(){
            var partner_id = $("tr.selected-room").closest("tr").find('.partner_id').text();
            folio_id = $("tr.selected-room").closest("tr").find('.folio_id').text();
            var room_id = $("tr.selected-room").closest("tr").find('td:nth-child(3)').text();
            var client = widget.pos.db.get_partner_by_id(parseInt(partner_id));
            window.posmodel.get_order().set_client(client);
            $(".set-customer").text("[R"+room_id+"]");
            $(".js_customer_name").text("[R"+room_id+"]");
            widget.gui.close_popup();
        },

    });


    gui.define_popup({name:'hotel_folio_widget', widget: HotelPosWidget});

    var HotelPosButton = screens.ActionButtonWidget.extend({
        template: 'HotelPosBtn',
        button_click: function() {
            var self = this;
            widget = this;
            this.gui.show_popup('hotel_folio_widget');
        }
    });

        screens.PaymentScreenWidget.include({
        validate_order: function(force_validation) {
            this._super();
            self = this;
            folio_id = null;
        },
    });

    var _super_order = model.Order.prototype;
    model.Order = model.Order.extend({
        export_as_JSON: function(){
            var json = _super_order.export_as_JSON.apply(this,arguments);
            json.folio_id = parseInt(folio_id);
//            folio_id = null;
            return json;
        },
    });

    screens.define_action_button({
        'name': 'hotel_pos_restaurant',
        'widget': HotelPosButton
    });

});
