// Copyright (c) 2016, C0D1G0 B1NAR10 and contributors
// For license information, please see license.txt

frappe.ui.form.on("CFDI Item", "item_code", function(frm, cdt, cdn) {
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
			// console.log(data);
			x = data.message;
			// v = data.message.tasa
			// v = data.message.taxes[0] ? parseFloat(data.message.taxes[0].tax_rate) : 0;
			// factortax = (v * 0.01) + 1;

			// console.log('datos item' + data.message);
			frappe.model.set_value(cdt, cdn, "tax", x.tasa);

			// si el impuesto NO ESTA INCLUIDO en el precio de venta
			factortax = ( x.tasa * 0.01);
			frappe.model.set_value(cdt, cdn, "impuestos_totales", parseFloat((row.monto * factortax).toFixed(2)) );
			frappe.model.set_value(cdt, cdn, "precio_neto", parseFloat( row.monto).toFixed(2) );
			frappe.model.set_value(cdt, cdn, "precio_unitario_neto", parseFloat(row.precio_de_venta ).toFixed(2) );

			// si el impuesto se incluye en el precio de venta
			// factortax = ( x.tasa * 0.01) + 1;
			// frappe.model.set_value(cdt, cdn, "impuestos_totales", parseFloat((row.monto - (row.monto / factortax)).toFixed(2)) );
			// frappe.model.set_value(cdt, cdn, "precio_neto", parseFloat( (row.monto / factortax)).toFixed(2) );
			// frappe.model.set_value(cdt, cdn, "precio_unitario_neto", parseFloat( (row.precio_de_venta / factortax)).toFixed(2) );
			}
		})

});

frappe.ui.form.on("CFDI Item", "qty", function(frm, cdt, cdn) {
	row = locals[cdt][cdn];
	factortax = (row.tax * 0.01);
	// factortax = (row.tax * 0.01) + 1;   -RG Cambiar tambien en precio_de_venta
	frappe.model.set_value(cdt, cdn, "monto", row.qty * row.precio_de_venta);
	frappe.model.set_value(cdt, cdn, "impuestos_totales", parseFloat((row.monto * factortax).toFixed(2)) );
	frappe.model.set_value(cdt, cdn, "precio_neto", parseFloat( row.monto).toFixed(2) );
	frappe.model.set_value(cdt, cdn, "precio_unitario_neto", parseFloat(row.precio_de_venta ).toFixed(2) );
});

frappe.ui.form.on("CFDI Item", "precio_de_venta", function(frm, cdt, cdn) {
	row = locals[cdt][cdn];
	factortax = (row.tax * 0.01);
	frappe.model.set_value(cdt, cdn, "monto", row.qty * row.precio_de_venta);
	frappe.model.set_value(cdt, cdn, "impuestos_totales", parseFloat((row.monto * factortax).toFixed(2)) );
	frappe.model.set_value(cdt, cdn, "precio_neto", parseFloat( row.monto).toFixed(2) );
	frappe.model.set_value(cdt, cdn, "precio_unitario_neto", parseFloat(row.precio_de_venta ).toFixed(2) );
});

