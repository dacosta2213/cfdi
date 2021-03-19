# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "cfdi"
app_title = "Cfdi"
app_publisher = "CODIGO BINARIO"
app_description = "CFDI for Frappe"
app_icon = " 'octicon octicon-file-binary'"
app_color = " 'octicon octicon-file-binary' , icon color: #2488ee"
app_email = "soporte@posix.mx"
app_license = "MIT"

# RG- 24-Jul-2019 - Quite Print Format (son nativos), Translation y UOM porque nomas chocaban con las instalaciones de los clientes
fixtures = [
    # "CFDI Clave Producto",
    # "CFDI Regimen Fiscal",
    # "CFDI Uso",
    # "Configuracion CFDI",
    # "CFDI Metodo Pago",
    # "CFDI Tipo De Comprobante",
    # "CFDI Forma de Pago",
    # "CFDI Clave Unidad",
    # "CFDI Relacion Documentos",
    # Para mover todos los cambios de una instancia a otra
    # {"dt":"Custom Field", "filters": [["dt", "in", ("Sales Invoice", "Sales Invoice Item","Item","User", "Customer", "Address","Payment Entry","Payment Entry Reference")]]},
    # {"dt":"Property Setter", "filters": [["doc_type", "in", ("Customize Form Field","Opportunity","Sales Invoice", "Sales Invoice Item", "Item","User", "Customer", "Address","Payment Entry Reference")]]},
    # Solo cambios que impacten payment entry
    {"dt":"Custom Field", "filters": [ ["dt", "in", ("Sales Invoice","CFDI Nota de Credito","Payment Entry","Payment Entry Reference")] ]},
    {"dt":"Property Setter", "filters": [["doc_type", "in", ("Sales Invoice","CFDI Nota de Credito","Payment Entry","Payment Entry Reference")] ]},
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/cfdi/css/cfdi.css"
# app_include_js = "/assets/cfdi/js/cfdi.js"

# include js, css files in header of web template
# web_include_css = "/assets/cfdi/css/cfdi.css"
# web_include_js = "/assets/cfdi/js/cfdi.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Sales Invoice" : "public/js/cfdi_sales_invoice.js",
    "Payment Entry" : "public/js/payment_entry_client.js",
    "CFDI Nota de Credito" : "public/js/cfdi_nota_de_credito.js"
    }
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "cfdi.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "cfdi.install.before_install"
# after_install = "cfdi.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "cfdi.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Payment Entry": {
		"on_update": "cfdi.cfdi.doctype.cfdi.cfdi.parcialidades_pe"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"cfdi.tasks.all"
# 	],
# 	"daily": [
# 		"cfdi.tasks.daily"
# 	],
# 	"hourly": [
# 		"cfdi.tasks.hourly"
# 	],
# 	"weekly": [
# 		"cfdi.tasks.weekly"
# 	]
# 	"monthly": [
# 		"cfdi.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "cfdi.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "cfdi.event.get_events"
# }
