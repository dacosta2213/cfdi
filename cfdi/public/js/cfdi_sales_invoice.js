frappe.ui.form.on("Sales Invoice", {
	// setup: function(frm) {
	// 	 frm.set_query('sales_invoice', 'si_sustitucion', () => {
	// 		    return {
	// 		        filters: {
	// 		            customer: frm.doc.customer
	// 		        }
	// 		    }
	// 		})
	// },
	onload: function(frm) {
    frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "Configuracion CFDI",
          filters: {
          "name": frm.doc.perfil
          }
        },
        callback: function (data) {
          if (frm.doc.__unsaved)  {
            let v = data.message;
            // console.log(v);
            cur_frm.set_value("regimen_fiscal", v.regimen_fiscal);
            cur_frm.set_value("forma_de_pago", v.forma_de_pago);
            cur_frm.set_value("tipo_de_comprobante", v.tipo_de_comprobante);
            cur_frm.set_value("metodo_pago", v.metodo_pago);
            cur_frm.set_value("lugar_expedicion", v.lugar_expedicion);
            cur_frm.set_value("zona_horaria", v.zona_horaria);
            cur_frm.set_value("uso_cfdi", v.uso_cfdi);
            cur_frm.set_value("no_certificado", v.no_certificado);
            cur_frm.set_value("nombre_emisor", v.nombre_emisor);
            cur_frm.set_value("rfc_emisor", v.rfc_emisor);
          }
        }
    })
  },
	perfil: function(frm){
		frappe.call({
			method: "frappe.client.get",
			args:{
				doctype: "Configuracion CFDI",
				filters: {
					"name": frm.doc.perfil
				}
			},
			callback: function(data){
				console.log(data.message);
				let v = data.message;
				cur_frm.set_value("regimen_fiscal", v.regimen_fiscal);
				cur_frm.set_value("forma_de_pago", v.forma_de_pago);
				cur_frm.set_value("tipo_de_comprobante", v.tipo_de_comprobante);
				cur_frm.set_value("metodo_pago", v.metodo_pago);
				cur_frm.set_value("lugar_expedicion", v.lugar_expedicion);
				cur_frm.set_value("zona_horaria", v.zona_horaria);
				cur_frm.set_value("uso_cfdi", v.uso_cfdi);
				cur_frm.set_value("no_certificado", v.no_certificado);
				cur_frm.set_value("nombre_emisor", v.nombre_emisor);
				cur_frm.set_value("rfc_emisor", v.rfc_emisor);
			}
		})
	},
	refresh: function(frm) {
		// if (cur_frm.doc.cfdi_status == "Timbrado" ) {
  	// 	$('.btn-secondary').hide();
		// } else {
		// 	$('.btn-secondary').show();
		// }

		frm.set_query('sustituido', () => {
		    return {
		        filters: {
		            cfdi_status: 'Cancelado'
		        }
		    }
		})
	},
	onload_post_render: function () {
		$('.btn[data-fieldname=timbrar_cfdi]').addClass('btn-success');
		$('.btn[data-fieldname=cancelar_cfdi]').addClass('btn-danger');
	},
	timbrar_cfdi: function(frm,dt,dn) {
		frappe.call({
			method: "frappe.client.get",
			freeze: true,
			freeze_message: 'Timbrando. Por favor espere...',
			args: {
				doctype: "Configuracion CFDI",
				filters: {
					"name": frm.doc.perfil
				}
			},
			callback: function (data) {
      	sales_invoice_timbrado(frm,dn,data.message)
      }
    })
	},
	cancelar_cfdi: function(frm,dt,dn) {
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Configuracion CFDI",
				filters: {
					"name": frm.doc.perfil
				}
			},
			callback: function (data) {
      	sales_invoice_cancelar(frm,dn,data.message)
    	}
  	})
	}
})

var sales_invoice_timbrado = function(frm,dn,v){
  frappe.call({
          method: "cfdi.cfdi.doctype.cfdi.cfdi.sales_invoice_timbrado",
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
var sales_invoice_cancelar = function(frm,dn,v) {
  frappe.call({
	method: "cfdi.cfdi.doctype.cfdi.cfdi.cancel_by_uuid_sales_invoice",
	freeze: true,
	freeze_message: 'Timbrando. Por favor espere...',
	args:{
		url: 'https://' + v.url,
		token: v.token,
		uuid: cur_frm.doc.uuid,
		docname: dn,
		rfc: cur_frm.doc.rfc_emisor
	},
	callback: function (data) {
		console.log(data.message.data);
		cur_frm.reload_doc();
	}
  })
}