frappe.ui.form.on('CFDI', {
	onload: function(frm) {

		if(frm.doc.__islocal) {

			erpnext.utils.map_current_doc({
				method: "cfdi.cfdi.doctype.cfdi.cfdi.ticket",
					source_doctype: "Sales Invoice",
					target: me.frm,
					setters: {
						customer: me.frm.doc.customer || undefined,
					},
					get_query_filters: {
						docstatus: 1,
						cfdi_status: ["=", "Sin Timbrar"],
						company: me.frm.doc.company
					}
			});
		}


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
						// console.log(v);
						cur_frm.set_value("regimen_fiscal", v.regimen_fiscal);
						cur_frm.set_value("forma_de_pago", v.forma_de_pago);
						cur_frm.set_value("tipo_de_comprobante", v.tipo_de_comprobante);
						cur_frm.set_value("metodo_pago", v.metodo_pago);
						cur_frm.set_value("lugar_expedicion", v.lugar_expedicion);
						cur_frm.set_value("uso_cfdi", v.uso_cfdi);
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
			if(!frm.doc.__islocal && frm.doc.docstatus === 1 && frm.doc.cfdi_status === "Timbrado" && frm.doc.metodo_pago === "PPD") {
				cur_frm.add_custom_button(__('Generar Pago'),
				function() {
					frappe.route_options = {
						"party_type": "Customer",
						"mode_of_payment": "Efectivo",
						"factura_fuente": frm.doc.name,
						"party": frm.doc.customer_name
					};
					frappe.new_doc("Payment Entry");
				});

			}

//RG- Si tiene app de personalizacion visual
			// $('.ayudachico').hide();
			// $('.ayudagrande').hide();
			//   $("label:contains('CFDI Clave de Producto')").append('<button data-video-id="nG79dJ4wUFM"  class="js-modal-btn ayudachico"><i class="far fa-question-circle"></i></button>')
			// 	  $("label:contains('CFDI Clave de Unidad')").append('<button data-video-id="9L6-xve0F1w"  class="js-modal-btn ayudachico"><i class="far fa-question-circle"></i></button>')
			//
			// $('.page-actions').prepend('<button data-video-id="yPw1OPBpXvU"  class="btn-xs js-modal-btn ayudagrande "><i class="far fa-question-circle"></i>  Ayuda</button>');
			// $(".js-modal-btn").modalVideo();

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
	},
	algo: function(data) {

	},
	timbrar_cfdi: function(frm) {
		// console.log('inicio de timbrado');
		if (frm.doc.__unsaved) {
			alert("La factura no esta guardada.")
		} else {
				frappe.call({
			      method: "cfdi.cfdi.doctype.cfdi.cfdi.timbrado",
			      args:{
						docname: frm.doc.name
					},
					error: function (data) {

						$('.modal-dialog').hide();
						alert('Error al timbrar.');
						frappe.hide_msgprint(instant);

					},
					callback: function (data) {
						console.log('timbrado exitoso');
						// data.doctype = "Journal Entry";
	          // data.accounts[0].account = "IVA NO FACTURADO LOMAS - D"
	          // data.accounts[1].account = "IMPUESTOS POR PAGAR 16% IVA - D"

					}
				})
		}
	},
	cancelar_cfdi: function(frm) {
		if (frm.doc.__unsaved) {
			alert("La factura no esta guardada.")
		} else {
			frappe.call({
				      method: "cfdi.cfdi.doctype.cfdi.cfdi.cancelacion",
				      args:{
							docname: frm.doc.name
						},
						callback: function (data) {
							cur_frm.set_value("cfdi_status", "Cancelado");
						}
			})
		}
	},
	desde_ticket: function () {
			erpnext.utils.map_current_doc({
				method: "cfdi.cfdi.doctype.cfdi.cfdi.ticket",
					source_doctype: "Sales Invoice",
					target: me.frm,
					setters: {
						customer: me.frm.doc.customer || undefined,
					},
					get_query_filters: {
						docstatus: 1,
						cfdi_status: ["=", "Sin Timbrar"],
						company: me.frm.doc.company
					}
			});
	},
	// insertar: function (data) {
	// 		data.doctype = "GL Entry";
	//     data.account = "VENTAS LOMAS - D";
	//     data.credit = 10;
	//     frappe.call({
	//       method: "frappe.client.insert",
	//       args: {
	//         "doc": data
	//       }
	//     })
	// },
	onload_post_render: function () {
		$('.btn[data-fieldname=timbrar_cfdi]').addClass('btn-success');
		$('.btn[data-fieldname=validar_ticket]').addClass('btn-warning');
	},
	validar_ticket: function (frm) {
	$(cur_frm.doc.items).each(function(index){
		var cdt = "CFDI";
		var cdn = cur_frm.doc.name;
		row = locals[cdt][cdn];
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Item",
				filters: {
				"item_code": this.item_code
				}
			},
			callback: function (data) {
				x = data.message;
				// v = parseFloat(data.message.taxes[0].tax_rate);
				renglon = cur_frm.fields_dict.items.grid.grid_rows[index].doc;
				renglon.tax = x.tasa;

				// RG - Si el tax no esta incluido en el precio
				// factortax = (x.tasa * 0.01) + 1;
				// renglon.impuestos_totales = parseFloat( (renglon.monto - (renglon.monto / factortax)).toFixed(2));
				// renglon.precio_neto = parseFloat( (renglon.monto / factortax)).toFixed(2) ;
				// renglon.precio_unitario_neto = parseFloat( (renglon.precio_de_venta / factortax)).toFixed(2);

				// RG - Si el IMPUESTO SI  esta incluido en el precio
				factortax = ( x.tasa * 0.01);
				renglon.impuestos_totales = parseFloat( (renglon.monto * factortax ).toFixed(2));
				renglon.precio_neto = parseFloat(renglon.monto).toFixed(2) ;
				renglon.precio_unitario_neto = parseFloat(renglon.precio_de_venta).toFixed(2);


				}
			})

		});
		frappe.show_alert("INFORMACION VALIDADA EXITOSAMENTE");
	},
	validate: function(frm){
		if (!frm.doc.ticket) {
			frappe.show_alert(__("La factura no esta ligada a un Sales Invoice"));

		}
		// RG - else { //si quiero validar que aiga un tiquets
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
				cur_frm.set_value("total", cur_frm.doc.total_impuestos + cur_frm.doc.total_neto);
		// } //del else
	}
});
