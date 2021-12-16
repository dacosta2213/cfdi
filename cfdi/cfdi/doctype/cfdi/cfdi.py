# -*- coding: utf-8 -*-
# Copyright (c) 2015, C0D1G0 B1NAR10 and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.file_manager import save_url
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt
import shutil
import os
import sys
import time
import base64
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from xml.dom import minidom
import requests
from datetime import datetime
import collections
import random
import string
from datetime import date
from datetime import *
import re

class CFDI(Document):
    pass

@frappe.whitelist()
def ticket(source_name, target_doc=None):
    doclist = get_mapped_doc("Sales Invoice", source_name,     {
        "Sales Invoice": {
            "doctype": "CFDI",
            "field_map": {
                "name": "ticket",
            }
        },
        "Sales Invoice Item": {
            "doctype": "CFDI Item",
            "field_map": {
                "rate": "precio_de_venta",
                "net_rate": "precio_unitario_neto",
                "amount": "monto",
                "parent": "fuente",
                "net_amount": "precio_neto",
                # "impuesto": "tax",

            }
        }

    }, target_doc)

    return doclist

# RG - Inicia SmarterWEb
@frappe.whitelist()
def validar_rfc(url, token, rfc):
	headers = {
	    'Authorization': "bearer " + token,
	    'Content-Type': "application/json"
	}
	response = requests.request("GET", url + "/lrfc/" + rfc, headers=headers)
	frappe.errprint(response.text)
	return response.text

@frappe.whitelist()
def cancel_by_uuid(url, token,docname, rfc, uuid):
    # frappe.errprint(rfc)
    c = frappe.get_doc("CFDI", docname)
    headers = {
        'Authorization': "bearer " + token,
        'Content-Type': "application/json"
    }
    response = requests.request("POST", url + "/cfdi33/cancel/" + rfc + "/" + uuid, headers=headers)

    if response.json().get('status') == 'error':
        frappe.msgprint((response.json().get('message')), "ERROR ENCONTRADO AL TIMBRAR")
    else:
        for d in c.items:
            frappe.db.set_value("Sales Invoice",d.fuente , 'cfdi_status', 'Sin Timbrar')
    return response.text

@frappe.whitelist()
def cancel_by_uuid_pago(docname):
    c = frappe.get_doc("Payment Entry", docname)
    uuid = c.uuid_pago
    d = frappe.get_doc("Configuracion CFDI", c.company)
    url = 'http://' + d.url
    token = d.token
    rfc = d.rfc_emisor

    headers = {
        'Authorization': "bearer " + token,
        'Content-Type': "application/json"
    }
    response = requests.request("POST", url + "/cfdi33/cancel/" + rfc + "/" + uuid, headers=headers)

    if response.json().get('status') == 'error':
        frappe.msgprint((response.json().get('message')), "ERROR ENCONTRADO AL TIMBRAR")
    else:
        frappe.db.set_value("Payment Entry",c.name, 'cfdi_status', 'Cancelado')
        frappe.msgprint(str(c.name) + " Cancelada exitosamente " )
    return response.text


@frappe.whitelist()
def cancel_by_uuid_egreso(url, token,docname, rfc, uuid):
    c = frappe.get_doc("CFDI Nota de Credito", docname)
    headers = {
        'Authorization': "bearer " + token,
        'Content-Type': "application/json"
    }
    response = requests.request("POST", url + "/cfdi33/cancel/" + rfc + "/" + uuid, headers=headers)

    if response.json().get('status') == 'error':
        frappe.msgprint((response.json().get('message')), "ERROR ENCONTRADO AL CANCELAR")
    else:
        frappe.db.set_value("CFDI Nota de Credito",c.name, 'cfdi_status', 'Cancelado')
        frappe.msgprint(str(c.name) + " Cancelada exitosamente " )
    return response.text

# RG - Timbrado de CFDI
@frappe.whitelist()
def issue(url, token, docname, version, b64=False):
    # RG - POST request al server de swarterweb
    xml = genera_xml(docname)
    boundary = "----=_Part_11_11939969.1490230712432"  #RG- declararlo como en issue_pago
    payload = "--" + boundary + "\r\nContent-Type: text/xml\r\nContent-Transfer-Encoding: binary\r\nContent-Disposition: " \
    "form-data; name=\"xml\"; filename=\"xml\"\r\n\r\n" + str(xml) + "\r\n--" + boundary + "-- "
    headers = {
    'Authorization': "bearer " + token,
    'Content-Type': "multipart/form-data; boundary=\"" + boundary + "\""
    }
    response = requests.request("POST", url + "/cfdi33/issue/" + version + "/" , data=payload.encode('utf-8'), headers=headers)
    liga = url + "/cfdi33/issue/" + version + "/"
    frappe.errprint(response.json()) #RG - para ver la respuesta en la consola
    frappe.errprint(payload)
    frappe.errprint(headers)
    frappe.errprint(liga)


    if response.json().get('status') == 'error': #RG - Ver si podemos manejar con una funcion separada el error
        if response.json().get('messageDetail'):
            frappe.msgprint((response.json().get('message')) + ". <b>Detalle del Error: </b>" + (response.json().get('messageDetail')), "ERROR DE SERVIDOR (PAC) ")
        else:
            frappe.msgprint((response.json().get('message')) , "ERROR DE SERVIDOR")
    else:
        # RG- Recuperar el response y manejar la info pa grabar los archivos/datos en el CFDI
        c = frappe.get_doc("CFDI", docname)
        fechaxml = str(c.creation)
        # webfolder = c.folder
        uuid = response.json().get('data').get('uuid')
        # generar xml
        cfdi_recibido = response.json().get('data').get('cfdi')
        dest = '/home/frappe/frappe-bench/sites/' + frappe.local.site + '/public/files/' + c.name  + "_" + fechaxml[0:10]
        f = open( dest + '.xml',"w+")
        f.write(cfdi_recibido)
        f.close()
        save_url( "/files/" + '/public/files/' + c.name  + "_" + fechaxml[0:10] + ".xml" , c.name  + "_" + fechaxml[0:10] + ".xml" , "CFDI" , c.name , "Home/Attachments" , 0)
        # EscribirPNG
        qr = response.json().get('data').get('qrCode')
        png = open( dest + ".png", "wb")
        png.write(base64.b64decode(qr))
        png.close()
        frappe.db.set_value("CFDI",c.name, 'qr', "/files/" + c.name  + "_" + fechaxml[0:10] +  ".png")
        # escribir todos los demas campos
        frappe.db.set_value("CFDI",c.name, 'cfdi_status', 'Timbrado')
        for d in c.items:
            frappe.db.set_value("Sales Invoice", d.fuente , 'cfdi_status', 'Timbrado')
        frappe.db.set_value("CFDI",c.name, 'SelloCFD', response.json().get('data').get('selloCFDI'))
        frappe.db.set_value("CFDI",c.name, 'cadenaOriginalSAT', response.json().get('data').get('cadenaOriginalSAT'))
        frappe.db.set_value("CFDI",c.name, 'FechaTimbrado', response.json().get('data').get('fechaTimbrado') )
        frappe.db.set_value("CFDI",c.name, 'uuid', uuid)
        frappe.db.set_value("CFDI",c.name, 'NoCertificadoSAT', response.json().get('data').get('noCertificadoSAT') )
        frappe.db.set_value("CFDI",c.name, 'SelloSAT', response.json().get('data').get('selloSAT') )
        # frappe.msgprint(str(c.name) + " Timbrada exitosamente " )
        mensaje = str(c.name)+" TIMBRADO EXITOSO . <a class= 'alert-info' href='https://" + frappe.local.site + "/files/" + c.name  + "_" + fechaxml[0:10] + ".xml' download> Descarga XML </a>"
        frappe.msgprint(mensaje)
    return response.json()


