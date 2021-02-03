// Copyright (c) 2018, C0D1G0 B1NAR10 and contributors
// For license information, please see license.txt

frappe.ui.form.on('Configuracion CFDI', {
	refresh: function(frm) {

		// $('.ayudachico').hide();
		// $('.ayudagrande').hide();
		//
		// $('.page-actions').prepend('<button data-video-id="VAC70boCkIo"  class="btn-xs js-modal-btn ayudagrande "><i class="far fa-question-circle"></i>  Ayuda</button>');
		// $(".js-modal-btn").modalVideo();

	},
	modo_prueba: function(frm) {
		if (cur_frm.doc.modo_prueba) {
			cur_frm.set_value("regimen_fiscal", "601");
			cur_frm.set_value("forma_de_pago", "03");
			cur_frm.set_value("tipo_de_comprobante", "I");
			cur_frm.set_value("metodo_pago", "PUE");
			cur_frm.set_value("lugar_expedicion", "21200");
			cur_frm.set_value("uso_cfdi","P01");
			cur_frm.set_value("no_certificado", "20001000000300022762");
			cur_frm.set_value("nombre_emisor", "Emisor de Prueba");
			cur_frm.set_value("rfc_emisor", "TCM970625MB1");
			// cur_frm.set_value("folder", "abc.posix.mx");
			cur_frm.set_value("url_timbrado", "https://t1demo.facturacionmoderna.com/timbrado/wsdl");
			cur_frm.set_value("user_id", "UsuarioPruebasWS");
			cur_frm.set_value("user_password", "b9ec2afa3361a59af4b4d102d3f704eabdf097d4");

			cur_frm.set_df_property("regimen_fiscal", "read_only", 1);
			cur_frm.set_df_property("forma_de_pago", "read_only", 1);
			cur_frm.set_df_property("tipo_de_comprobante", "read_only", 1);
			cur_frm.set_df_property("metodo_pago", "read_only", 1);
			cur_frm.set_df_property("lugar_expedicion", "read_only", 1);
			cur_frm.set_df_property("uso_cfdi", "read_only", 1);
			cur_frm.set_df_property("no_certificado", "read_only", 1);
			cur_frm.set_df_property("nombre_emisor", "read_only", 1);
			cur_frm.set_df_property("rfc_emisor", "read_only", 1);
			// cur_frm.set_df_property("folder", "read_only", 1);

		} else {
			cur_frm.set_value("regimen_fiscal", "601");
			cur_frm.set_value("forma_de_pago", "03");
			cur_frm.set_value("tipo_de_comprobante", "I");
			cur_frm.set_value("metodo_pago", "PUE");
			cur_frm.set_value("lugar_expedicion", "");
			cur_frm.set_value("uso_cfdi","P01");
			cur_frm.set_value("no_certificado", "");
			cur_frm.set_value("nombre_emisor", "");
			cur_frm.set_value("rfc_emisor", "");
			// cur_frm.set_value("folder", "abc.posix.mx");
			cur_frm.set_value("url_timbrado", "https://t2.facturacionmoderna.com/timbrado/wsdl");
			cur_frm.set_value("user_id", "FORN790120TE7");
			cur_frm.set_value("user_password", "e8d451a3fec61eef9ee6b358d6f0d78922777e8d");

			cur_frm.set_df_property("regimen_fiscal", "read_only", 0);
			cur_frm.set_df_property("forma_de_pago", "read_only", 0);
			cur_frm.set_df_property("tipo_de_comprobante", "read_only", 0);
			cur_frm.set_df_property("metodo_pago", "read_only", 0);
			cur_frm.set_df_property("lugar_expedicion", "read_only", 0);
			cur_frm.set_df_property("uso_cfdi", "read_only", 0);
			cur_frm.set_df_property("no_certificado", "read_only", 0);
			cur_frm.set_df_property("nombre_emisor", "read_only", 0);
			cur_frm.set_df_property("rfc_emisor", "read_only", 0);
			// cur_frm.set_df_property("folder", "read_only", 0);
		}

	}
});
