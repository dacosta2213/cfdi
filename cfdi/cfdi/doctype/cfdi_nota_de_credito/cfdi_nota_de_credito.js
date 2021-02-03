// Copyright (c) 2018, C0D1G0 B1NAR10 and contributors
// For license information, please see license.txt

frappe.ui.form.on("CFDI Nota de Credito Item", "item_code", function(frm, cdt, cdn) {
	row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "monto", row.qty * row.precio_de_venta);

	frappe.call({
		method: "frappe.client.get",
		args: {
			doctype: "Item",
			filters: {
			"item_code": row.item_code
			}
		},
		error: function (data) {

			$('.modal-dialog').hide();
			alert('Por favor selecciona un articulo.');
			frappe.hide_msgprint(instant);

		},
		callback: function (data) {
			x = data.message;
			// v = data.message.tasa
			// v = data.message.taxes[0] ? parseFloat(data.message.taxes[0].tax_rate) : 0;
			// factortax = (v * 0.01) + 1;
			factortax = ( x.tasa * 0.01);
			frappe.model.set_value(cdt, cdn, "tax", x.tasa);
			frappe.model.set_value(cdt, cdn, "impuestos_totales", parseFloat((row.monto * factortax).toFixed(2)) );
			frappe.model.set_value(cdt, cdn, "precio_neto", parseFloat( row.monto).toFixed(2) );
			frappe.model.set_value(cdt, cdn, "precio_unitario_neto", parseFloat(row.precio_de_venta ).toFixed(2) );
			// si el impuesto se incluye en el precio de venta
			// frappe.model.set_value(cdt, cdn, "impuestos_totales", parseFloat((row.monto - (row.monto / factortax)).toFixed(2)) );
			// frappe.model.set_value(cdt, cdn, "precio_neto", parseFloat( (row.monto / factortax)).toFixed(2) );
			// frappe.model.set_value(cdt, cdn, "precio_unitario_neto", parseFloat( (row.precio_de_venta / factortax)).toFixed(2) );
			}
		})

});

frappe.ui.form.on("CFDI Nota de Credito Item", "qty", function(frm, cdt, cdn) {
	row = locals[cdt][cdn];
	factortax = (row.tax * 0.01);
	// factortax = (row.tax * 0.01) + 1;
	frappe.model.set_value(cdt, cdn, "monto", row.qty * row.precio_de_venta);
	frappe.model.set_value(cdt, cdn, "impuestos_totales", parseFloat((row.monto * factortax).toFixed(2)) );
	frappe.model.set_value(cdt, cdn, "precio_neto", parseFloat( row.monto).toFixed(2) );
	frappe.model.set_value(cdt, cdn, "precio_unitario_neto", parseFloat(row.precio_de_venta ).toFixed(2) );
});

frappe.ui.form.on("CFDI Nota de Credito Item", "precio_de_venta", function(frm, cdt, cdn) {
	row = locals[cdt][cdn];
	factortax = (row.tax * 0.01);
	frappe.model.set_value(cdt, cdn, "monto", row.qty * row.precio_de_venta);
	frappe.model.set_value(cdt, cdn, "impuestos_totales", parseFloat((row.monto * factortax).toFixed(2)) );
	frappe.model.set_value(cdt, cdn, "precio_neto", parseFloat( row.monto).toFixed(2) );
	frappe.model.set_value(cdt, cdn, "precio_unitario_neto", parseFloat(row.precio_de_venta ).toFixed(2) );
});