def genera_xml(docname):
  tieneiva = 0
  notieneiva = 0
  c = frappe.get_doc("CFDI", docname)
  cant = len(c.items)
  mytime = datetime.strptime('0800','%H%M').time()
  #fecha_actual = datetime.combine(c.posting_date,mytime).isoformat()[0:19] #dacosta - para hacer que se timbre con la fecha de posting_date

  fecha_actual = (datetime.now()- timedelta(minutes=480)).isoformat()[0:19]
  # fecha_actual = (datetime.now()- timedelta(minutes=360)).isoformat()[0:19]
  # fecha_obj = datetime.strptime(c.creation, "%Y-%m-%d %H:%M:%S.%f")
  # fecha_actual = fecha_obj.isoformat()[0:19]

  serie = c.naming_series.replace('-','')
  folio = c.name.replace(serie,'')
  FormaPago = c.forma_de_pago
  SubTotal = 0
  # Falta descuento
  Total = '%.2f' % c.total
  TipoDeComprobante = c.tipo_de_comprobante
  MetodoPago = c.metodo_pago
  LugarExpedicion = c.lugar_expedicion
  NoCertificado = c.no_certificado

  rfc_emisor = c.rfc_emisor
  nombre_emisor = c.nombre_emisor
  regimen_fiscal = c.regimen_fiscal

  tax_id = c.tax_id.replace('&','&amp;')
  # nombre_receptor = c.customer_name.encode('ascii', 'ignore').decode('ascii')
  # nombre_receptor = c.customer_name.encode('UTF-8', 'ignore')
  # nombre_receptor = c.customer_name.decode('UTF-8')
  nombre_receptor = c.customer_name.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ').replace('Ñ','N').replace('ñ','n').replace('Ü', 'U')

  tipo = []
  tasa = []
  cantidad = []
  cfdi_items = ""
  cfdi_traslados = ""

  for d in c.items:
      NoIdentificacion = d.item_code.replace('"','')
      ClaveProdServ = d.clave_producto
      ClaveUnidad = d.clave_unidad
      Cantidad = d.qty
      Unidad = d.stock_uom
      ValorUnitario = '%.2f' % d.precio_unitario_neto
      Importe = '%.2f' % d.precio_neto
      idx = d.idx
      Descripcion = d.item_name
      SubTotal = round(SubTotal + float(d.precio_neto), 2)

      if d.tipo_de_impuesto == "IVA":
          TrasladosBase = '%.2f' % d.precio_neto
          Impuesto = "002"
          TasaOCuota = .01 * float(d.tax)
          ImpuestosTrasladosTasaOCuota='%.6f' % TasaOCuota
          Importetax = '%.2f' % (TasaOCuota * float(d.precio_neto))
          tipo.append(Impuesto)
          tasa.append(ImpuestosTrasladosTasaOCuota)
          cantidad.append(Importetax)
      elif d.tipo_de_impuesto == "IEPS":
          TrasladosBase = '%.2f' % d.precio_neto
          Impuesto="003"
          TasaOCuota = .01 * float(d.tax)
          ImpuestosTrasladosTasaOCuota='%.6f' % TasaOCuota
          Importetax = '%.2f' % (TasaOCuota * float(d.precio_neto))
          tipo.append(Impuesto)
          tasa.append(ImpuestosTrasladosTasaOCuota)
          cantidad.append(Importetax)
      else:
          notieneiva = 1
          TrasladosBase= '%.2f' % d.precio_neto
          Impuesto="002"
          TasaOCuota="0.000000"
          Importetax= "0.00"

      cfdi_items += """
    <cfdi:Concepto ClaveProdServ="{ClaveProdServ}" NoIdentificacion="{NoIdentificacion}" Cantidad="{Cantidad}" ClaveUnidad="{ClaveUnidad}" Unidad="{Unidad}" Descripcion="{Descripcion}" ValorUnitario="{ValorUnitario}" Importe="{Importe}" Descuento="0.00">
      <cfdi:Impuestos>
        <cfdi:Traslados>
          <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="Tasa" TasaOCuota="{ImpuestosTrasladosTasaOCuota}" Importe="{Importetax}"/>
      </cfdi:Traslados>
  </cfdi:Impuestos>
</cfdi:Concepto>""".format(**locals())

  uso_cfdi = c.uso_cfdi
  cTipo = collections.Counter(tipo)
  cTasa = collections.Counter(tasa)
  total_impuesto = 0
  TotalImpuestosTrasladados = 0.0
  for w, val1 in cTipo.items():
    for y, val2 in cTasa.items():
      suma = 0.0
      for z in range(0,cant):
        if (tasa[z] == y) and (tipo[z] == w):
                    suma = suma+float(cantidad[z])
      b = y
      t = w
      total_impuesto = total_impuesto + suma
      TotalImpuestosTrasladados = round(suma,2)
      # total_impuesto = '%.2f' %  total_impuesto1
      if(suma>0):
                cfdi_traslados += """
                <cfdi:Traslado Impuesto="{t}" TipoFactor="Tasa" TasaOCuota="{b}" Importe="{TotalImpuestosTrasladados}"/>""".format(**locals())
      else:
          cfdi_traslados += """
          <cfdi:Traslado Impuesto="{t}" TipoFactor="Tasa" TasaOCuota="{b}" Importe="{suma}"/>""".format(**locals())

  Total = round(SubTotal + TotalImpuestosTrasladados, 2)
  cfdi = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd"
Version="3.3" Serie="{serie}" Folio="{folio}" Fecha="{fecha_actual}" Sello="" FormaPago="{FormaPago}" NoCertificado=""
Certificado="" CondicionesDePago="CONTADO" SubTotal="{SubTotal}" Descuento="0.00" Moneda="MXN" Total="{Total}" TipoDeComprobante="{TipoDeComprobante}" MetodoPago="{MetodoPago}" LugarExpedicion="{LugarExpedicion}">
  <cfdi:Emisor Rfc="{rfc_emisor}" Nombre="{nombre_emisor}" RegimenFiscal="{regimen_fiscal}"/>
  <cfdi:Receptor Rfc="{tax_id}" Nombre="{nombre_receptor}" UsoCFDI="{uso_cfdi}"/>
  <cfdi:Conceptos>""".format(**locals())

  cfdi += cfdi_items

  cfdi_conceptos = """
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="{TotalImpuestosTrasladados}">
      <cfdi:Traslados> """.format(**locals())
  cfdi += cfdi_conceptos
  cfdi += cfdi_traslados

  cfdi += """
  </cfdi:Traslados>
