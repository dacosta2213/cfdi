# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "Cfdi",
			"category": "Modules",
			"label": _("Cfdi"),
			"color": "#1abc9c",
			"icon": "octicon octicon-file-binary",
			"type": "module",
			"disable_after_onboard": 1,
			"description": "CFDI para ERPNEXT.",
			"onboard_present": 1
		}
	]
