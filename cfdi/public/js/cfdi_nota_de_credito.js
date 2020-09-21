frappe.ui.form.on("CFDI Nota de Credito", {
  setup: function(frm) {
    frm.set_query("tipo_documento" ,function(doc) {
      return{
				"filters": {
          "name":["in",["Sales Invoice","CFDI"]]
        }
			}
    })
  }
  // validate: function(frm){
  //   if(cur_frm.doc.currency!="MXN"){
  //     var cambio = cur_frm.doc.conversion_rate;
  //
  //     $(cur_frm.doc.items).each(function(index){
  //       this.precio_de_venta = (this.precio_de_venta/cambio).toFixed(2);
  //       this.monto = this.monto/cambio
  //       this.precio_unitario_neto =
  //     });
  //   }
  // }
})