</cfdi:Impuestos>
</cfdi:Comprobante>
""".format(**locals())
  frappe.errprint(cfdi)
  return cfdi

# RG- Para los complementos de pago (REP)
@frappe.whitelist()
def issue_pago(url, token, docname, version,user_id,user_password,folder,nombre_emisor,no_certificado, b64=False):
    # RG - POST request al server de swarterweb
    xml = genera_xml_pago(docname,url,user_id,user_password,folder,nombre_emisor,no_certificado)
    frappe.errprint(xml)
    # boundary = "----=_Part_11_11939969.1490230712432"
    lst = [random.choice(string.ascii_letters + string.digits) for n in range(30)]
    boundary = "".join(lst)
    payload = "--" + boundary + "\r\nContent-Type: text/xml\r\nContent-Transfer-Encoding: binary\r\nContent-Disposition: form-data; name=\"xml\"; filename=\"xml\"\r\n\r\n" + str(xml) + "\r\n--" + boundary + "-- "
    headers = {
      'Authorization': "bearer " + token,
      'Content-Type': "multipart/form-data; boundary=\"" + boundary + "\""
    }
    response = requests.request("POST", url + "/cfdi33/issue/" + version + "/" , data=payload.encode('utf-8'), headers=headers, timeout=300)
    liga = url + "/cfdi33/issue/" + version + "/"

    if response.json().get('status') == 'error':
        if response.json().get('messageDetail'):
            frappe.msgprint((response.json().get('message')) + ". <b>Detalle del Error: </b>" + (response.json().get('messageDetail')), "ERROR DE SERVIDOR (PAC) ")
        else:
            frappe.msgprint((response.json().get('message')) , "ERROR DE SERVIDOR")
    else:
        c = frappe.get_doc("Payment Entry", docname)
        # webfolder = c.folder
        uuid = response.json().get('data').get('uuid')
        fechaxml = str(c.creation)
        # generar xml
        cfdi_recibido = response.json().get('data').get('cfdi')
        dest = '/home/frappe/frappe-bench/sites/' + frappe.local.site + '/public/files/' + c.name  + "_" + fechaxml[0:10]
        f = open( dest + '.xml',"w+")
        f.write(cfdi_recibido)
        f.close()
        save_url( "/files/" + c.name  + "_" + fechaxml[0:10] + ".xml" , c.name  + "_" + fechaxml[0:10] + ".xml" , "Payment Entry" , c.name , "Home/Attachments" , 0)
        # EscribirPNG
        qr = response.json().get('data').get('qrCode')
        png = open( dest + ".png", "wb")
        png.write(base64.b64decode(qr))
        png.close()
        frappe.db.set_value("Payment Entry",c.name, 'qr', "/files/" + c.name  + "_" + fechaxml[0:10] +  ".png")
        # escribir todos los demas campos
        frappe.db.set_value("Payment Entry",c.name, 'cfdi_status', 'Timbrado')
        frappe.db.set_value("Payment Entry",c.name, 'SelloCFD', response.json().get('data').get('selloCFDI'))
        frappe.db.set_value("Payment Entry",c.name, 'cadenaOriginalSAT', response.json().get('data').get('cadenaOriginalSAT'))
        frappe.db.set_value("Payment Entry",c.name, 'FechaTimbrado', response.json().get('data').get('fechaTimbrado') )
        frappe.db.set_value("Payment Entry",c.name, 'uuid_pago', uuid)
        frappe.db.set_value("Payment Entry",c.name, 'NoCertificadoSAT', response.json().get('data').get('noCertificadoSAT') )
        frappe.db.set_value("Payment Entry",c.name, 'SelloSAT', response.json().get('data').get('selloSAT') )
        frappe.msgprint(str(c.name) + " Timbrada exitosamente " )
    return response.json()

def genera_xml_pago(docname, url,user_id,user_password,folder,nombre_emisor,no_certificado):
    Fecha = (datetime.now()- timedelta(minutes=480)).isoformat()[0:19]
    c = frappe.get_doc("Payment Entry", docname)
    cliente = frappe.get_doc("Customer", c.party_name)

#    if frappe.local.site == "demo.totall.mx":
    Fecha = c.fecha.isoformat()[0:19] if c.fecha else (datetime.now()- timedelta(minutes=480)).isoformat()[0:19]

    #si = frappe.get_doc(tipo, invoice)

    #SerieCFDI = si.naming_series
    #FolioCFDI = si.name
    url_timbrado = url
    user_id = user_id
    user_password = user_password
    webfolder =folder
    RegimenFiscal = c.regimen_fiscal
    if c.es_factoraje == 1:
        b = frappe.get_doc("Bank", c.banco)
        RfcReceptor = b.tax_id.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ').replace('Ü', 'U')
    else:
        RfcReceptor = cliente.tax_id.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ').replace('Ü', 'U')
    #########+++++++++++++++++SE COMENTARON LOS .replace DE LAS LINEAS 382 Y 214
    if c.es_factoraje == 1:
        NombreReceptor = c.banco
    else:
        NombreReceptor = c.party_name.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ').replace('Ü', 'U')
    LugarExpedicion = c.lugar_expedicion

    mytime = datetime.strptime('1200','%H%M').time()
    FechaContabilizacion = datetime.combine(c.posting_date,mytime).isoformat()[0:19]

    Serie = c.naming_series.replace('-','')
    Folio = c.name.replace(Serie,'')
    rfc_emisor = c.rfc_emisor
    nombre_emisor = nombre_emisor
    NoCertificado = no_certificado
    FormaDePagoP = c.forma_de_pago
    Monto = '%.2f' %  c.received_amount
    IdDocumento = c.documento_relacionado

    # Currency = c.paid_from_account_currency
    #TipoCambio = 1 if c.currency == "MXN" else '%2f' % c.source_enchange_rate

    MetodoDePagoDR = c.metodo_pago_cfdi
    NumOperacion = c.reference_no
    # ImpSaldoAnt = '%.2f' % c.references[0].outstanding_amount
    ImpSaldoAnt = '%.2f' % c.impsaldoanterior
    # ImpSaldoInsoluto = '%.2f' % (c.references[0].outstanding_amount - c.received_amount )
    ImpSaldoInsoluto = '%.2f' % (c.impsaldoanterior - c.received_amount )

    cfdi_pago= """<?xml version="1.0" encoding="utf-8" ?>
    <cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:pago10="http://www.sat.gob.mx/Pagos" xsi:schemaLocation=" http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd http://www.sat.gob.mx/Pagos http://www.sat.gob.mx/sitio_internet/cfd/Pagos/Pagos10.xsd" Version="3.3"
        Serie="{Serie}" Folio="{Folio}" Fecha="{Fecha}" Sello="" NoCertificado="{NoCertificado}" Certificado="" SubTotal="0" Moneda="XXX" Total="0" TipoDeComprobante="P" LugarExpedicion="{LugarExpedicion}">
        <cfdi:Emisor Rfc="{rfc_emisor}" Nombre="{nombre_emisor}" RegimenFiscal="{RegimenFiscal}"/>
        <cfdi:Receptor Rfc="{RfcReceptor}" Nombre="{NombreReceptor}" UsoCFDI="P01"/>
        <cfdi:Conceptos>
            <cfdi:Concepto ClaveProdServ="84111506" Cantidad="1" ClaveUnidad="ACT" Descripcion="Pago" ValorUnitario="0" Importe="0">
            </cfdi:Concepto>
        </cfdi:Conceptos>
        <cfdi:Complemento>
            <pago10:Pagos Version="1.0">""".format(**locals())

    # MonedaP= c.moneda
    TipoCambioP = c.target_exchange_rate
    MonedaP = c.paid_to_account_currency
    if MonedaP != 'MXN': # Si el Pago es diferente a MXN
        cfdi_pago+="""
            <pago10:Pago FechaPago="{FechaContabilizacion}" FormaDePagoP="{FormaDePagoP}" TipoCambioP ="{TipoCambioP}"  MonedaP="{MonedaP}"  Monto="{Monto}" NumOperacion="{NumOperacion}">""".format(**locals())
    else:
        cfdi_pago+="""
            <pago10:Pago FechaPago="{FechaContabilizacion}" FormaDePagoP="{FormaDePagoP}" MonedaP="MXN" Monto="{Monto}" NumOperacion="{NumOperacion}">""".format(**locals())

    for x in c.references:
        si = frappe.get_doc('Sales Invoice', x.reference_name)
        MonedaDR = si.currency
        # if MonedaDR != MonedaP:
            # frappe.throw('Las moneda del documento original es diferente a la moneda de pago. Documento Original: ' + str(si.name))
        TipoCambioDR = None if si.currency == "MXN" else ('%2f' % si.conversion_rate)
        # TipoCambioDR = None
        IdDocumento = x.uuid
        SerieCFDI = si.naming_series
        FolioCFDI = si.name.replace(SerieCFDI,'')
        MetodoPago = si.metodo_pago
        ImpSaldoAnt = '%.2f' % x.outstanding_amount
        ImpPagado = '%.2f' % x.pagado
        parc = 0
        frappe.errprint(x.reference_name)
        parcialidades = frappe.db.sql("""SELECT * from `tabPayment Entry Reference` WHERE reference_name = %s AND docstatus = 1""",(x.reference_name),as_dict=1)
        for conteo in parcialidades:
            parc += 1
        ImpSaldoInsoluto= '%.2f' %  (float(ImpSaldoAnt) - float(ImpPagado))
        frappe.db.set_value("Sales Invoice",si.name, 'monto_pendiente', ImpSaldoInsoluto)
        frappe.errprint(IdDocumento)
        cfdi_pago+="""
            <pago10:DoctoRelacionado IdDocumento="{IdDocumento}" Serie="{SerieCFDI}" Folio="{FolioCFDI}" """.format(**locals())
        #if frappe.local.site == "demo.totall.mx": # Remover if y bloque else completo una ves comprovado el correcto funcionamiento del if - AG - 18/01/21
        if TipoCambioDR: #Solo si Factura diferente a MXN
            #frappe.msgprint('En transacciones de moneda extranjera, solo puede existir 1 factura relacionada en Referencias del Pago (Payment Reference) ')
            ImpSaldoAnt = '%.2f' % ( flt(x.outstanding_amount) / flt(TipoCambioDR) )

            if si.monto_pendiente > 1:
                ImpSaldoAnt = '%.2f' % ( si.monto_pendiente )
            # ImpPagado = '%.2f' % flt(Monto)
            # ImpSaldoInsoluto= '%.2f' %  (float(ImpSaldoAnt) - float(ImpPagado))
            if MonedaP == MonedaDR:# Si Moneda de Pago igual a Moneda de Factura - Factura y Pago USD
                ImpSaldoAnt = '%.2f' % (x.monto_pendiente)
                ImpPagado = '%.2f' % (flt(x.pagado) / flt(c.tipo_cambio))
                ImpSaldoInsoluto = '%.2f' %  (float(ImpSaldoAnt) - float(ImpPagado))
                frappe.errprint("Saldo Anterior: " + ImpSaldoAnt + "Pago: " + ImpPagado + "Saldo Nuevo: " + ImpSaldoInsoluto)
                if float(ImpSaldoInsoluto) < 0 and float(ImpPagado) > float(ImpSaldoAnt):
                    ImpSaldoInsoluto = '%.2f' %  0
                    ImpPagado = '%.2f' %  flt(ImpSaldoAnt)
                    frappe.errprint("Saldo Anterior: " + ImpSaldoAnt + "Pago: " + ImpPagado + "Saldo Nuevo: " + ImpSaldoInsoluto)
                frappe.db.set_value("Sales Invoice",si.name, 'monto_pendiente', ImpSaldoInsoluto)

                cfdi_pago+="""MonedaDR="{MonedaDR}" MetodoDePagoDR="{MetodoPago}" NumParcialidad="{parc}" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
                """.format(**locals())


            else: #Si la Moneda de Pago es Diferente a la Moneda de Factura  - Factura USD - Pago MXN

                tipocambio = round(c.tipo_cambio, 4)
                ImpPagado = round(x.pagado / tipocambio, 2)
                ImpSaldoAnt = '%.2f' % (x.monto_pendiente)

                ImpSaldoInsoluto = '%.2f' %  (float(ImpSaldoAnt) - float(ImpPagado))
                if float(ImpSaldoInsoluto) < 0 and float(ImpPagado) > float(ImpSaldoAnt):
                    ImpSaldoInsoluto = '%.2f' %  0
                    ImpPagado = '%.2f' %  flt(ImpSaldoAnt)
                    frappe.errprint("Saldo Anterior: " + ImpSaldoAnt + "Pago: " + ImpPagado + "Saldo Nuevo: " + ImpSaldoInsoluto)
                frappe.db.set_value("Sales Invoice",si.name, 'monto_pendiente', ImpSaldoInsoluto)
                cfdi_pago+="""TipoCambioDR="{tipocambio}" MonedaDR="{MonedaDR}" MetodoDePagoDR="{MetodoPago}" NumParcialidad="{parc}" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
                """.format(**locals())
        else: # Si la Factura es en MXN
            if MonedaP != "MXN": #Si el Pago es Diferente de MXN
                cfdi_pago+="""TipoCambioDR="{TipoCambioP}" MonedaDR="{MonedaDR}" MetodoDePagoDR="{MetodoPago}" NumParcialidad="{parc}" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
                """.format(**locals())
            else:
                cfdi_pago+="""MonedaDR="{MonedaDR}" MetodoDePagoDR="{MetodoPago}" NumParcialidad="{parc}" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
                """.format(**locals())
        # else:
        #     if TipoCambioDR:
        #         ImpSaldoAnt = '%.2f' % x.total_moneda_original
        #         ImpPagado = '%.2f' % x.total_moneda_original
        #         ImpSaldoInsoluto= '%.2f' %  (float(ImpSaldoAnt) - float(ImpPagado))
        #         cfdi_pago+="""MonedaDR="{MonedaDR}" MetodoDePagoDR="PPD" NumParcialidad="{no_parcialidad}" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
        #         """.format(**locals())
        #     else:
        #         cfdi_pago+="""MonedaDR="{MonedaDR}" MetodoDePagoDR="PPD" NumParcialidad="{no_parcialidad}" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
        #         """.format(**locals())

    if c.es_factoraje == 1:
        pagado_imp = round(c.total_allocated_amount -c.base_received_amount, 2)
        parc = parc + 1
        cfdi_pago+="""</pago10:Pago>
                <pago10:Pago Monto="{pagado_imp}" MonedaP="{MonedaP}" FormaDePagoP="17" FechaPago="{FechaContabilizacion}">
                    <pago10:DoctoRelacionado Serie="{SerieCFDI}" Folio="{FolioCFDI}" NumParcialidad="{parc}" MonedaDR="{MonedaP}" MetodoDePagoDR="PUE" ImpSaldoInsoluto="0.00" ImpSaldoAnt="{pagado_imp}" ImpPagado="{pagado_imp}" IdDocumento="{IdDocumento}"/>
                    """.format(**locals())

    cfdi_pago+="""</pago10:Pago>
            </pago10:Pagos>
        </cfdi:Complemento>
    </cfdi:Comprobante>""".format(**locals())

    return cfdi_pago


@frappe.whitelist()
def parcialidades_pe(doc,method=None):
#    if frappe.local.site == "demo.totall.mx":
        for item in doc.references:
            parc = 1
            # Obtiene todos los Pagos del Sinv en la lina actual
            parcialidades = frappe.get_list('Payment Entry Reference', filters={'reference_name':item.reference_name}, fields=['parent'])
            for parcialidad in parcialidades:
                pe_rel = frappe.get_doc('Payment Entry',parcialidad.parent)
                if pe_rel.fecha:
                    pago = frappe.db.get_value('Payment Entry',{'name':parcialidad.parent,'fecha':['<',doc.fecha],'docstatus':['=',1]},'posting_date')
                else:
                    pago = frappe.db.get_value('Payment Entry',{'name':parcialidad.parent,'creation':['<',doc.creation],'docstatus':['=',1]},'posting_date')

                if pago:
                    parc = parc + 1
            item.no_parcialidad = parc
            return
# MAPA DE complementos
# Num_Operacion = c.name
# FormaDePago = c.forma_de_pago
#
# PAGO10 - Iterar sobre reference
# id documento=uuid_pago
# serie y folio = reference_name
# met pago = 'PPD'
# ImpSaldoAnt=total_moneda_original
# ImpPagado=alocated_amount
# ImpSaldoInsoluto=ImpSaldoAnt - ImpPagado

