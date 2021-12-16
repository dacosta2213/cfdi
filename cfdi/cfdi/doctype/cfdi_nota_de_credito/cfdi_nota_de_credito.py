# -*- coding: utf-8 -*-
# Copyright (c) 2018, C0D1G0 B1NAR10 and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import date

class CFDINotadeCredito(Document):
	# @frappe.whitelist()
	# def movimiento(doc):
	# 	# frappe.throw('Desarrollo en proceso')
	# 	crear_pago(doc)
	# 	if doc.tipo_de_factura == "Devolucion":
	# 		crear_entrada(doc)

	# RG - Crear Pago
	@frappe.whitelist()
	def crear_pago(name):
		doc = frappe.get_doc('CFDI Nota de Credito',name)
		company = frappe.get_doc('Company',doc.company)
		cliente = frappe.get_doc('Customer',doc.customer)
		today = date.today()

		pii = frappe.new_doc("Payment Entry")
		pii.mode_of_payment = 'Transferencia Bancaria'
		# pii.payment_type = 'Pay'
		pii.party_type = 'Customer'
		pii.party = doc.customer
		pii.posting_date = today.strftime("%Y-%m-%d") #Daniel Acosta: Estaba mostrando un error de Fiscal Year al generar el payment entry

		# if doc.forma_de_pago != '01':
		# 	pii.paid_from = company.default_cash_account
		# else:
		# 	pii.paid_from = company.default_bank_account

		#pii.paid_to = company.default_receivable_account #frappe.get_value("Company",doc.company,'default_receivable_account')
		# pii.paid_to_account_currency = doc.currency
		# pii.paid_to  = doc.paid_to
		pii.reference_no = doc.name
		pii.naming_series = 'NC-'
		# RG - Los clientes con currency != MXN solo pueden hacaer transacciones en su moneda nativa (ej. USD)
		# RG - Los clientes sin default_currency o con MXN pueden transaccionar en cualquier moneda
		# RG - Los payment entries derivados de los descuentos automaticos NO podran timbrarse.
		pii.paid_amount = float(doc.total) * float(doc.conversion)
		frappe.errprint(pii.paid_amount)
		pii.source_exchange_rate = 1
		pii.received_amount = float(doc.total) * float(doc.conversion_rate)
		frappe.errprint(pii.received_amount)
		# frappe.errprint(float(doc.total) * float(doc.conversion_rate))
		for i in doc.si_sustitucion:
			pii.append('references', {
				'reference_doctype': 'Sales Invoice',
				'reference_name': i.sales_invoice,
				'allocated_amount': float(doc.total) * float(doc.conversion_rate),
			})

		pii.flags.ignore_permissions = True
		pii.flags.ignore_mandatory = True
		# pii.flags.ignore_validate = True
		pii.save()
		frappe.msgprint('Devolucion monetaria generada : '  + '<a href="#Form/Payment Entry/' + pii.name + '"target="_blank">' + pii.name + '</a>'  )

	# RG - Crear Pago
	@frappe.whitelist()
	def crear_entrada(name):
		doc = frappe.get_doc('CFDI Nota de Credito',name)
		if doc.tipo_de_factura == "Devolucion":
			pii = frappe.new_doc("Stock Entry")
			pii.purpose = 'Material Receipt'
			for i in doc.items:
				pii.append('items', {
					'item_code': i.item_code,
					'qty': i.qty,
					'uom': i.stock_uom,
					't_warehouse': i.warehouse,
				})
			pii.flags.ignore_permissions = True
			pii.submit()
			frappe.msgprint('Devolucion de Inventario generada : '  + '<a href="#Form/Stock Entry/' + pii.name + '"target="_blank">' + pii.name + '</a>'  )
			frappe.errprint('HECHO')