frappe.ui.form.on('CFDI Nota de Credito', {
	finalizar: function(frm) {
		frm.call('movimiento')
	},
	setup: function(frm) {
		 frm.set_query('paid_to', () => {
			    return {
			        filters: {
			            root_type: 'Asset',
			            account_currency: frm.doc.currency
			        }
			    }
			})
		 // frm.set_query('sales_invoice', 'si_sustitucion', () => {
			//     return {
			//         filters: {
			//             customer: frm.doc.customer
			//         }
			//     }
			// })
	},
	onload: function(frm) {
		frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Configuracion CFDI",
					filters: {
					"name": "Cliente"
					}
				},
				callback: function (data) {
					if (frm.doc.__unsaved)  {
						v = data.message;
						console.log(v);
						cur_frm.set_value("regimen_fiscal", v.regimen_fiscal);
						//cur_frm.set_value("forma_de_pago", v.forma_de_pago);
						//cur_frm.set_value("metodo_pago", v.metodo_pago);
						cur_frm.set_value("lugar_expedicion", v.lugar_expedicion);
						// cur_frm.set_value("uso_cfdi", v.uso_cfdi);
						cur_frm.set_value("no_certificado", v.no_certificado);
						cur_frm.set_value("nombre_emisor", v.nombre_emisor);
						cur_frm.set_value("rfc_emisor", v.rfc_emisor);
						cur_frm.set_value("url_timbrado", v.url_timbrado);
						cur_frm.set_value("folder", v.folder);
						cur_frm.set_value("user_id", v.user_id);
						cur_frm.set_value("user_password", v.user_password);
					}
				}
				})
		},
		refresh: function(frm) {
			if(cur_frm.doc.status === "Timbrado" || cur_frm.doc.status === "Cancelado") {
				cur_frm.set_df_property("forma_de_pago", "read_only", 1);
				cur_frm.set_df_property("condiciones_de_pago", "read_only", 1);
				cur_frm.set_df_property("metodo_de_pago", "read_only", 1);
				cur_frm.set_df_property("referencia_de_pago", "read_only", 1);
				cur_frm.set_df_property("cliente", "read_only", 1);
				cur_frm.set_df_property("status", "read_only", 1);
				cur_frm.get_field("items").grid.toggle_enable("item_code", false);
				cur_frm.get_field("items").grid.toggle_enable("qty", false);
			}
			if(doc.docstatus=1) {
				cur_frm.add_custom_button(__('Payment'),
					this.make_payment_entry, __("Make"));
					}
		},
		onload_post_render: function () {
			$('.btn[data-fieldname=timbrar_cfdi]').addClass('btn-success');
			$('.btn[data-fieldname=validar_ticket]').addClass('btn-warning');
		},
		timbrar_cfdi: function(frm,dt,dn) {
			// debe de ir a issue_egreso(url, token, docname, version, b64=False):
			console.log('inicio de timbrado');
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Configuracion CFDI",
					filters: {
						"name": 'Cliente'
					}
				},
				callback: function (data) {
	      	nc_timbrado(frm,dn,data.message)
	      }
	    })

			// frappe.call({
			// 	      method: "cfdi.cfdi.doctype.cfdi.cfdi.issue_egreso",
			// 				args:{
			// 					url: 'https://' + frm.doc.url,
			// 					token: frm.doc.token,
			// 					docname: frm.doc.name,
			// 					version: frm.doc.version
			// 				},
			// 				callback: function (data) {
			// 					console.log(data.message.data);
			// 					frm.reload_doc();
			// 				}
			// 			})

		},
		cancelar_cfdi: function(frm) {
			console.log('inicio de cancelacion');
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Configuracion CFDI",
					filters: {
						"name": 'Cliente'
					}
				},
				callback: function (data) {
					console.log(data.message)
	      	cancelar(frm,data.message)
	      }
	    })

			// if (frm.doc.__unsaved) {
			// 	alert("La factura no esta guardada.")
			// } else {
			// 	frappe.call({
			// 		      method: "cfdi.cfdi.doctype.cfdi.cfdi.cancelar_egreso",
			// 		      args:{
			// 					docname: frm.doc.name
			// 				},
			// 				callback: function (data) {
			// 					cur_frm.set_value("cfdi_status", "Cancelado");
			// 				}
			// 	})
			// }
		},
		validate: function(frm){
			var iiva = 0;
			var iieps = 0;
			var ineto = 0;
			var itotal = 0;

			$(cur_frm.doc.items).each(function(index){

				ineto += parseFloat(this.precio_neto);
				itotal += parseFloat(this.monto);
				if (this.tax == 16) {
					iiva += parseFloat(this.impuestos_totales);
				} else if (this.tax == 8)  {
					iieps += parseFloat(this.impuestos_totales);
				}
			});
			cur_frm.set_value("total_iva", parseFloat(iiva));
			cur_frm.set_value("total_ieps", parseFloat(iieps));
			cur_frm.set_value("total_impuestos", parseFloat(iiva) + parseFloat(iieps));
			cur_frm.set_value("total_neto", parseFloat(ineto));
			// var totaldesc = parseFloat(itotal) - parseFloat(cur_frm.doc.descuento);
			cur_frm.set_value("total", cur_frm.doc.total_impuestos + cur_frm.doc.total_neto);

		}
});


var nc_timbrado = function(frm,dn,v){
  frappe.call({
          method: "cfdi.cfdi.doctype.cfdi.cfdi.issue_egreso",
          args:{
            url: 'https://' + v.url,
            token: v.token,
            docname: dn,
            version: v.version
          },
          callback: function (data) {
            console.log(data.message.data);
            frm.reload_doc();
          }
    })
}

var cancelar = function(frm,v){
	frappe.call({
					method: "cfdi.cfdi.doctype.cfdi.cfdi.cancel_by_uuid_egreso",
					args:{
						url: 'https://' + v.url,
						token: v.token,
						uuid: frm.doc.uuid,
						docname: frm.doc.name,
						rfc: frm.doc.rfc_emisor
					},
					callback: function (data) {
						console.log(data.message);
						frm.reload_doc();
					}
		})
}