# RG-Para las notas de credito CFDI
@frappe.whitelist()
def issue_egreso(url, token, docname, version, b64=False):
    # RG - POST request al server de swarterweb
    xml = genera_xml_egreso(docname)
    boundary = "----=_Part_11_11939969.1490230712432"
    payload = "--" + boundary + "\r\nContent-Type: text/xml\r\nContent-Transfer-Encoding: binary\r\nContent-Disposition: " \
    "form-data; name=\"xml\"; filename=\"xml\"\r\n\r\n" + str(xml) + "\r\n--" + boundary + "-- "
    headers = {
    'Authorization': "bearer " + token,
    'Content-Type': "multipart/form-data; boundary=\"" + boundary + "\""
    }
    response = requests.request("POST", url + "/cfdi33/issue/" + version + "/" , data=payload.encode('utf-8'), headers=headers)
    liga = url + "/cfdi33/issue/" + version + "/"
    frappe.errprint(response.json())
    frappe.errprint(payload)
    frappe.errprint(headers)
    frappe.errprint(liga)

    if response.json().get('status') == 'error':
        frappe.msgprint((response.json().get('message')), "ERROR ENCONTRADO AL TIMBRAR")
    else:
        # RG- Recuperar el response y manejar la info pa grabar los archivos/datos en el CFDI
        c = frappe.get_doc("CFDI Nota de Credito", docname)
        # webfolder = c.folder
        uuid = response.json().get('data').get('uuid')
        fechaxml = str(c.creation)
        # generar xml
        cfdi_recibido = response.json().get('data').get('cfdi')
        dest = '/home/frappe/frappe-bench/sites/' + frappe.local.site + '/public/files/' + c.name  + "_" + fechaxml[0:10]
        f = open( dest + '.xml',"w+")
        f.write(cfdi_recibido)
        f.close()
        save_url( "/files/" + c.name  + "_" + fechaxml[0:10] + ".xml" , c.name  + "_" + fechaxml[0:10] + ".xml" , "CFDI Nota de Credito" , c.name , "Home/Attachments" , 0)
        # EscribirPNG
        qr = response.json().get('data').get('qrCode')
        png = open( dest + ".png", "wb")
        png.write(base64.b64decode(qr))
        png.close()
        frappe.db.set_value("CFDI Nota de Credito",c.name, 'qr', "/files/" + c.name  + "_" + fechaxml[0:10] +  ".png")
        # escribir todos los demas campos

        frappe.db.set_value("CFDI Nota de Credito",c.name, 'cfdi_status', 'Timbrado')
        frappe.db.set_value("CFDI Nota de Credito",c.name, 'sellocfd', response.json().get('data').get('selloCFDI'))
        frappe.db.set_value("CFDI Nota de Credito",c.name, 'cadenaoriginalsat', response.json().get('data').get('cadenaOriginalSAT'))
        frappe.db.set_value("CFDI Nota de Credito",c.name, 'fechatimbrado', response.json().get('data').get('fechaTimbrado') )
        frappe.db.set_value("CFDI Nota de Credito",c.name, 'uuid', uuid)
        frappe.db.set_value("CFDI Nota de Credito",c.name, 'nocertificadosat', response.json().get('data').get('noCertificadoSAT') )
        frappe.db.set_value("CFDI Nota de Credito",c.name, 'sellosat', response.json().get('data').get('selloSAT') )

        frappe.msgprint(str(c.name) + " Timbrada exitosamente " )
    return response.json()


def genera_xml_egreso(docname):
  tieneiva = 0
  notieneiva = 0
  c = frappe.get_doc("CFDI Nota de Credito", docname)
  mytime = datetime.strptime('0800','%H%M').time()
  #fecha_actual = datetime.combine(c.posting_date,mytime).isoformat()[0:19] #dacosta - para hacer que se timbre con la fecha de posting_date

  mytime = datetime.strptime('0800','%H%M').time()
  fecha_actual = datetime.combine(c.posting_date,mytime).isoformat()[0:19] #dacosta - para hacer que se timbre con la fecha de posting_date
  serie = c.naming_series.replace('-','')
  folio = c.name.replace(serie,'')
  FormaPago = c.forma_de_pago
  SubTotal = float(c.total_neto)
  # Falta descuento
  Total = '%.2f' % (c.total)
  TipoDeComprobante = "E"
  MetodoPago = c.metodo_pago
  LugarExpedicion = c.lugar_expedicion
  NoCertificado = c.no_certificado

  rfc_emisor = c.rfc_emisor
  nombre_emisor = c.nombre_emisor.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
  regimen_fiscal = c.regimen_fiscal

  tax_id = c.tax_id.replace('&','&amp;')
  nombre_receptor = c.customer_name.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
  uso_cfdi = c.uso_cfdi

  # fac_rel = frappe.get_doc(c.tipo_documento,c.factura_fuente)
  tipo_rel = c.tipo_de_relacion
  # uuid_rel = fac_rel.uuid

  Currency = c.currency
  if Currency == 'MXN':
    TipoCambio = 1
  else:
    TipoCambio = '%.4f' % float(c.conversion_rate)

  cfdi = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd"
Version="3.3" Serie="{serie}" Folio="{folio}" Fecha="{fecha_actual}" Sello="" FormaPago="{FormaPago}" NoCertificado=""
Certificado="" CondicionesDePago="CONTADO" SubTotal="{SubTotal}" Moneda="{Currency}" TipoCambio = "{TipoCambio}" Total="{Total}" TipoDeComprobante="{TipoDeComprobante}" MetodoPago="{MetodoPago}" LugarExpedicion="{LugarExpedicion}">""".format(**locals())
  site = frappe.local.site
  # if site == "demo.totall.mx":
  cfdi+= """
  <cfdi:CfdiRelacionados TipoRelacion="{tipo_rel}">""".format(**locals())
  for d in c.si_sustitucion:
      cfdi+="""
      <cfdi:CfdiRelacionado UUID="{d.uuid}"/>""".format(**locals())
  cfdi+="""
  </cfdi:CfdiRelacionados>""".format(**locals())
  cfdi+="""
  <cfdi:Emisor Rfc="{rfc_emisor}" Nombre="{nombre_emisor}" RegimenFiscal="{regimen_fiscal}"/>
  <cfdi:Receptor Rfc="{tax_id}" Nombre="{nombre_receptor}" UsoCFDI="{uso_cfdi}"/>
  <cfdi:Conceptos>""".format(**locals())
  for d in c.items:
      NoIdentificacion = d.item_code
      ClaveProdServ = d.clave_producto
      ClaveUnidad = d.clave_unidad
      Cantidad = d.qty
      Unidad = d.stock_uom
      ValorUnitario = '%.2f' % d.precio_unitario_neto
      Importe = '%.2f' % d.precio_neto
      idx =d.idx
      Descripcion = d.item_name
      if d.tax == 16:
          tieneiva = 1
          TrasladosBase = '%.2f' % d.precio_neto
          Impuesto = "002"
          TasaOCuota = "0.160000"
          Importetax = '%.2f' % d.impuestos_totales
      else:
          notieneiva = 1
          TrasladosBase= '%.2f' % d.precio_neto
          Impuesto="002"
          TasaOCuota="0.000000"
          Importetax= "0.00"
      cfdi += """
    <cfdi:Concepto ClaveProdServ="{ClaveProdServ}" NoIdentificacion="{NoIdentificacion}" Cantidad="{Cantidad}" ClaveUnidad="{ClaveUnidad}" Unidad="{Unidad}" Descripcion="{Descripcion}" ValorUnitario="{ValorUnitario}" Importe="{Importe}">
      <cfdi:Impuestos>
        <cfdi:Traslados>
          <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="Tasa" TasaOCuota="{TasaOCuota}" Importe="{Importetax}"/>
      </cfdi:Traslados>
  </cfdi:Impuestos>
</cfdi:Concepto>""".format(**locals())
  TotalImpuestosTrasladados='%.2f' % c.total_impuestos
  TotalIva = '%.2f' % c.total_iva
  frappe.errprint(TotalIva)
  TotalIeps = '%.2f' % c.total_ieps
  cfdi += """
</cfdi:Conceptos>
<cfdi:Impuestos TotalImpuestosTrasladados="{TotalImpuestosTrasladados}">
    <cfdi:Traslados>
      """.format(**locals())
  if notieneiva == 1:
      cfdi += """ <cfdi:Traslado Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.000000" Importe="0.00"/>""".format(**locals())
  else:
      cfdi += """ <cfdi:Traslado Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="{TotalIva}"/>""".format(**locals())
  cfdi += """
  </cfdi:Traslados>
</cfdi:Impuestos>
</cfdi:Comprobante>
""".format(**locals())
  frappe.errprint(cfdi)
  return cfdi


