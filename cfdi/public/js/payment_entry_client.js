frappe.ui.form.on("Payment Entry", {
  setup: function(frm) {
    frm.set_query("tipo_documento" ,function(doc) {
      return{
				"filters": {
          "name":["in",["Sales Invoice","CFDI"]]
        }
			}
    })
  },
  paid_amount: function(frm){
    cur_frm.set_value("saldo_insoluto", cur_frm.doc.impsaldoanterior - cur_frm.doc.paid_amount);
  },
  onload_post_render: function(frm) {

  },
  validate: function(frm) {
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
    			let v = data.message;
    			console.log('onload_post: ', v)
    			cur_frm.set_value("regimen_fiscal", v.regimen_fiscal);
    			cur_frm.set_value("lugar_expedicion", v.lugar_expedicion);
    			cur_frm.set_value("rfc_emisor", v.rfc_emisor);
    			cur_frm.set_value("url_timbrado", v.url_timbrado);
    			cur_frm.set_value("folder", v.folder);
    			cur_frm.set_value("user_id", v.user_id);
    			cur_frm.set_value("user_password", v.user_password);
    		}
    	}
    })

    if (frm.doc.party_type === "Customer") {
      $(frm.doc.references).each(function(index){
          frappe.db.get_value('Sales Invoice',this.reference_name,['grand_total','uuid'], (r) => {
            if(this.total_moneda_original==null){
              this.total_moneda_original = r.grand_total
            }
            this.uuid = r.uuid
      		})
      })
    }
  },
  after_save: function(frm) {
    var total_original = 0.0;
    $(cur_frm.doc.references).each(function(index){
      total_original = parseFloat(total_original) + parseFloat(this.total_moneda_original);
    });
    cur_frm.set_value("gran_total_original", total_original);
  },
  refresh: function(frm) {


    console.log('Payment Entry Script loaded')
    $(".btn[data-fieldname=presentar_al_sat]").addClass('btn-success');
  },
  presentar_al_sat: function(frm,dt,dn) {
    if (frm.doc.__unsaved) {
      alert("El documento no está guardado.")
    } else {
      frappe.call({
  			method: "frappe.client.get",
  			args: {
  				doctype: "Configuracion CFDI",
  				filters: {
  					"name": "Cliente"
  				}
  			},
  			callback: function (data) {
          console.log('respuesta de Configuracion CFDI: ', data.message)
        	payment_entry_pago(frm,dn,data.message)
        }
      })
    }
  },
  cancelar: function(frm) {
    if (frm.doc.__unsaved) {
      alert("El documento no esta guardado.")
    } else {
      frappe.call({
        method: "cfdi.cfdi.doctype.cfdi.cfdi.cancel_by_uuid_pago",
        args:{
          docname: frm.doc.name
        }
      })
    }
  },
  timbrar_cfdi_sin_servicio: function(frm) {
    swal({
      title: 'Timbrado de CFDI',
      type: 'info',
      html:'Necesitas contratar timbres para timbrar esta factura',
    	showCloseButton: true,
    })
  }
})

//RG>Aaron - Para que esta user_id? - si no se ocupa para el 15 Ene 2020, quitarlo y quitarlo del metodo de py
var payment_entry_pago = function(frm,dn,v){
  frappe.call({
    method: "cfdi.cfdi.doctype.cfdi.cfdi.issue_pago",
    freeze: true,
    freeze_message: 'Timbrando. Por favor espere...',
    args:{
      invoice: frm.doc.factura_fuente,
      url: 'https://' + v.url,
      token: v.token,
      docname: dn,
      version: v.version,
      tipo: frm.doc.tipo_documento,
      user_id: v.user_id,
      user_password: v.user_password,
      folder: v.folder,
      nombre_emisor: v.nombre_emisor,
      no_certificado: v.no_certificado
    },
    callback: function (data) {
      console.log(data.message.data);
      frm.reload_doc();
    }
  })
}
