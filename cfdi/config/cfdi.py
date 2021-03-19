from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Document"),
			"items": [
				{
					"type": "doctype",
					"name": "CFDI",
					"label": _("CFDI Global"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Sales Invoice",
					"label": _("Sales Invoice"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Payment Entry",
					"label": _("Payment Entry"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Perfil Fiscal",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "CFDI Nota de Credito",
					"onboard": 1,
				}
			]
		},
		{
			"label": _("Catalogos"),
			"items": [
				{
					"type": "doctype",
					"name": "CFDI Clave Unidad",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "CFDI Forma de Pago",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "CFDI Tipo De Comprobante",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "CFDI Metodo Pago",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "CFDI Uso",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "CFDI Regimen Fiscal",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "CFDI Relacion Documentos",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "CFDI Clave Producto",
					"onboard": 1,
				}
			]
		},
		{
			"label": _("Setup"),
			"items": [
				{
					"type": "doctype",
					"name": "Customer",
					"label": _("Customer"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Item",
					"label": _("Item"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Configuracion CFDI",
					"onboard": 1,
				}
			]
		},
		{
			"label": _("Report"),
			"items": [
				{
					"type": "report",
					"name": "CFDI Nota de Credito Timbrado",
					"doctype": "CFDI Nota de Credito"
				},
				{
					"type": "report",
					"name": "Timbrado de Facturas (Sales Invoice)",
					"doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"name": "Complemento de Pago",
					"doctype": "Payment Entry"
				},
				{
					"type": "report",
					"name": "Detalles CFDI",
					"doctype": "CFDI"
				},

			]
		}
	]