# Dev-Aaron Timbrado Sales Invoice
@frappe.whitelist()
def sales_invoice_timbrado(url, token, docname, version, b64=False):
    # RG - POST request al server de swarterweb
    xml = sales_invoice_timbrado_xml(docname)
    frappe.errprint(xml)
    lst = [random.choice(string.ascii_letters + string.digits) for n in range(30)]
    boundary = "".join(lst)
    payload = "--" + boundary + "\r\nContent-Type: text/xml\r\nContent-Transfer-Encoding: binary\r\nContent-Disposition: " \
    "form-data; name=\"xml\"; filename=\"xml\"\r\n\r\n" + str(xml) + "\r\n--" + boundary + "-- "
    headers = {
        'Authorization': "bearer " + token,
        'Content-Type': "multipart/form-data; boundary=\"" + boundary + "\""
    }
    response = requests.request("POST", url + "/cfdi33/issue/" + version + "/" , data=payload.encode('utf-8'), headers=headers)
    liga = url + "/cfdi33/issue/" + version + "/"
    frappe.errprint(response.json())

    if response.json().get('status') == 'error':
        if response.json().get('messageDetail'):
            frappe.msgprint((response.json().get('message')) + ". <b>Detalle del Error: </b>" + (response.json().get('messageDetail')), "ERROR DE SERVIDOR (PAC) ")
        else:
            frappe.msgprint((response.json().get('message')) , "ERROR DE SERVIDOR")
    else:
        # RG- Recuperar el response y manejar la info pa grabar los archivos/datos en el CFDI
        c = frappe.get_doc("Sales Invoice", docname)
        uuid = response.json().get('data').get('uuid')
        cfdi_recibido = response.json().get('data').get('cfdi')
        fechaxml = str(c.creation)
        dest = '/home/frappe/frappe-bench/sites/' + frappe.local.site + '/public/files/' + c.name  + "_" + fechaxml[0:10]
        f = open( dest + '.xml',"w+")
        f.write(cfdi_recibido)
        f.close()
        save_url( "/files/" + c.name  + "_" + fechaxml[0:10] + ".xml" , c.name  + "_" + fechaxml[0:10] + ".xml" , "Sales Invoice" , c.name , "Home/Attachments" , 0)
        qr = response.json().get('data').get('qrCode')
        png = open( dest + ".png", "wb")
        png.write(base64.b64decode(qr))
        png.close()
        frappe.db.set_value("Sales Invoice",c.name, 'qr', "/files/" + c.name  + "_" + fechaxml[0:10] +  ".png")
        frappe.db.set_value("Sales Invoice",c.name, 'cfdi_status', 'Timbrado')
        frappe.db.set_value("Sales Invoice",c.name, 'sellocfd', response.json().get('data').get('selloCFDI'))
        frappe.db.set_value("Sales Invoice",c.name, 'cadenaoriginalsat', response.json().get('data').get('cadenaOriginalSAT'))
        frappe.db.set_value("Sales Invoice",c.name, 'fechatimbrado', response.json().get('data').get('fechaTimbrado') )
        frappe.db.set_value("Sales Invoice",c.name, 'uuid', uuid)
        frappe.db.set_value("Sales Invoice",c.name, 'nocertificadosat', response.json().get('data').get('noCertificadoSAT') )
        frappe.db.set_value("Sales Invoice",c.name, 'sellosat', response.json().get('data').get('selloSAT') )

        mensaje = "TIMBRADO EXITOSO . <a class= 'alert-info' href='https://" + frappe.local.site + "/files/" + c.name  + "_" + fechaxml[0:10] + ".xml' download> Descarga XML </a>"
        frappe.msgprint(mensaje)
        return ["TIMBRADO EXITOSO!",mensaje,uuid,xml]




def sales_invoice_timbrado_xml(docname):
    c = frappe.get_doc("Sales Invoice", docname)
    cliente = frappe.get_doc("Customer", c.customer)
    cant = len(c.items)
    company = frappe.get_doc("Configuracion CFDI", c.company)
    # horaminuto = c.posting_time
    # frappe.errprint(h oraminuto)
    # mytime = horaminuto.strftime("%H:%M:%S")
    # frappe.errprint(horaminuto)
    # return
    #fecha_actual = datetime.combine(c.posting_date,mytime).isoformat()[0:19] #dacosta - para hacer que se timbre con la fecha de posting_date
    descuento = round(c.discount_amount, 2)
    fecha_actual = (c.creation).isoformat()[0:19]
    serie = c.naming_series.replace('-','')
    folio = c.name.replace(serie,'')
    # frappe.errprint(c.name.replace(serie,''))
    FormaPago = c.forma_de_pago
    #SubTotal = '%.2f' % c.net_total
    SubTotal = 0
    Total = '%.2f' % (c.grand_total)
    # Total = 3509.40
    TipoDeComprobante = 'I'
    # TipoCambio = 1 if c.currency = "MXN" else '%2f' % c.conversion_rate
    MetodoPago = c.metodo_pago
    LugarExpedicion = company.lugar_expedicion
    Currency = c.currency
    if Currency == 'MXN':
      TipoCambio = 1
    else:
      TipoCambio = '%.4f' % c.conversion_rate
    rfc_emisor = company.rfc_emisor
    nombre_emisor = company.nombre_emisor.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
    regimen_fiscal = company.regimen_fiscal
    tax_id = cliente.tax_id.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ').replace('Ü', 'U')
    nombre_receptor = c.customer_name.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
    uso_cfdi = c.uso_cfdi

    tipo = []
    tasa = []
    cantidad = []
    cfdi_items = ""
    cfdi_traslados = ""
    cfdi_mercancias = ""
    if c.comercio_exterior == 1:
        cfdi_mercancias = """
            <cce11:Mercancias>
            """.format(**locals())
    for x in c.items:
        i = frappe.get_doc("Item", x.item_code)
        if c.comercio_exterior == 1:
            arancelaria = frappe.get_doc("Fraccion Arancelaria", i.fraccion_arancelaria)
            UMT = arancelaria.umt
        else:
            arancelaria = ""
            UMT = ""
        NoIdentificacion = x.item_code.replace('"','').replace('&','&amp;')
        ClaveProdServ = i.clave_producto
        ClaveUnidad = i.clave_unidad
        Cantidad = x.qty
        Unidad = x.stock_uom
        ValorUnitario = '%.2f' % x.rate
        Importe = '%.2f' % x.amount
        idx = x.idx
        Descripcion = x.description.replace('"','').replace('&','&amp;').replace('<div class="ql-editor read-mode"><p>','').replace('<div><p>','').replace('</p></div>','').replace('<br>','').replace('<p>','').replace('</p>','').replace('<div class=ql-editor read-mode>','').replace('@','&commat;').replace('<strong>','').replace('</strong>','')
        des = round(x.descuento*x.qty, 2)
        TrasladosBase= '%.2f' % (float(x.amount) - float(des))
        SubTotal = round(SubTotal + float(x.amount), 2)
        TasaOCuota = .01 * float(x.tasa)
        ImpuestosTrasladosTasaOCuota='%.6f' % TasaOCuota
        Importetax= '%.2f' % (TasaOCuota * (float(x.amount) - des))
        Tasa = 'Tasa'
        FraccionArancelaria = i.fraccion_arancelaria
        UnidadAduana = i.unidad_aduana
        TipoImpuesto = x.tipo_de_impuesto


        if c.comercio_exterior == 1:
            NoIdentificacion_exterior = str(NoIdentificacion) + " " + str(x.idx)
            cfdi_mercancias += """
                <cce11:Mercancia NoIdentificacion="{NoIdentificacion_exterior}" FraccionArancelaria="{FraccionArancelaria}"  CantidadAduana="{Cantidad}" UnidadAduana="{UMT}" ValorUnitarioAduana="{ValorUnitario}" ValorDolares="{Importe}"/>
                """.format(**locals())
            TipoImpuesto = "EXTERIOR"

        if TipoImpuesto == 'IVA':
            Impuesto = '002'
            tipo.append(Impuesto)
            tasa.append(ImpuestosTrasladosTasaOCuota)
            cantidad.append(Importetax)
            frappe.errprint(Importetax)
            cfdi_items += """
            <cfdi:Concepto ClaveProdServ="{ClaveProdServ}" NoIdentificacion="{NoIdentificacion}" Cantidad="{Cantidad}" ClaveUnidad="{ClaveUnidad}" Unidad="{Unidad}" Descripcion="{Descripcion}" ValorUnitario="{ValorUnitario}" Importe="{Importe}" Descuento="{des}">
                <cfdi:Impuestos>
                    <cfdi:Traslados>
                        <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="{Tasa}" TasaOCuota="{ImpuestosTrasladosTasaOCuota}" Importe="{Importetax}"/>
                    </cfdi:Traslados>
                </cfdi:Impuestos>
            </cfdi:Concepto>""".format(**locals())
        elif TipoImpuesto == "SIN IVA":
            Impuesto="002"
            tipo.append(Impuesto)
            tasa.append(ImpuestosTrasladosTasaOCuota)
            cantidad.append(Importetax)
            frappe.errprint(Importetax)
            cfdi_items += """
            <cfdi:Concepto ClaveProdServ="{ClaveProdServ}" NoIdentificacion="{NoIdentificacion}" Cantidad="{Cantidad}" ClaveUnidad="{ClaveUnidad}" Unidad="{Unidad}" Descripcion="{Descripcion}" ValorUnitario="{ValorUnitario}" Importe="{Importe}" Descuento="{des}">
                <cfdi:Impuestos>
                    <cfdi:Traslados>
                        <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="{Tasa}" TasaOCuota="{ImpuestosTrasladosTasaOCuota}" Importe="{Importetax}"/>
                    </cfdi:Traslados>
                </cfdi:Impuestos>
            </cfdi:Concepto>""".format(**locals())
        elif TipoImpuesto == "IEPS":
            Impuesto="003"
            tipo.append(Impuesto)
            tasa.append(ImpuestosTrasladosTasaOCuota)
            cantidad.append(Importetax)
            frappe.errprint(Importetax)
            cfdi_items += """
            <cfdi:Concepto ClaveProdServ="{ClaveProdServ}" NoIdentificacion="{NoIdentificacion}" Cantidad="{Cantidad}" ClaveUnidad="{ClaveUnidad}" Unidad="{Unidad}" Descripcion="{Descripcion}" ValorUnitario="{ValorUnitario}" Importe="{Importe}" Descuento="{des}">
                <cfdi:Impuestos>
                    <cfdi:Traslados>
                        <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="{Tasa}" TasaOCuota="{ImpuestosTrasladosTasaOCuota}" Importe="{Importetax}"/>
                    </cfdi:Traslados>
                </cfdi:Impuestos>
            </cfdi:Concepto>""".format(**locals())
        elif TipoImpuesto == "EXENTO":
            TrasladosBase1= x.net_amount
            TrasladosBase= '%.2f' % (TrasladosBase1)
            Impuesto="002"
            ImpuestosTrasladosTasaOCuota="0.000000"
            Importetax= "0.00"
            Tasa = 'Exento'
            tipo.append(Impuesto)
            tasa.append(ImpuestosTrasladosTasaOCuota)
            cantidad.append(Importetax)
            frappe.errprint(Importetax)
            cfdi_items += """
            <cfdi:Concepto ClaveProdServ="{ClaveProdServ}" NoIdentificacion="{NoIdentificacion}" Cantidad="{Cantidad}" ClaveUnidad="{ClaveUnidad}" Unidad="{Unidad}" Descripcion="{Descripcion}" ValorUnitario="{ValorUnitario}" Importe="{Importe}" Descuento="{des}">
                <cfdi:Impuestos>
                    <cfdi:Traslados>
                        <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="{Tasa}"/>
                    </cfdi:Traslados>
                </cfdi:Impuestos>
            </cfdi:Concepto>""".format(**locals())
        elif TipoImpuesto == "EXTERIOR":
            NoIdentificacion_exterior = str(NoIdentificacion) + " " + str(x.idx)
            cfdi_items += """
                <cfdi:Concepto ClaveProdServ="{ClaveProdServ}" NoIdentificacion="{NoIdentificacion_exterior}" Cantidad="{Cantidad}" ClaveUnidad="{ClaveUnidad}" Unidad="{Unidad}" Descripcion="{Descripcion}" ValorUnitario="{ValorUnitario}" Importe="{Importe}" Descuento="{des}">
            </cfdi:Concepto>""".format(**locals())

        # tipo.append(Impuesto)
        # tasa.append(ImpuestosTrasladosTasaOCuota)
        # cantidad.append(Importetax)
        # frappe.errprint(Importetax)
        # cfdi_items += """
        # <cfdi:Concepto ClaveProdServ="{ClaveProdServ}" NoIdentificacion="{NoIdentificacion}" Cantidad="{Cantidad}" ClaveUnidad="{ClaveUnidad}" Unidad="{Unidad}" Descripcion="{Descripcion}" ValorUnitario="{ValorUnitario}" Importe="{Importe}" Descuento="{des}">
        #     <cfdi:Impuestos>
        #         <cfdi:Traslados>
        #             <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="{Tasa}" TasaOCuota="{ImpuestosTrasladosTasaOCuota}" Importe="{Importetax}"/>
        #         </cfdi:Traslados>
        #     </cfdi:Impuestos>
        # </cfdi:Concepto>""".format(**locals())
        # # TotalImpuestosTrasladados= 4558.38

    cTipo = collections.Counter(tipo)
    cTasa = collections.Counter(tasa)
    total_impuesto = 0
    TotalImpuestosTrasladados = 0.00
    for w, val1 in cTipo.items():
        for y, val2 in cTasa.items():
            if c.comercio_exterior == 1:
                suma = "EXTERIOR"
            else:
                suma =0
            for z in range(0,cant):
                if (tasa[z] == y) and (tipo[z] == w):
                    suma1 = suma+float(cantidad[z])
                    suma = round(suma1, 2)
            b = y
            t = w
            total_impuesto = total_impuesto+suma
            TotalImpuestosTrasladados = suma

            if(suma>0):
                cfdi_traslados += """
                <cfdi:Traslado Impuesto="{t}" TipoFactor="{Tasa}" TasaOCuota="{b}" Importe="{suma}"/>""".format(**locals())
            elif(suma==0):
                cfdi_traslados += """
                <cfdi:Traslado Impuesto="{t}" TipoFactor="{Tasa}" TasaOCuota="{b}" Importe="{suma}"/>""".format(**locals())
            elif(suma=="EXTERIOR"):
                cfdi_traslados += ""
    Total = round(SubTotal - descuento + TotalImpuestosTrasladados, 2)
    cfdi = ""
    if c.comercio_exterior == 1:
        Totalant = round(SubTotal - descuento + TotalImpuestosTrasladados, 2)
        Total = '%.2f' % (Totalant)
        cfdi_comprobante = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:cce11="http://www.sat.gob.mx/ComercioExterior11" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd http://www.sat.gob.mx/ComercioExterior11 http://www.sat.gob.mx/sitio_internet/cfd/ComercioExterior11/ComercioExterior11.xsd"
