# -*- coding: utf-8 -*-
# Copyright (c) 2018, C0D1G0 B1NAR10 and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import date

class CFDINotadeCredito(Document):
	def movimiento(self):
		# frappe.throw('Desarrollo en proceso')
		crear_pago(self)
		if self.tipo_de_factura == "Devolucion":
			crear_entrada(self)

# RG - Crear Pago
def crear_pago(self):
	company = frappe.get_doc('Company',self.company)
	cliente = frappe.get_doc('Customer',self.customer)
	today = date.today()

	pii = frappe.new_doc("Payment Entry")
	pii.mode_of_payment = 'Transferencia Bancaria'
	# pii.payment_type = 'Pay'
	pii.party_type = 'Customer'
	pii.party = self.customer
	pii.posting_date = today.strftime("%Y-%m-%d") #Daniel Acosta: Estaba mostrando un error de Fiscal Year al generar el payment entry

	# if self.forma_de_pago != '01':
	# 	pii.paid_from = company.default_cash_account
	# else:
	# 	pii.paid_from = company.default_bank_account

	#pii.paid_to = company.default_receivable_account #frappe.get_value("Company",self.company,'default_receivable_account')
	# pii.paid_to_account_currency = self.currency
	# pii.paid_to  = self.paid_to
	pii.reference_no = self.name
	pii.naming_series = 'NC-'
	# RG - Los clientes con currency != MXN solo pueden hacaer transacciones en su moneda nativa (ej. USD)
	# RG - Los clientes sin default_currency o con MXN pueden transaccionar en cualquier moneda
	# RG - Los payment entries derivados de los descuentos automaticos NO podran timbrarse.
	if self.currency != cliente.default_currency:
		pii.paid_amount = float(self.total) * float(self.conversion_rate)
	else:
		pii.paid_amount = float(self.total)
	pii.source_exchange_rate = float(self.conversion_rate)
	pii.received_amount = float(self.total) * float(self.conversion_rate)
	# frappe.errprint(float(self.total) * float(self.conversion_rate))
	for i in self.si_sustitucion:
		pii.append('references', {
			'reference_doctype': 'Sales Invoice',
			'reference_name': i.sales_invoice,
			'allocated_amount': float(i.valor) * float(self.conversion_rate),
		})
	pii.flags.ignore_permissions = True
	pii.flags.ignore_mandatory = True
	# pii.flags.ignore_validate = True
	pii.submit()
	frappe.msgprint('Devolucion monetaria generada : '  + '<a href="#Form/Payment Entry/' + pii.name + '"target="_blank">' + pii.name + '</a>'  )

# RG - Crear Pago
def crear_entrada(self):
	pii = frappe.new_doc("Stock Entry")
	pii.purpose = 'Material Receipt'
	for i in self.items:
		pii.append('items', {
			'item_code': i.item_code,
			'qty': i.qty,
			'uom': i.stock_uom,
			't_warehouse': i.warehouse,
		})
	pii.flags.ignore_permissions = True
	pii.submit()
	frappe.msgprint('Devolucion de Inventario generada : '  + '<a href="#Form/Stock Entry/' + pii.name + '"target="_blank">' + pii.name + '</a>'  )