Version="3.3" Serie="{serie}" Folio="{folio}" Fecha="{fecha_actual}" Sello="" FormaPago="{FormaPago}" NoCertificado=""
Certificado="" CondicionesDePago="CONTADO" SubTotal="{SubTotal}" Descuento="{descuento}" Moneda="{Currency}" TipoCambio = "{TipoCambio}" Total="{Total}" TipoDeComprobante="{TipoDeComprobante}" MetodoPago="{MetodoPago}" LugarExpedicion="{LugarExpedicion}">""".format(**locals())
    else:
        cfdi_comprobante = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd"
Version="3.3" Serie="{serie}" Folio="{folio}" Fecha="{fecha_actual}" Sello="" FormaPago="{FormaPago}" NoCertificado=""
Certificado="" CondicionesDePago="CONTADO" SubTotal="{SubTotal}" Descuento="{descuento}" Moneda="{Currency}" TipoCambio = "{TipoCambio}" Total="{Total}" TipoDeComprobante="{TipoDeComprobante}" MetodoPago="{MetodoPago}" LugarExpedicion="{LugarExpedicion}">""".format(**locals())
    cfdi += cfdi_comprobante
    #
    #es_sustitucion = frappe.get_value('Sales Invoice', docname,'sustituidos')
    # try:
    #site = frappe.local.site
    # if site == "demo.totall.mx":
    if c.cfdi_sustitucion == 1:
        relacion = c.relacion
        cfdi += """
        <cfdi:CfdiRelacionados TipoRelacion="{relacion}">""".format(**locals())
        for d in c.si_sustitucion:
            cfdi+="""
            <cfdi:CfdiRelacionado UUID="{d.uuid}"/>""".format(**locals())
        cfdi+="""
        </cfdi:CfdiRelacionados>""".format(**locals())
    # if es_sustitucion:
    # if c.sustituidos == 1:
        # frappe.errprint('si existe')
    # else:
        # frappe.errprint('no existe')


    cfdi+= """
    <cfdi:Emisor Rfc="{rfc_emisor}" Nombre="{nombre_emisor}" RegimenFiscal="{regimen_fiscal}"/>
    <cfdi:Receptor Rfc="{tax_id}" Nombre="{nombre_receptor}" UsoCFDI="{uso_cfdi}"/>
    <cfdi:Conceptos>""".format(**locals())

    cfdi += cfdi_items


    if c.comercio_exterior == 1:
         tax_id = "XAXX010101000"
         cfdi_conceptos = """
    </cfdi:Conceptos>""".format(**locals())
    else:
        cfdi_conceptos = """
   </cfdi:Conceptos>
   <cfdi:Impuestos TotalImpuestosTrasladados="{TotalImpuestosTrasladados}">
       <cfdi:Traslados>""".format(**locals())
    cfdi += cfdi_conceptos
    cfdi += cfdi_traslados
    cfdi_complemento = ""
    cfdi_emisor = ""
    cfdi_receptor = ""
    cfdi_header = """
        </cfdi:Traslados>
    </cfdi:Impuestos>
</cfdi:Comprobante>
    """.format(**locals())

    if c.comercio_exterior == 1:
        EDireccion = frappe.get_doc("Address", c.customer_address)
        ECalle = re.findall("[^0-9]+", EDireccion.address_line1)[0].replace('#', '')
        ENumeroExterior = re.findall("\d+", EDireccion.address_line1)[0]
        EColonia = EDireccion.county
        EEstado = EDireccion.clave_estado
        ECp = EDireccion.pincode
        #########################################
        #Letras del pais UNIDECODE Origen
        pais = frappe.get_doc("CFDI Clave Estado", EDireccion.clave_estado)
        EPais = pais.pais
    if c.comercio_exterior == 1:
        cfdi_complemento = """
    <cfdi:Complemento>
        <cce11:ComercioExterior Version="1.1" TipoOperacion="2" ClaveDePedimento="{c.clave_pedimento}" CertificadoOrigen="0" Incoterm="{c.incoterm}" Subdivision="0" TipoCambioUSD="{TipoCambio}" TotalUSD="{Total}" xmlns:cce11="http://www.sat.gob.mx/ComercioExterior11" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/ComercioExterior11 http://www.sat.gob.mx/sitio_internet/cfd/ComercioExterior11/ComercioExterior11.xsd">""".format(**locals())
        cfdi_emisor = """
            <cce11:Emisor>
                <cce11:Domicilio Calle="López Cotilla" NumeroExterior="13" Localidad="12" Municipio="101" Estado="JAL" Pais="MEX" CodigoPostal="{company.lugar_expedicion}"/>
            </cce11:Emisor>
            """.format(**locals())
        cfdi_receptor = """
            <cce11:Receptor>
                <cce11:Domicilio Calle="{ECalle}" NumeroExterior="{ENumeroExterior}" Colonia="{EColonia}" Estado="{EEstado}" Pais="{EPais}" CodigoPostal="{ECp}"/>
            </cce11:Receptor>
            """.format(**locals())

        cfdi_header = """
            </cce11:Mercancias>
        </cce11:ComercioExterior>
    </cfdi:Complemento>
</cfdi:Comprobante>
        """.format(**locals())
    cfdi += cfdi_complemento
    cfdi += cfdi_emisor
    cfdi += cfdi_receptor
    cfdi += cfdi_mercancias
    cfdi += cfdi_header
    frappe.errprint(cfdi)
    return cfdi

@frappe.whitelist()
def cancel_by_uuid_sales_invoice(url, token,uuid,docname, rfc):
    c = frappe.get_doc("Sales Invoice", docname)

    headers = {
        'Authorization': "bearer " + token,
        'Content-Type': "application/json"
    }
    response = requests.request("POST", url + "/cfdi33/cancel/" + rfc + "/" + uuid, headers=headers)

    if response.json().get('status') == 'error':
        if response.json().get('messageDetail'):
            frappe.msgprint((response.json().get('message')) + ". <b>Detalle del Error: </b>" + (response.json().get('messageDetail')), "ERROR DE SERVIDOR (PAC) ")
        else:
            frappe.msgprint((response.json().get('message')) , "ERROR DE SERVIDOR")
    else:
        frappe.db.set_value("Sales Invoice", c.name, 'cfdi_status','Cancelado')
        frappe.msgprint(str(c.name)+ " Cancelada Exitosamente")
    return response.text


#############################################
#Comienza Carta Porte
@frappe.whitelist()
def carta_porte_timbrado(url, token, docname, version, b64=False):
    # RG - POST request al server de swarterweb
    xml = carta_porte_timbrado_xml(docname)
    frappe.errprint(xml)
    lst = [random.choice(string.ascii_letters + string.digits) for n in range(30)]
    boundary = "".join(lst)
    payload = "--" + boundary + "\r\nContent-Type: text/xml\r\nContent-Transfer-Encoding: binary\r\nContent-Disposition: " \
    "form-data; name=\"xml\"; filename=\"xml\"\r\n\r\n" + str(xml) + "\r\n--" + boundary + "-- "
    headers = {
        'Authorization': "bearer " + token,
        'Content-Type': "multipart/form-data; boundary=\"" + boundary + "\""
    }
    response = requests.request("POST", url + "/cfdi33/issue/" + version + "/" , data=payload.encode('utf-8'), headers=headers)
    liga = url + "/cfdi33/issue/" + version + "/"
    frappe.errprint(response.json())

    if response.json().get('status') == 'error':
        if response.json().get('messageDetail'):
            frappe.msgprint((response.json().get('message')) + ". <b>Detalle del Error: </b>" + (response.json().get('messageDetail')), "ERROR DE SERVIDOR (PAC) ")
        else:
            frappe.msgprint((response.json().get('message')) , "ERROR DE SERVIDOR")
    else:
        # RG- Recuperar el response y manejar la info pa grabar los archivos/datos en el CFDI
        c = frappe.get_doc("Delivery Trip", docname)
        uuid = response.json().get('data').get('uuid')
        cfdi_recibido = response.json().get('data').get('cfdi')
        fechaxml = str(c.creation)
        dest = '/home/frappe/frappe-bench/sites/' + frappe.local.site + '/public/files/' + c.name  + "_" + fechaxml[0:10]
        f = open( dest + '.xml',"w+")
        f.write(cfdi_recibido)
        f.close()
        save_url( "/files/" + c.name  + "_" + fechaxml[0:10] + ".xml" , c.name  + "_" + fechaxml[0:10] + ".xml" , "Delivery Trip" , c.name , "Home/Attachments" , 0)
        qr = response.json().get('data').get('qrCode')
        png = open( dest + ".png", "wb")
        png.write(base64.b64decode(qr))
        png.close()
        frappe.db.set_value("Delivery Trip",c.name, 'qr', "/files/" + c.name  + "_" + fechaxml[0:10] +  ".png")
        frappe.db.set_value("Delivery Trip",c.name, 'cfdi_status', 'Timbrado')
        frappe.db.set_value("Delivery Trip",c.name, 'sellocfd', response.json().get('data').get('selloCFDI'))
        frappe.db.set_value("Delivery Trip",c.name, 'cadenaoriginalsat', response.json().get('data').get('cadenaOriginalSAT'))
        frappe.db.set_value("Delivery Trip",c.name, 'fechatimbrado', response.json().get('data').get('fechaTimbrado') )
        frappe.db.set_value("Delivery Trip",c.name, 'uuid', uuid)
        frappe.db.set_value("Delivery Trip",c.name, 'nocertificadosat', response.json().get('data').get('noCertificadoSAT') )
        frappe.db.set_value("Delivery Trip",c.name, 'sellosat', response.json().get('data').get('selloSAT') )

        mensaje = "TIMBRADO EXITOSO . <a class= 'alert-info' href='https://" + frappe.local.site + "/files/" + uuid + ".xml' download> Descarga XML </a>"
        frappe.msgprint(mensaje)
        return ["TIMBRADO EXITOSO!",mensaje,uuid,xml]




def carta_porte_timbrado_xml(docname):
    c = frappe.get_doc("Delivery Trip", docname)
    TranspInternac = ""
    if c.transporte_internacional == 1:
        TranspInternac = 'Si'
    else:
        TranspInternac = 'No'


    company = frappe.get_doc("Configuracion CFDI", c.company)
    fecha_actual = (c.creation).isoformat()[0:19]
    fecha_salida = (c.departure_time).isoformat()[0:19]
    serie = c.naming_series.replace('-','')
    folio = c.name.replace(serie,'')
    FormaPago = c.forma_de_pago
    if c.tipo_de_comprobante == "I":
        SubTotal = '%.2f' % c.precio_traslado
        Total = round(c.precio_traslado * 1.16, 2)
    else:
        SubTotal = 0
        Total = 0

    TipoDeComprobante = c.tipo_de_comprobante
    MetodoPago = c.metodo_de_pago
    LugarExpedicion = company.lugar_expedicion
    Currency = c.currency
    if Currency == 'MXN':
        TipoCambio = 1
    else:
        TipoCambio = '%.4f' % c.conversion_rate
    rfc_emisor = company.rfc_emisor
    nombre_emisor = company.nombre_emisor.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
    regimen_fiscal = company.regimen_fiscal
    uso_cfdi = c.uso_cfdi


	##########################################
	#Datos de Direccion de Origen

    ODireccion = frappe.get_doc("Address", c.driver_address)
    OCalle = re.findall("[^0-9]+", ODireccion.address_line1)[0].replace('#', '')
    ONumeroExterior = re.findall("\d+", ODireccion.address_line1)[0]
	#########################################
	#Letras del pais UNIDECODE Origen
    OClave_estado = ODireccion.clave_estado
    InfOClave_estado = frappe.get_doc("CFDI Clave Estado", OClave_estado)
    OPais = InfOClave_estado.pais
    articulo_claveDT = c.unidad_pesocp
    suma_distancia = 0
    ##########################################
	#Datos de Direccion de destinatario
    for dest in c.delivery_stops:
        UCliente = dest.customer
        cliente = frappe.get_doc("Customer", UCliente)
        nombre_receptor = UCliente.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
        tax_id = cliente.tax_id.replace('&','&amp;').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ').replace('Ü', 'U')
        rfc_receptor = cliente.tax_id
        Fecha_llegada = (dest.estimated_arrival).isoformat()[0:19]
        UDireccion = frappe.get_doc("Address", dest.address)
        UCalle = re.findall("[^0-9]+", UDireccion.address_line1)[0].replace('#', '')
        UNumeroExterior = re.findall("\d+", UDireccion.address_line1)[0]
		#########################################
		#Letras del pais UNIDECODE Origen
        UClave_estado = UDireccion.clave_estado
        InfUClave_estado = frappe.get_doc("CFDI Clave Estado", UClave_estado)
        UPais = InfUClave_estado.pais
        UCodigo_postal = UDireccion.pincode
		##########################################

        distancia = round(dest.distance, 2)
        suma_distancia += round(distancia, 2)
		##########################################
		#Obtener informacion de Notra de Entrega
        DN = frappe.get_doc("Delivery Note", dest.delivery_note)
        cant = len(DN.items)

        PesoBrutoTotal = DN.total_net_weight
        cfdi_ubicacion_destino = """
            <cartaporte20:Ubicacion TipoUbicacion="Destino" RFCRemitenteDestinatario="{rfc_receptor}" FechaHoraSalidaLlegada="{Fecha_llegada}" DistanciaRecorrida="{distancia}">
               <cartaporte20:Domicilio Calle="{UCalle}" NumeroExterior="{UNumeroExterior}" Estado="{UClave_estado}" Pais="{UPais}" CodigoPostal="{UCodigo_postal}" />
            </cartaporte20:Ubicacion>
        """.format(**locals())

		##########################################
		#Obtener informacion de articulos en Notra de Entrega
        tipo = []
        tasa = []
        cantidad = []
        cfdi_items = ""
        cfdi_traslados = ""
        for articulos_nota in DN.items:
            articulo_qty = articulos_nota.qty
            articulo_peso = articulos_nota.total_weight
            row = str(articulos_nota.idx)
            NumTotalMercancias = len(row)
			##########################################
			#Obtener informacion del articulo en general
            informacion_articulo = frappe.get_doc("Item", articulos_nota.item_code)
            articulo_cps = informacion_articulo.clave_producto
            articulo_cu = informacion_articulo.clave_unidad
            articulo_claveUP = informacion_articulo.unidad_pesocp
            material_peligroso = informacion_articulo.material_peligroso
            articulo_descripcion = informacion_articulo.description
            articulos_mercancias_header = """   </cartaporte20:Ubicaciones>
            <cartaporte20:Mercancias PesoBrutoTotal="{PesoBrutoTotal}" UnidadPeso="{articulo_claveDT}" NumTotalMercancias="{NumTotalMercancias}" >""".format(**locals())
            articulos_mercancias = """
                <cartaporte20:Mercancia BienesTransp="{articulo_cps}" Descripcion="{articulo_descripcion}" Cantidad="{articulo_qty}" ClaveUnidad="{articulo_claveUP}" PesoEnKg="{articulo_peso}">
                </cartaporte20:Mercancia>""".format(**locals())

            NoIdentificacion = articulos_nota.item_code.replace('"','').replace('&','&amp;')
            ClaveProdServ = informacion_articulo.clave_producto
            ClaveUnidad = informacion_articulo.clave_unidad
            Cantidad = articulos_nota.qty
            Unidad = articulos_nota.stock_uom
            ValorUnitario = '%.2f' % c.precio_traslado
            Importe = '%.2f' % c.precio_traslado
            idx = articulos_nota.idx
            Descripcion = articulos_nota.item_name.replace('"','').replace('&','&amp;')
            TrasladosBase= '%.2f' % c.precio_traslado
            TasaOCuota = .01 * float(informacion_articulo.tasa)
            ImpuestosTrasladosTasaOCuota='%.6f' % TasaOCuota
            Importetax= '%.2f' % (TasaOCuota * (float(c.precio_traslado)))
            Tasa = 'Tasa'

            if informacion_articulo.tipo_de_impuesto == 'IVA':
                Impuesto = '002'
                tipo.append(Impuesto)
                tasa.append(ImpuestosTrasladosTasaOCuota)
                cantidad.append(Importetax)
                frappe.errprint(Importetax)
                cfdi_items += """
        <cfdi:Concepto ClaveProdServ="78101800" NoIdentificacion="01" Cantidad="1" ClaveUnidad="E48" Unidad="SERVICIO" Descripcion="FLETE" ValorUnitario="{ValorUnitario}" Importe="{Importe}">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="{Tasa}" TasaOCuota="{ImpuestosTrasladosTasaOCuota}" Importe="{Importetax}"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>""".format(**locals())
            elif informacion_articulo.tipo_de_impuesto == "SIN IVA":
                Impuesto="002"
                tipo.append(Impuesto)
                tasa.append(ImpuestosTrasladosTasaOCuota)
                cantidad.append(Importetax)
                frappe.errprint(Importetax)
                cfdi_items += """
        <cfdi:Concepto ClaveProdServ="78101800" NoIdentificacion="01" Cantidad="1" ClaveUnidad="E48" Unidad="SERVICIO" Descripcion="FLETE" ValorUnitario="{ValorUnitario}" Importe="{Importe}">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="{Tasa}" TasaOCuota="{ImpuestosTrasladosTasaOCuota}" Importe="{Importetax}"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>""".format(**locals())
            elif informacion_articulo.tipo_de_impuesto == "IEPS":
                Impuesto="003"
                tipo.append(Impuesto)
                tasa.append(ImpuestosTrasladosTasaOCuota)
                cantidad.append(Importetax)
                frappe.errprint(Importetax)
                cfdi_items += """
        <cfdi:Concepto ClaveProdServ="78101800" NoIdentificacion="01" Cantidad="1" ClaveUnidad="E48" Unidad="SERVICIO" Descripcion="FLETE" ValorUnitario="{ValorUnitario}" Importe="{Importe}">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="{Tasa}" TasaOCuota="{ImpuestosTrasladosTasaOCuota}" Importe="{Importetax}"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>""".format(**locals())
            elif informacion_articulo.tipo_de_impuesto == "EXENTO":
                TrasladosBase1= articulos_nota.net_amount
                TrasladosBase= '%.2f' % (TrasladosBase1)
                Impuesto="002"
                ImpuestosTrasladosTasaOCuota="0.000000"
                Importetax= "0.00"
                Tasa = 'Exento'
                tipo.append(Impuesto)
                tasa.append(ImpuestosTrasladosTasaOCuota)
                cantidad.append(Importetax)
                frappe.errprint(Importetax)
                cfdi_items += """
        <cfdi:Concepto ClaveProdServ="78101800" NoIdentificacion="01" Cantidad="1" ClaveUnidad="E48" Unidad="SERVICIO" Descripcion="FLETE" ValorUnitario="{ValorUnitario}" Importe="{Importe}">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="{Tasa}"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>""".format(**locals())

        cTipo = collections.Counter(tipo)
        cTasa = collections.Counter(tasa)
        total_impuesto = 0
        TotalImpuestosTrasladados = 0.00
        for w, val1 in cTipo.items():
            for y, val2 in cTasa.items():
                suma =0
                for z in range(0,cant):
                    if (tasa[z] == y) and (tipo[z] == w):
                        suma1 = suma+float(cantidad[z])
                        suma = round(suma1, 2)
                b = y
                t = w
                total_impuesto = total_impuesto+suma
                TotalImpuestosTrasladados = suma

                if(suma>0):
                    cfdi_traslados += """
                <cfdi:Traslado Impuesto="{t}" TipoFactor="{Tasa}" TasaOCuota="{b}" Importe="{suma}"/>""".format(**locals())
                else:
                    cfdi_traslados += """
                <cfdi:Traslado Impuesto="{t}" TipoFactor="{Tasa}" TasaOCuota="{b}" Importe="{suma}"/>""".format(**locals())

#        Total = round(SubTotal + TotalImpuestosTrasladados, 2)
	##########################################
	#Si es auto transporte AutotransporteFederal
    if c.via == '01':
		#Obtener datos de Vehiculo
        vehicle = frappe.get_doc("Vehicle", c.vehicle)
        PermSCT = vehicle.tipo_permiso
        NumPermisoSCT = vehicle.numero_permiso
        NombreAseg = vehicle.insurance_company
        NumPolizaSeguro = vehicle.policy_no
        ConfigVehicular = vehicle.configuracion_vehicular
        AnioModeloVM = vehicle.model
        PlacaVM = c.vehicle.replace("-","")
	##########################################
	#Obtener datos de Operador
    operador = frappe.get_doc("Driver", c.driver)
    RFCOperador = operador.rfc
    NumLicencia = operador.license_number
    NombreOperador = operador.full_name
	#Obtener datos de Direccion de Operador
    DO = frappe.get_doc("Address", c.driver_address)
    DOCalle = re.findall("[^0-9]+", DO.address_line1)[0].replace('#', '')
    DONumeroExterior = re.findall("\d+", DO.address_line1)[0]
	#########################################
	#Letras del pais UNIDECODE Origen
    InfDOClave_estado = frappe.get_doc("CFDI Clave Estado", UClave_estado)
    DOPais = InfDOClave_estado.pais
    DOClave_estado = DO.clave_estado
    DOCodigo_postal = DO.pincode

    if c.tipo_de_comprobante == "I":
        cfdi = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd http://www.sat.gob.mx/CartaPorte20 http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte20.xsd"
    xmlns:cartaporte20="http://www.sat.gob.mx/CartaPorte20" Version="3.3" Serie="{serie}" Folio="{folio}" Fecha="{fecha_actual}" Sello="" FormaPago="{FormaPago}" NoCertificado=""
    xmlns:cfdi="http://www.sat.gob.mx/cfd/3"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Certificado="" CondicionesDePago="CONTADO" SubTotal="{SubTotal}" Moneda="{Currency}" TipoCambio = "{TipoCambio}" Total="{Total}" TipoDeComprobante="{TipoDeComprobante}" MetodoPago="{MetodoPago}" LugarExpedicion="{LugarExpedicion}">""".format(**locals())
    else:
        cfdi = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd http://www.sat.gob.mx/CartaPorte20 http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte20.xsd"
    xmlns:cartaporte20="http://www.sat.gob.mx/CartaPorte20" Version="3.3" Serie="{serie}" Folio="{folio}" Fecha="{fecha_actual}" Sello="" NoCertificado=""
    xmlns:cfdi="http://www.sat.gob.mx/cfd/3"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Certificado="" SubTotal="{SubTotal}" Moneda="XXX" Total="{Total}" TipoDeComprobante="{TipoDeComprobante}" LugarExpedicion="{LugarExpedicion}">""".format(**locals())

    cfdi+= """
    <cfdi:Emisor Rfc="{rfc_emisor}" Nombre="{nombre_emisor}" RegimenFiscal="{regimen_fiscal}"/>
    <cfdi:Receptor Rfc="{tax_id}" Nombre="{nombre_receptor}" UsoCFDI="{uso_cfdi}"/>
    <cfdi:Conceptos>""".format(**locals())

    if c.tipo_de_comprobante == "I":
        cfdi += cfdi_items
    else:
        cfdi += """
        <cfdi:Concepto ClaveProdServ="78101800" NoIdentificacion="01" Cantidad="1" ClaveUnidad="E48" Unidad="SERVICIO" Descripcion="FLETE" ValorUnitario="{ValorUnitario}" Importe="{Importe}" />
    </cfdi:Conceptos>
        """.format(**locals())

    cfdi_conceptos = """
    </cfdi:Conceptos>
    <cfdi:Impuestos TotalImpuestosTrasladados="{TotalImpuestosTrasladados}">
        <cfdi:Traslados>""".format(**locals())
    if c.tipo_de_comprobante == "I":
        cfdi += cfdi_conceptos
        cfdi += cfdi_traslados
        cfdi += """
        </cfdi:Traslados>
    </cfdi:Impuestos>
    """.format(**locals())

    cfdi_carta_porte = """<cfdi:Complemento>
        <cartaporte20:CartaPorte Version="2.0" TranspInternac="{TranspInternac}" TotalDistRec="{suma_distancia}">
            <cartaporte20:Ubicaciones>""".format(**locals())

    cfdi_ubicacion_origen = """
            <cartaporte20:Ubicacion TipoUbicacion="Origen" RFCRemitenteDestinatario="{rfc_emisor}" FechaHoraSalidaLlegada="{fecha_salida}">
                <cartaporte20:Domicilio Calle="{DOCalle}" NumeroExterior="{DONumeroExterior}" Estado="{DOClave_estado}" Pais="MEX" CodigoPostal="{DOCodigo_postal}" />
            </cartaporte20:Ubicacion>""".format(**locals())

    cfdi_autotransporte = """
                <cartaporte20:Autotransporte PermSCT="{PermSCT}" NumPermisoSCT="{NumPermisoSCT}">
                    <cartaporte20:IdentificacionVehicular ConfigVehicular="{ConfigVehicular}" PlacaVM="{PlacaVM}" AnioModeloVM="{AnioModeloVM}" />
                    <cartaporte20:Seguros AseguraRespCivil="{NombreAseg}" PolizaRespCivil="{NumPolizaSeguro}"/>
                </cartaporte20:Autotransporte>
            </cartaporte20:Mercancias>
        """.format(**locals())
    cfdi_figura_transporte = """    <cartaporte20:FiguraTransporte>
                <cartaporte20:TiposFigura TipoFigura="01" RFCFigura="VAAM130719H60" NumLicencia="a234567890">
                </cartaporte20:TiposFigura>
            </cartaporte20:FiguraTransporte>
        </cartaporte20:CartaPorte>
    </cfdi:Complemento>
</cfdi:Comprobante>""".format(**locals())

    cfdi += cfdi_carta_porte
    cfdi += cfdi_ubicacion_origen
    cfdi += cfdi_ubicacion_destino
    cfdi += articulos_mercancias_header
    cfdi += articulos_mercancias
    cfdi += cfdi_autotransporte
    cfdi += cfdi_figura_transporte
    frappe.errprint(cfdi)
    return cfdi

@frappe.whitelist()
def cancel_by_uuid_carta_porte(url, token,uuid,docname, rfc):
    c = frappe.get_doc("Delivery Trip", docname)

    headers = {
        'Authorization': "bearer " + token,
        'Content-Type': "application/json"
    }
    response = requests.request("POST", url + "/cfdi33/cancel/" + rfc + "/" + uuid, headers=headers)

    if response.json().get('status') == 'error':
        if response.json().get('messageDetail'):
            frappe.msgprint((response.json().get('message')) + ". <b>Detalle del Error: </b>" + (response.json().get('messageDetail')), "ERROR DE SERVIDOR (PAC) ")
        else:
            frappe.msgprint((response.json().get('message')) , "ERROR DE SERVIDOR")
    else:
        frappe.db.set_value("Delivery Trip", c.name, 'cfdi_status','Cancelado')
        frappe.msgprint(str(c.name)+ " Cancelada Exitosamente")
    return response.text
