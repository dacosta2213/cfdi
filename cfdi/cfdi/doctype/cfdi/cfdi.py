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
    d = frappe.get_doc("Configuracion CFDI", 'Cliente')
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
        # webfolder = c.folder
        uuid = response.json().get('data').get('uuid')
        # generar xml
        cfdi_recibido = response.json().get('data').get('cfdi')
        dest = '/home/frappe/frappe-bench/sites/' + frappe.local.site + '/public/files/' + uuid
        f = open( dest + '.xml',"w+")
        f.write(cfdi_recibido)
        f.close()
        save_url( "/files/" + uuid +  ".xml" , uuid + ".xml" , "CFDI" , c.name , "Home/Attachments" , 0)
        # EscribirPNG
        qr = response.json().get('data').get('qrCode')
        png = open( dest + ".png", "wb")
        png.write(base64.b64decode(qr))
        png.close()
        frappe.db.set_value("CFDI",c.name, 'qr', "/files/" + uuid +  ".png")
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
        mensaje = str(c.name)+" TIMBRADO EXITOSO . <a class= 'alert-info' href='https://" + frappe.local.site + "/files/" + uuid + ".xml' download> Descarga XML </a>"
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
  SubTotal = float(c.total)
  # Falta descuento
  descuento = float(c.discount_amount)
  Total = '%.2f' % (c.grand_total)
  TipoDeComprobante = c.tipo_de_comprobante
  MetodoPago = c.metodo_pago
  LugarExpedicion = c.lugar_expedicion
  NoCertificado = c.no_certificado

  rfc_emisor = c.rfc_emisor

  nombre_emisor = c.nombre_emisor.replace('&','Y').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
  regimen_fiscal = c.regimen_fiscal

  tax_id = c.tax_id.replace('&','&amp;')
  # nombre_receptor = c.customer_name.encode('ascii', 'ignore').decode('ascii')
  # nombre_receptor = c.customer_name.encode('UTF-8', 'ignore')
  # nombre_receptor = c.customer_name.decode('UTF-8')
  nombre_receptor = c.customer_name#.replace('&','Y').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('Á','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('Ü'.'u').replace('ü','u').replace('@',' ')
  uso_cfdi = c.uso_cfdi

  tipo = []
  tasa = []
  cantidad = []
  cfdi_items = ""
  cfdi_traslados = ""

  for d in c.items:
      NoIdentificacion = d.item_code
      ClaveProdServ = d.clave_producto
      ClaveUnidad = d.clave_unidad
      Cantidad = d.qty
      Unidad = d.stock_uom
      ValorUnitario = '%.2f' % d.precio_unitario_neto
      Importe = '%.2f' % d.precio_neto
      idx = d.idx
      Descripcion = d.item_name

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
    <cfdi:Concepto ClaveProdServ="{ClaveProdServ}" NoIdentificacion="{NoIdentificacion}" Cantidad="{Cantidad}" ClaveUnidad="{ClaveUnidad}" Unidad="{Unidad}" Descripcion="{Descripcion}" ValorUnitario="{ValorUnitario}" Importe="{Importe}">
      <cfdi:Impuestos>
        <cfdi:Traslados>
          <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="Tasa" TasaOCuota="{ImpuestosTrasladosTasaOCuota}" Importe="{Importetax}"/>
      </cfdi:Traslados>
  </cfdi:Impuestos>
</cfdi:Concepto>""".format(**locals())

  TotalImpuestosTrasladados='%.2f' % c.total_impuestos

  cTipo = collections.Counter(tipo)
  cTasa = collections.Counter(tasa)
  total_impuesto = 0
  for w, val1 in cTipo.items():
    for y, val2 in cTasa.items():
      suma =0
      for z in range(0,cant):
        if (tasa[z] == y) and (tipo[z] == w):
                    suma = suma+float(cantidad[z])
      b = y
      t = w
      total_impuesto = total_impuesto + suma
      if(suma>0):
                cfdi_traslados += """
                <cfdi:Traslado Impuesto="{t}" TipoFactor="Tasa" TasaOCuota="{b}" Importe="{suma}"/>""".format(**locals())
      else:
          cfdi_traslados += """
          <cfdi:Traslado Impuesto="{t}" TipoFactor="Tasa" TasaOCuota="{b}" Importe="{suma}"/>""".format(**locals())

  Total = float(SubTotal) + float(total_impuesto)
  cfdi = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd"
Version="3.3" Serie="{serie}" Folio="{folio}" Fecha="{fecha_actual}" Sello="" FormaPago="{FormaPago}" NoCertificado=""
Certificado="" CondicionesDePago="CONTADO" SubTotal="{SubTotal}" Descuento="{descuento}" Moneda="MXN" Total="{Total}" TipoDeComprobante="{TipoDeComprobante}" MetodoPago="{MetodoPago}" LugarExpedicion="{LugarExpedicion}">
  <cfdi:Emisor Rfc="{rfc_emisor}" Nombre="{nombre_emisor}" RegimenFiscal="{regimen_fiscal}"/>
  <cfdi:Receptor Rfc="{tax_id}" Nombre="{nombre_receptor}" UsoCFDI="{uso_cfdi}"/>
  <cfdi:Conceptos>""".format(**locals())

  cfdi += cfdi_items

  cfdi_conceptos = """
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="{total_impuesto}">
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
        # generar xml
        cfdi_recibido = response.json().get('data').get('cfdi')
        dest = '/home/frappe/frappe-bench/sites/' + frappe.local.site + '/public/files/' + uuid
        f = open( dest + '.xml',"w+")
        f.write(cfdi_recibido)
        f.close()
        save_url( "/files/" + uuid +  ".xml" , uuid + ".xml" , "Payment Entry" , c.name , "Home/Attachments" , 0)
        # EscribirPNG
        qr = response.json().get('data').get('qrCode')
        png = open( dest + ".png", "wb")
        png.write(base64.b64decode(qr))
        png.close()
        frappe.db.set_value("Payment Entry",c.name, 'qr', "/files/" + uuid +  ".png")
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
    RfcReceptor = c.tax_id.replace('&','&amp;')
    #########+++++++++++++++++SE COMENTARON LOS .replace DE LAS LINEAS 382 Y 214
    NombreReceptor = c.party_name#.replace('&','Y').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('Á','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('Ü'.'u').replace('ü','u').replace('@',' ')
    LugarExpedicion = c.lugar_expedicion
    now = datetime.now()
    mytime = now.strftime('%H%M')
    FechaContabilizacion = datetime.combine(c.posting_date,mytime).isoformat()[0:19]

    Serie = c.naming_series.replace('-','')
    Folio = c.name.replace(Serie,'')
    rfc_emisor = c.rfc_emisor
    nombre_emisor = nombre_emisor.replace('&','Y').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
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
            <cfdi:Concepto ClaveProdServ="84111506" Cantidad="1" ClaveUnidad="ACT" Descripcion="Pago" ValorUnitario="0" Importe="0.00">
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
        SerieCFDI = x.reference_name
        FolioCFDI = x.reference_name
        MetodoPago = si.metodo_pago
        ImpSaldoAnt = '%.2f' % x.outstanding_amount
        ImpPagado = '%.2f' % x.allocated_amount
        no_parcialidad = x.no_parcialidad if x.no_parcialidad else 1
        ImpSaldoInsoluto= '%.2f' %  (float(ImpSaldoAnt) - float(ImpPagado))
        frappe.errprint(IdDocumento)
        cfdi_pago+="""
            <pago10:DoctoRelacionado IdDocumento="{IdDocumento}" Serie="{SerieCFDI}" Folio="{FolioCFDI}" """.format(**locals())
        if frappe.local.site == "demo.totall.mx": # Remover if y bloque else completo una ves comprovado el correcto funcionamiento del if - AG - 18/01/21
            if TipoCambioDR: #Solo si Factura diferente a MXN
                frappe.msgprint('En transacciones de moneda extranjera, solo puede existir 1 factura relacionada en Referencias del Pago (Payment Reference) ')
                ImpSaldoAnt = '%.2f' % ( flt(x.outstanding_amount) / flt(TipoCambioDR) )
                # ImpPagado = '%.2f' % flt(Monto)
                # ImpSaldoInsoluto= '%.2f' %  (float(ImpSaldoAnt) - float(ImpPagado))
                if MonedaP == MonedaDR:# Si Moneda de Pago igual a Moneda de Factura - Factura y Pago USD
                    ImpPagado = '%.2f' % flt(Monto)
                    ImpSaldoInsoluto= '%.2f' %  (float(ImpSaldoAnt) - float(ImpPagado))
                    cfdi_pago+="""MonedaDR="{MonedaDR}" MetodoDePagoDR="{MetodoPago}" NumParcialidad="{no_parcialidad}" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
                    """.format(**locals())
                else: #Si la Moneda de Pago es Diferente a la Moneda de Factura  - Factura USD - Pago MXN
                    ImpPagado = '%.2f' % (flt(Monto) / flt(TipoCambioDR) )
                    ImpSaldoInsoluto= '%.2f' %  (float(ImpSaldoAnt) - float(ImpPagado))
                    cfdi_pago+="""TipoCambioDR="{TipoCambioDR}" MonedaDR="{MonedaDR}" MetodoDePagoDR="{MetodoPago}" NumParcialidad="{no_parcialidad}" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
                    """.format(**locals())
            else: # Si la Factura es en MXN
                if MonedaP != "MXN": #Si el Pago es Diferente de MXN
                    cfdi_pago+="""TipoCambioDR="{TipoCambioP}" MonedaDR="{MonedaDR}" MetodoDePagoDR="{MetodoPago}" NumParcialidad="{no_parcialidad}" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
                    """.format(**locals())
                else:
                    cfdi_pago+="""MonedaDR="{MonedaDR}" MetodoDePagoDR="{MetodoPago}" NumParcialidad="{no_parcialidad}" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
                    """.format(**locals())
        else:
            if TipoCambioDR:
                ImpSaldoAnt = '%.2f' % x.total_moneda_original
                ImpPagado = '%.2f' % x.total_moneda_original
                ImpSaldoInsoluto= '%.2f' %  (float(ImpSaldoAnt) - float(ImpPagado))
                cfdi_pago+="""MonedaDR="{MonedaDR}" MetodoDePagoDR="PPD" NumParcialidad="1" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
                """.format(**locals())
            else:
                cfdi_pago+="""MonedaDR="{MonedaDR}" MetodoDePagoDR="PPD" NumParcialidad="1" ImpSaldoAnt="{ImpSaldoAnt}" ImpPagado="{ImpPagado}" ImpSaldoInsoluto="{ImpSaldoInsoluto}"/>
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
        # generar xml
        cfdi_recibido = response.json().get('data').get('cfdi')
        dest = '/home/frappe/frappe-bench/sites/' + frappe.local.site + '/public/files/' + uuid
        f = open( dest + '.xml',"w+")
        f.write(cfdi_recibido)
        f.close()
        save_url( "/files/" + uuid +  ".xml" , uuid + ".xml" , "CFDI Nota de Credito" , c.name , "Home/Attachments" , 0)
        # EscribirPNG
        qr = response.json().get('data').get('qrCode')
        png = open( dest + ".png", "wb")
        png.write(base64.b64decode(qr))
        png.close()
        frappe.db.set_value("CFDI Nota de Credito",c.name, 'qr', "/files/" + uuid +  ".png")
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

  fecha_actual = (datetime.now()- timedelta(minutes=480)).isoformat()[0:19]
  serie = c.naming_series.replace('-','')
  folio = c.name.replace(serie,'')
  FormaPago = c.forma_de_pago
  SubTotal = float(c.total)
  # Falta descuento
  descuento = float(c.discount_amount)
  Total = '%.2f' % (c.grand_total)
  TipoDeComprobante = c.tipo_de_comprobante
  MetodoPago = c.metodo_pago
  LugarExpedicion = c.lugar_expedicion
  NoCertificado = c.no_certificado

  rfc_emisor = c.rfc_emisor
  nombre_emisor = c.nombre_emisor.replace('&','Y').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
  regimen_fiscal = c.regimen_fiscal

  tax_id = c.tax_id.replace('&','&amp;')
  nombre_receptor = c.customer_name.replace('&','Y').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
  uso_cfdi = c.uso_cfdi

  # fac_rel = frappe.get_doc(c.tipo_documento,c.factura_fuente)
  tipo_rel = c.tipo_de_relacion
  # uuid_rel = fac_rel.uuid

  Currency = c.currency
  if Currency == 'MXN':
    TipoCambio = 1
  else:
    TipoCambio = '%.4f' % c.conversion_rate

  cfdi = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd"
Version="3.3" Serie="{serie}" Folio="{folio}" Fecha="{fecha_actual}" Sello="" FormaPago="{FormaPago}" NoCertificado=""
Certificado="" CondicionesDePago="CONTADO" SubTotal="{SubTotal}" Descuento="{descuento}" Moneda="{Currency}" TipoCambio = "{TipoCambio}" Total="{Total}" TipoDeComprobante="{TipoDeComprobante}" MetodoPago="{MetodoPago}" LugarExpedicion="{LugarExpedicion}">""".format(**locals())
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
  TotalIeps = '%.2f' % c.total_ieps
  cfdi += """
</cfdi:Conceptos>
<cfdi:Impuestos TotalImpuestosTrasladados="{TotalImpuestosTrasladados}">
    <cfdi:Traslados>
      <cfdi:Traslado Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="{TotalIva}"/>
      """.format(**locals())
  if notieneiva: cfdi += """ <cfdi:Traslado Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.000000" Importe="0.00"/>""".format(**locals())
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
        dest = '/home/frappe/frappe-bench/sites/' + frappe.local.site + '/public/files/' + uuid
        f = open( dest + '.xml',"w+")
        f.write(cfdi_recibido)
        f.close()
        save_url( "/files/" + uuid +  ".xml" , uuid + ".xml" , "Sales Invoice" , c.name , "Home/Attachments" , 0)
        qr = response.json().get('data').get('qrCode')
        png = open( dest + ".png", "wb")
        png.write(base64.b64decode(qr))
        png.close()
        frappe.db.set_value("Sales Invoice",c.name, 'qr', "/files/" + uuid +  ".png")
        frappe.db.set_value("Sales Invoice",c.name, 'cfdi_status', 'Timbrado')
        frappe.db.set_value("Sales Invoice",c.name, 'sellocfd', response.json().get('data').get('selloCFDI'))
        frappe.db.set_value("Sales Invoice",c.name, 'cadenaoriginalsat', response.json().get('data').get('cadenaOriginalSAT'))
        frappe.db.set_value("Sales Invoice",c.name, 'fechatimbrado', response.json().get('data').get('fechaTimbrado') )
        frappe.db.set_value("Sales Invoice",c.name, 'uuid', uuid)
        frappe.db.set_value("Sales Invoice",c.name, 'nocertificadosat', response.json().get('data').get('noCertificadoSAT') )
        frappe.db.set_value("Sales Invoice",c.name, 'sellosat', response.json().get('data').get('selloSAT') )

        mensaje = "TIMBRADO EXITOSO . <a class= 'alert-info' href='https://" + frappe.local.site + "/files/" + uuid + ".xml' download> Descarga XML </a>"
        frappe.msgprint(mensaje)
        return ["TIMBRADO EXITOSO!",mensaje,uuid,xml]

def sales_invoice_timbrado_xml(docname):
    c = frappe.get_doc("Sales Invoice", docname)
    cant = len(c.items)
    # horaminuto = c.posting_time
    # frappe.errprint(h oraminuto)
    # mytime = horaminuto.strftime("%H:%M:%S")
    # frappe.errprint(horaminuto)
    # return
    #fecha_actual = datetime.combine(c.posting_date,mytime).isoformat()[0:19] #dacosta - para hacer que se timbre con la fecha de posting_date
    descuento = float(c.discount_amount)
    fecha_actual = (c.creation).isoformat()[0:19]
    serie = c.naming_series.replace('-','')
    folio = c.name.replace(serie,'')
    # frappe.errprint(c.name.replace(serie,''))
    FormaPago = c.forma_de_pago
    #SubTotal = '%.2f' % c.net_total
    SubTotal = float(c.total)
    Total = '%.2f' % (c.grand_total)
    # Total = 3509.40
    TipoDeComprobante = c.tipo_de_comprobante
    # TipoCambio = 1 if c.currency = "MXN" else '%2f' % c.conversion_rate
    MetodoPago = c.metodo_pago
    LugarExpedicion = c.lugar_expedicion
    Currency = c.currency
    if Currency == 'MXN':
      TipoCambio = 1
    else:
      TipoCambio = '%.4f' % c.conversion_rate
    rfc_emisor = c.rfc_emisor
    nombre_emisor = c.nombre_emisor.replace('&','Y').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
    regimen_fiscal = c.regimen_fiscal

    tax_id = c.tax_id.replace('&','&amp;')
    nombre_receptor = c.customer_name.replace('&','Y').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
    uso_cfdi = c.uso_cfdi

    tipo = []
    tasa = []
    cantidad = []
    cfdi_items = ""
    cfdi_traslados = ""
    for x in c.items:
        NoIdentificacion = x.item_code
        ClaveProdServ = x.clave_producto
        ClaveUnidad = x.clave_unidad
        Cantidad = x.qty
        Unidad = x.stock_uom
        ValorUnitario = '%.2f' % x.rate
        Importe = float(x.amount)
        idx = x.idx
        Descripcion = x.item_name
        des = float(x.descuento)
        TrasladosBase1= Importe - des
        TrasladosBase= float(TrasladosBase1)
        TasaOCuota = .01 * float(x.tasa)
        ImpuestosTrasladosTasaOCuota='%.6f' % TasaOCuota
        Importetax1= float(TrasladosBase * 0.16)
        Importetax= '%.2f' % (Importetax1)

        if x.tipo_de_impuesto == "IVA":
            Impuesto="002"
        elif x.tipo_de_impuesto == "IEPS":
            Impuesto="003"
        else:
            TrasladosBase1= Importe - des
            TrasladosBase= '%.2f' % (TrasladosBase1)
            Impuesto="002"
            ImpuestosTrasladosTasaOCuota="0.000000"
            Importetax= "0.00"

        tipo.append(Impuesto)
        tasa.append(ImpuestosTrasladosTasaOCuota)
        cantidad.append(Importetax)

        cfdi_items += """
        <cfdi:Concepto ClaveProdServ="{ClaveProdServ}" NoIdentificacion="{NoIdentificacion}" Cantidad="{Cantidad}" ClaveUnidad="{ClaveUnidad}" Unidad="{Unidad}" Descripcion="{Descripcion}" ValorUnitario="{ValorUnitario}" Importe="{Importe}" Descuento="{des}">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado Base="{TrasladosBase}" Impuesto="{Impuesto}" TipoFactor="Tasa" TasaOCuota="{ImpuestosTrasladosTasaOCuota}" Importe="{Importetax}"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>""".format(**locals())

        TotalImpuestosTrasladados='%.2f' % c.total_taxes_and_charges
        # TotalImpuestosTrasladados= 4558.38

    cTipo = collections.Counter(tipo)
    cTasa = collections.Counter(tasa)
    total_impuesto = 0
    for w, val1 in cTipo.items():
        for y, val2 in cTasa.items():
            suma =0
            for z in range(0,cant):
                if (tasa[z] == y) and (tipo[z] == w):
                    suma = suma+float(cantidad[z])
            b = y
            t = w
            total_impuesto = total_impuesto+suma
            if(suma>0):
                cfdi_traslados += """
                <cfdi:Traslado Impuesto="{t}" TipoFactor="Tasa" TasaOCuota="{b}" Importe="{suma}"/>""".format(**locals())
            else:
                cfdi_traslados += """
                <cfdi:Traslado Impuesto="{t}" TipoFactor="Tasa" TasaOCuota="{b}" Importe="{suma}"/>""".format(**locals())

    Total = '%.2f' % (c.grand_total)
    cfdi = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd"
Version="3.3" Serie="{serie}" Folio="{folio}" Fecha="{fecha_actual}" Sello="" FormaPago="{FormaPago}" NoCertificado=""
Certificado="" CondicionesDePago="CONTADO" SubTotal="{SubTotal}" Descuento="{descuento}" Moneda="{Currency}" TipoCambio = "{TipoCambio}" Total="{Total}" TipoDeComprobante="{TipoDeComprobante}" MetodoPago="{MetodoPago}" LugarExpedicion="{LugarExpedicion}">""".format(**locals())
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

    cfdi_conceptos = """
    </cfdi:Conceptos>
    <cfdi:Impuestos TotalImpuestosTrasladados="{total_impuesto}">
        <cfdi:Traslados>""".format(**locals())
    cfdi += cfdi_conceptos
    cfdi += cfdi_traslados
    cfdi += """
        </cfdi:Traslados>
    </cfdi:Impuestos>
</cfdi:Comprobante>
    """.format(**locals())
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

# RG- Termina Smarterweb

# RG-COMIENZA MODULO CFDI - FACTURACION MODERNA
# from frappe.model.document import Document
# from frappe.model.mapper import get_mapped_doc
# from frappe.utils.file_manager import save_url
# import shutil
# import os
# import sys
# import time
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler
# import threading
# from xml.dom import minidom
# from datetime import timedelta,datetime
# import base64
# # from M2Crypto import RSA
# from lxml import etree as ET
# import sha
# from suds import WebFault
# from suds.client import Client
# import logging
#
# class Cliente:
#   def __init__(self, url, opciones = {}, debug = False):
#     self.debug = debug
#     self.url = url
#     self.opciones = {}
#     if self.debug: self._activa_debug()
#     for key, value in opciones.iteritems():
#       if key in ['emisorRFC', 'UserID', 'UserPass']:
#         self.opciones.update({ key: value })
#
#   def timbrar(self, src, opciones = { 'generarCBB': True, 'generarTXT': False, 'generarPDF': False}):
#     try:
#       # en caso de que src sea una ruta a archivo y no una cadena, abrir y cargar ruta
#       if os.path.isfile(src): src = open(src, 'r').read()
#       opciones['text2CFDI'] = base64.b64encode(src)
#       self.opciones.update(opciones)
#       cliente = Client(self.url)
#       respuesta = cliente.service.requestTimbrarCFDI(self.opciones)
#
#       for propiedad in ['xml', 'pdf', 'png', 'txt']:
#         if propiedad in respuesta:
#           self.__dict__[propiedad] = base64.b64decode(respuesta[propiedad])
#
#       if 'xml' in respuesta:
#         xml_cfdi = ET.fromstring(self.xml)
#         tfd = xml_cfdi.xpath('//tfd:TimbreFiscalDigital', namespaces={"tfd": "http://www.sat.gob.mx/TimbreFiscalDigital"})
#         self.__dict__['uuid'] = tfd[0].get('UUID')
#         self.__dict__['SelloCFD'] = tfd[0].get('SelloCFD')
#         self.__dict__['NoCertificadoSAT'] = tfd[0].get('NoCertificadoSAT')
#         self.__dict__['SelloSAT'] = tfd[0].get('SelloSAT')
#         self.__dict__['FechaTimbrado'] = tfd[0].get('FechaTimbrado')
#
#       if self.debug:
#         self.logger.info("\nSOAP request:\n %s" % cliente.last_sent())
#         self.logger.info("\nSOAP response:\n %s" % cliente.last_received())
#
#       return True
#     except WebFault, e:
#       self.__dict__['codigo_error'] = e.fault.faultcode
#       self.__dict__['error'] = e.fault.faultstring
#       if self.debug:
#         self.logger.error("\nSOAP request:\n %s\nSOAP response: [%s] - %s" % (cliente.last_sent(), e.fault.faultcode, e.fault.faultstring))
#       return False
#     except Exception, e:
#       self.__dict__['codigo_error'] = 'Error desconocido'
#       self.__dict__['error'] = e.message
#       return False
#
#   def cancelar(self, uuid):
#     try:
#       cliente = Client(self.url)
#       opciones = {'uuid': uuid}
#       opciones.update(self.opciones)
#       respuesta = cliente.service.requestCancelarCFDI(opciones)
#       if self.debug:
#         self.logger.info("\nSOAP request:\n %s" % cliente.last_sent())
#         self.logger.info("\nSOAP response:\n %s" % cliente.last_received())
#       return True
#     except WebFault, e:
#       self.__dict__['codigo_error'] = e.fault.faultcode
#       self.__dict__['error'] = e.fault.faultstring
#       if self.debug:
#         self.logger.error("\nSOAP request:\n %s\nSOAP response: [%s] - %s" % (cliente.last_sent(), e.fault.faultcode, e.fault.faultstring))
#       return False
#     except Exception, e:
#       self.__dict__['codigo_error'] = 'Error desconocido'
#       self.__dict__['error'] = e.message
#       return False
#
#   def activarCancelacion(self, archCer, archKey, passKey):
#     try:
#       # en caso de que archCer y/o archKey sean una ruta a archivo y no una cadena, abrir y cargar ruta
#       if os.path.isfile(archCer): archCer = open(archCer, 'r').read()
#       if os.path.isfile(archKey): archKey = open(archKey, 'r').read()
#       opciones = {}
#       opciones['archivoKey'] = base64.b64encode(archKey)
#       opciones['archivoCer'] = base64.b64encode(archCer)
#       opciones['clave'] = passKey
#       self.opciones.update(opciones)
#       cliente = Client(self.url)
#       respuesta = cliente.service.activarCancelacion(self.opciones)
#       if self.debug:
#         self.logger.info("\nSOAP request:\n %s" % cliente.last_sent())
#         self.logger.info("\nSOAP response:\n %s" % cliente.last_received())
#       return True
#     except WebFault, e:
#       self.__dict__['codigo_error'] = e.fault.faultcode
#       self.__dict__['error'] = e.fault.faultstring
#       if self.debug:
#         self.logger.error("\nSOAP request:\n %s\nSOAP response: [%s] - %s" % (cliente.last_sent(), e.fault.faultcode, e.fault.faultstring))
#       return False
#     except Exception, e:
#       self.__dict__['codigo_error'] = 'Error desconocido'
#       self.__dict__['error'] = e.message
#       return False
#
#   def _activa_debug(self):
#     if not os.path.exists('log'): os.makedirs('log')
#     self.logger = logging.getLogger('facturacion_moderna')
#     hdlr = logging.FileHandler('log/facturacion_moderna.log')
#     formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
#     hdlr.setFormatter(formatter)
#     self.logger.addHandler(hdlr)
#     self.logger.setLevel(logging.INFO)
#
# @frappe.whitelist()
# def prueba_cancelacion(docname, debug = True):
#
#   c = frappe.get_doc("Sales Invoice", docname)
#
#   rfc_emisor = c.rfc_emisor
#   url_timbrado = c.url_timbrado
#   user_id = c.user_id
#   user_password = c.user_password
#
#   params = {'emisorRFC': rfc_emisor, 'UserID': user_id, 'UserPass': user_password}
#   cliente = Cliente(url_timbrado, params, debug)
#
#   # UUID del comprobante a cancelar
#   uuid = c.uuid
#
#   if cliente.cancelar(uuid):
#     frappe.msgprint("Cancelacion Exitosa")
#     frappe.db.set_value("Sales Invoice",c.name, 'cfdi_status', 'Cancelado')  #RG-asi cambio el status del timbrado
#   else:
#     frappe.msgprint("[%s] - %s" % (cliente.codigo_error, cliente.error))
#
# if __name__ == '__main__':
#   prueba_cancelacion()
#
# @frappe.whitelist()
# def cancelacion(docname,debug = True):
#   c = frappe.get_doc("CFDI", docname)
#   # si = c.ticket
#   rfc_emisor = c.rfc_emisor
#   url_timbrado = c.url_timbrado
#   user_id = c.user_id
#   user_password = c.user_password
#   params = {'emisorRFC': rfc_emisor, 'UserID': user_id, 'UserPass': user_password}
#   cliente = Cliente(url_timbrado, params, debug)
#   # UUID del comprobante a cancelar
#   uuid = c.uuid
#   if cliente.cancelar(uuid):
#     frappe.db.set_value("CFDI",c.name, 'cfdi_status', 'Cancelado')  #RG-asi cambio el status del timbrado
#     for d in c.items:
#         frappe.db.set_value("Sales Invoice",d.fuente , 'cfdi_status', 'Sin Timbrar')
#     frappe.msgprint("Cancelacion Exitosa")
#
#   else:
#     frappe.msgprint("[%s] - %s" % (cliente.codigo_error, cliente.error))
#
# if __name__ == '__main__':
#   cancelacion()
#
# @frappe.whitelist()
# def cancelar_egreso(docname, debug = True):
#   c = frappe.get_doc("CFDI Nota de Credito", docname)
#   rfc_emisor = c.rfc_emisor
#   url_timbrado = c.url_timbrado
#   user_id = c.user_id
#   user_password = c.user_password
#   params = {'emisorRFC': rfc_emisor, 'UserID': user_id, 'UserPass': user_password}
#   cliente = Cliente(url_timbrado, params, debug)
#   # UUID del comprobante a cancelar
#   uuid = c.uuid
#   if cliente.cancelar(uuid):
#     frappe.msgprint("Cancelacion Exitosa")
#     frappe.db.set_value("CFDI Nota de Credito",c.name, 'cfdi_status', 'Cancelado')  #RG-asi cambio el status del timbrado
#   else:
#     frappe.msgprint("[%s] - %s" % (cliente.codigo_error, cliente.error))
#
# if __name__ == '__main__':
#   cancelar_egreso()
#
#
# @frappe.whitelist()
# def prueba_timbrado(docname, debug = True):
#
#   c = frappe.get_doc("Sales Invoice", docname)
#
#   rfc_emisor = c.rfc_emisor
#   url_timbrado = c.url_timbrado
#   user_id = c.user_id
#   user_password = c.user_password
#
#   cfdif = genera_layout(docname,rfc_emisor)
#
#   params = {'emisorRFC': rfc_emisor, 'UserID': user_id, 'UserPass': user_password}
#   options = {'generarCBB': True, 'generarPDF': True, 'generarTXT': True}
#   cliente = Cliente(url_timbrado, params, debug)
#   source = '/home/frappe/frappe-bench/sites/comprobantes/'
#   webfolder =c.folder
#   dest ='/home/frappe/frappe-bench/sites/' + webfolder + '/public/files/'
#   # dest = '/home/frappe/frappe-bench/sites/facturas.posix.mx/public/files/'
#
#   if cliente.timbrar(cfdif, options):
#     folder = 'comprobantes'
#     if not os.path.exists(folder): os.makedirs(folder)
#     comprobante = os.path.join(folder, cliente.uuid)
#     for extension in ['xml', 'pdf', 'png', 'txt']:
#       if hasattr(cliente, extension):
#         with open(("%s.%s" % (comprobante, extension)), 'wb' if extension in ['pdf','png'] else 'w') as f: f.write(getattr(cliente, extension))
#
#     uuid=comprobante[13:]
#
#     shutil.move(source + uuid  + ".xml", dest) # RG-Muevo el file de donde lo deja factmoderna a donde lo quiero
#     shutil.move(source + uuid  + ".png", dest) # RG-Muevo el file de donde lo deja factmoderna a donde lo quiero
#     save_url("/files/" + uuid + ".xml",  uuid + ".xml", "Sales Invoice",c.name, "Home/Attachments", 0) # RG-agrego el file como attachment # save_url (file_url, filename, dt, dn, folder, is_private)
#     frappe.db.set_value("Sales Invoice",c.name, 'cfdi_status', 'Timbrado')  #RG-asi cambio el status del timbrado
#     frappe.db.set_value("Sales Invoice",c.name, 'SelloCFD', cliente.SelloCFD)  #RG-Asi inserto los valores del xml
#     frappe.db.set_value("Sales Invoice",c.name, 'FechaTimbrado', cliente.FechaTimbrado)
#     frappe.db.set_value("Sales Invoice",c.name, 'uuid', cliente.uuid)
#     frappe.db.set_value("Sales Invoice",c.name, 'NoCertificadoSAT', cliente.NoCertificadoSAT)
#     frappe.db.set_value("Sales Invoice",c.name, 'SelloSAT', cliente.SelloSAT)
#     frappe.db.set_value("Sales Invoice",c.name, 'qr', 'http://' + webfolder + '/files/' + uuid + ".png")  #RG-Asi inserto EL QR
#
#
#
#     frappe.msgprint(str(c.name) + " Timbrada exitosamente " + "    "  + "<a href='javascript:void(0)' onclick='window.location.reload()'><button class='btn btn-primary btn-sm primary-action' > Agregar XML a Factura</button></a>")
#
#   else:
#     frappe.msgprint("ERROR EN TIMBRADO: " + "[%s] - %s" % (cliente.codigo_error, cliente.error))
#
# @frappe.whitelist()
# def genera_layout(docname,rfc_emisor):
#   mytime = datetime.strptime('0800','%H%M').time()
#   fecha_actual = datetime.combine(c.posting_date,mytime).isoformat()[0:19] #dacosta - para hacer que se timbre con la fecha de posting_date
#
#   fecha_actual = (datetime.now()- timedelta(minutes=360)).isoformat()[0:19]
#   c = frappe.get_doc("Sales Invoice", docname)
#   serie = c.naming_series
#   folio = c.name
#   nombre_receptor = c.customer_name.replace('&','Y').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
#   SubTotal='%.1f' % c.net_total
#   # SubTotal='%.1f' % c.total
#   redondeo = c.rounding_adjustment * -1
#   Descuento='%.1f' % (c.discount_amount)
#   # Descuento='%.1f' % (c.base_total - c.net_total)
#   PorcDescuento=flt((100 - c.additional_discount_percentage) * .01,2)
#   factorDesc = flt((c.additional_discount_percentage) * .01,2)
#   # Total='%.1f' % (c.base_grand_total + flt(redondeo))   RG- Se lo quite porque daba bronca el redondeo
#   Total='%.1f' % c.grand_total
#   # Total='%.1f' % c.base_grand_total
#   FormaPago=c.forma_de_pago
#   TipoDeComprobante=c.tipo_de_comprobante
#   MetodoPago=c.metodo_pago
#   LugarExpedicion=c.lugar_expedicion
#   NoCertificado=c.no_certificado
#   Rfc=c.tax_id.replace('&','&amp;')
#   TotalImpuestosTrasladados='%.1f' % c.total_taxes_and_charges
#   TotalIva = '%.1f' % c.taxes[0].tax_amount
#   UsoCFDI = c.uso_cfdi
#   Nombre = c.nombre_emisor
#   RegimenFiscal = c.regimen_fiscal
#   cfdif = """[ComprobanteFiscalDigital]
# Version=3.3
# Serie={serie}
# Folio={folio}
# Fecha={fecha_actual}
# FormaPago={FormaPago}
# NoCertificado={NoCertificado}
# Moneda=MXN
# TipoDeComprobante={TipoDeComprobante}
# MetodoPago={MetodoPago}
# LugarExpedicion={LugarExpedicion}
#
# SubTotal={SubTotal}
# Descuento={Descuento}
# Total={Total}
#
# [Emisor]
# Rfc={rfc_emisor}
# Nombre={Nombre}
# RegimenFiscal={RegimenFiscal}
#
# [Receptor]
# Rfc={Rfc}
# Nombre={nombre_receptor}
#
# UsoCFDI={UsoCFDI}
#
# """.format(**locals())
#   for d in c.items:
#     NoIdentificacion=d.item_code
#     ClaveProdServ=d.clave_de_producto
#     ClaveUnidad=d.clave_unidad
#     Cantidad=d.qty
#     Unidad=d.uom
#     ValorUnitario='%.1f' % d.net_rate
#     # ValorUnitario='%.1f' % d.rate
#     Importe='%.1f' %  (d.net_amount)
#     # Importe='%.1f' %  (d.rate * d.qty)
#     idx=d.idx
#     Descripcion=d.description.encode('ascii', 'ignore').decode('ascii')
#     if "16.0" in d.item_tax_rate:
#       DescuentoItem= '%.1f' % (flt(Importe)  * factorDesc)
#       PreBase= flt(Importe)  - flt(DescuentoItem)
#       ImpuestosTrasladosBase= '%.1f' % PreBase
#       ImpuestosTrasladosImpuesto="002"
#       ImpuestosTrasladosTasaOCuota="0.160000"
#       # ImpuestosTrasladosImporte='%.1f' % (PreBase * 0.16)   #RG- 23/Ene/2018 - cambie a .2 el decimal - estaba a .1
#       ImpuestosTrasladosImporte='%.1f' % ( d.net_amount * 0.16)
#
#     elif "8.0" in d.item_tax_rate:
#       DescuentoItem= '%.1f' % ((flt(Importe) * 1.08) * factorDesc)
#       PreImporte = flt(Importe) * 0.08
#       PreBase= flt(Importe)  - flt(DescuentoItem)
#       ImpuestosTrasladosBase= '%.1f' % PreBase
#       ImpuestosTrasladosImpuesto="003"
#       ImpuestosTrasladosTasaOCuota="0.080000"
#       ImpuestosTrasladosImporte='%.1f' % ( d.net_amount * 0.08)
#       # ImpuestosTrasladosBase= '%.1f' % PreBase
#     else:
#       DescuentoItem= '%.1f' % ((flt(Importe) * factorDesc))
#       ImpuestosTrasladosImporte = "0.00"
#       ImpuestosTrasladosImpuesto = "002"
#       ImpuestosTrasladosTasaOCuota ="0.000000"
#       PreBase = flt(Importe)  - flt(DescuentoItem)
#       ImpuestosTrasladosBase= '%.1f' % PreBase
#     cfdif += """[Concepto#{idx}]
# ClaveProdServ={ClaveProdServ}
# NoIdentificacion={NoIdentificacion}
# Cantidad={Cantidad}
# ClaveUnidad={ClaveUnidad}
# Unidad={Unidad}
# ValorUnitario={ValorUnitario}
# Descuento={DescuentoItem}
# Importe={Importe}
# Impuestos.Traslados.Base=[{ImpuestosTrasladosBase}]
# Impuestos.Traslados.Impuesto=[{ImpuestosTrasladosImpuesto}]
# Impuestos.Traslados.TipoFactor=[Tasa]
# Impuestos.Traslados.TasaOCuota=[{ImpuestosTrasladosTasaOCuota}]
# Impuestos.Traslados.Importe=[{ImpuestosTrasladosImporte}]
# Descripcion={Descripcion}
#
# """.format(**locals())
#   cfdif += """[Traslados]
# TotalImpuestosTrasladados={TotalImpuestosTrasladados}
# Impuesto=[002]
# TipoFactor=[Tasa]
# TasaOCuota=[0.160000]
# Importe=[{TotalIva}]
# """.format(**locals())
# #   for t in c.taxes:
# #     if t.rate == 16:
# #       Impuesto="002"
# #       TasaOCuota="0.160000"
# #       Importe='%.1f' % t.tax_amount
# #       # Importe='%.2f' % (t.tax_amount_after_discount_amount)
# #     # if t.description == "IEPS 8":
# #     elif t.rate==8:
# #       Impuesto="003"
# #       TasaOCuota="0.080000"
# #       Importe='%.2f' % t.tax_amount
# #     else:
# #       Impuesto="002"
# #       TasaOCuota="0.000000"
# #       Importe='%.2f' % t.tax_amount
# #     cfdif += """
# # Impuesto=[{Impuesto}]
# # TipoFactor=[Tasa]
# # TasaOCuota=[{TasaOCuota}]
# # Importe=[{Importe}]
#   frappe.errprint(cfdif)     #RG-esto es nomas pa ver que es lo que estoy mandando
#   return cfdif;
#
# if __name__ == '__main__':
#   prueba_timbrado()
#
#
# @frappe.whitelist()
# def timbrado(docname,debug = True):
#
#   # si = 0
#   c = frappe.get_doc("CFDI", docname)
#   # si = c.ticket
#   # si = frappe.get_doc("Sales Invoice", si)
#
#   rfc_emisor = c.rfc_emisor
#   url_timbrado = c.url_timbrado
#   user_id = c.user_id
#   user_password = c.user_password
#
#   cfdif = genera_layout_cfdi(docname,rfc_emisor)
#
#   params = {'emisorRFC': rfc_emisor, 'UserID': user_id, 'UserPass': user_password}
#   options = {'generarCBB': True, 'generarPDF': True, 'generarTXT': True}
#   cliente = Cliente(url_timbrado, params, debug)
#   source = '/home/frappe/frappe-bench/sites/comprobantes/'
#   webfolder =c.folder
#   dest ='/home/frappe/frappe-bench/sites/' + webfolder + '/public/files/'
#   # dest = '/home/frappe/frappe-bench/sites/facturas.posix.mx/public/files/'
#
#   if cliente.timbrar(cfdif, options):
#     folder = 'comprobantes'
#     if not os.path.exists(folder): os.makedirs(folder)
#     comprobante = os.path.join(folder, cliente.uuid)
#     for extension in ['xml', 'pdf', 'png', 'txt']:
#       if hasattr(cliente, extension):
#         with open(("%s.%s" % (comprobante, extension)), 'wb' if extension in ['pdf','png'] else 'w') as f: f.write(getattr(cliente, extension))
#
#     uuid=comprobante[13:]
#
#     shutil.move(source + uuid  + ".xml", dest) # RG-Muevo el file de donde lo deja factmoderna a donde lo quiero
#     shutil.move(source + uuid  + ".png", dest)
#     save_url("/files/" + uuid + ".xml",  uuid + ".xml", "CFDI",c.name, "Home/Attachments", 0) # RG-agrego el file como attachment # save_url (file_url, filename, dt, dn, folder, is_private)
#     frappe.db.set_value("CFDI",c.name, 'cfdi_status', 'Timbrado')  #RG-asi cambio el status del timbrado
#     for d in c.items:
#         frappe.db.set_value("Sales Invoice", d.fuente , 'cfdi_status', 'Timbrado')
#     frappe.db.set_value("CFDI",c.name, 'SelloCFD', cliente.SelloCFD)  #RG-Asi inserto los valores del xml
#     frappe.db.set_value("CFDI",c.name, 'FechaTimbrado', cliente.FechaTimbrado)
#     frappe.db.set_value("CFDI",c.name, 'uuid', cliente.uuid)
#     frappe.db.set_value("CFDI",c.name, 'NoCertificadoSAT', cliente.NoCertificadoSAT)
#     frappe.db.set_value("CFDI",c.name, 'SelloSAT', cliente.SelloSAT)
#     frappe.db.set_value("CFDI",c.name, 'qr', '/files/' + uuid + ".png")
#
#     # empiezo a generar el archivo para el envio
#     with open("/home/frappe/frappe-bench/sites/" + webfolder + "/public/files/{0}.xml".format(uuid), "rb") as fileobj:
#     	filedata = fileobj.read()
#     out = {
#     		"fname": "{0}.xml".format(uuid),
#     		"fcontent": filedata
#     }
#     message = "Anexo a este correo encontrara su factura. Gracias por su preferencia."
#     frappe.sendmail(["{0}".format(c.email)], \
#     subject="Factura Electronica:  {0}.".format(c.name), \
#     attachments = [out,frappe.attach_print("CFDI", c.name, file_name="{0}".format(c.name), print_format="CFDI")], \
#     content=message,delayed=False)
#
#     frappe.msgprint(str(c.name) + " Timbrada exitosamente " + "    "  + "<a href='javascript:void(0)' onclick='window.location.reload()'><button class='btn btn-primary btn-sm primary-action' > Agregar XML a Factura</button></a>")
#
#   else:
#     frappe.msgprint("ERROR EN TIMBRADO: " + "[%s] - %s" % (cliente.codigo_error, cliente.error))
#
# @frappe.whitelist()
# def genera_layout_cfdi(docname,rfc_emisor):
#   tieneiva = 0
#   notieneiva = 0
#   tieneieps = 0
#   mytime = datetime.strptime('0800','%H%M').time()
#   #fecha_actual = datetime.combine(c.posting_date,mytime).isoformat()[0:19] #dacosta - para hacer que se timbre con la fecha de posting_date
#
#   fecha_actual = (datetime.now()- timedelta(minutes=360)).isoformat()[0:19]
#   c = frappe.get_doc("CFDI", docname)
#   serie = c.naming_series
#   folio = c.name
#   nombre_receptor = c.customer_name.replace('&','Y').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
#   SubTotal='%.2f' % c.total_neto
#   Total='%.2f' % c.total
#   FormaPago=c.forma_de_pago
#   TipoDeComprobante=c.tipo_de_comprobante
#   MetodoPago=c.metodo_pago
#   LugarExpedicion=c.lugar_expedicion
#   NoCertificado=c.no_certificado
#   Rfc=c.tax_id.replace('&','&amp;')
#   TotalImpuestosTrasladados='%.2f' % c.total_impuestos
#   TotalIva = '%.2f' % c.total_iva
#   TotalIeps = '%.2f' % c.total_ieps
#   UsoCFDI = c.uso_cfdi
#   Nombre = c.nombre_emisor
#   RegimenFiscal = c.regimen_fiscal
#   cfdif = """[ComprobanteFiscalDigital]
# Version=3.3
# Serie={serie}
# Folio={folio}
# Fecha={fecha_actual}
# FormaPago={FormaPago}
# NoCertificado={NoCertificado}
# Moneda=MXN
# TipoDeComprobante={TipoDeComprobante}
# MetodoPago={MetodoPago}
# LugarExpedicion={LugarExpedicion}
#
# SubTotal={SubTotal}
# Descuento=0
# Total={Total}
#
# [Emisor]
# Rfc={rfc_emisor}
# Nombre={Nombre}
# RegimenFiscal={RegimenFiscal}
#
# [Receptor]
# Rfc={Rfc}
# Nombre={nombre_receptor}
#
# UsoCFDI={UsoCFDI}
#
# """.format(**locals())
#   for d in c.items:
#     NoIdentificacion=d.item_code
#     ClaveProdServ=d.clave_producto
#     ClaveUnidad=d.clave_unidad
#     Cantidad=d.qty
#     Unidad=d.stock_uom
#     ValorUnitario='%.2f' % d.precio_unitario_neto
#     Importe= '%.2f' % d.precio_neto
#     idx=d.idx
#     Descripcion=d.item_name
#     if d.tax == 16:
#         tieneiva = 1
#         ImpuestosTrasladosBase= '%.2f' % d.precio_neto
#         ImpuestosTrasladosImpuesto="002"
#         ImpuestosTrasladosTasaOCuota="0.160000"
#         ImpuestosTrasladosImporte='%.2f' % d.impuestos_totales
#     elif d.tax == 8:
#         tieneieps = 1
#         ImpuestosTrasladosBase= '%.2f' % d.precio_neto
#         ImpuestosTrasladosImpuesto="003"
#         ImpuestosTrasladosTasaOCuota="0.080000"
#         ImpuestosTrasladosImporte='%.2f' % d.impuestos_totales
#     else:
#         notieneiva = 1
#         ImpuestosTrasladosImporte = "0.00"
#         ImpuestosTrasladosImpuesto = "002"
#         ImpuestosTrasladosTasaOCuota ="0.000000"
#         ImpuestosTrasladosBase= '%.2f' % d.precio_neto
#     cfdif += """[Concepto#{idx}]
# ClaveProdServ={ClaveProdServ}
# NoIdentificacion={NoIdentificacion}
# Cantidad={Cantidad}
# ClaveUnidad={ClaveUnidad}
# Unidad={Unidad}
# ValorUnitario={ValorUnitario}
# Descuento=0
# Importe={Importe}
# Impuestos.Traslados.Base=[{ImpuestosTrasladosBase}]
# Impuestos.Traslados.Impuesto=[{ImpuestosTrasladosImpuesto}]
# Impuestos.Traslados.TipoFactor=[Tasa]
# Impuestos.Traslados.TasaOCuota=[{ImpuestosTrasladosTasaOCuota}]
# Impuestos.Traslados.Importe=[{ImpuestosTrasladosImporte}]
# Descripcion={Descripcion}
#
# """.format(**locals())
#   if notieneiva and tieneiva and tieneieps:
#     cfdif += """[Traslados]
#     TotalImpuestosTrasladados={TotalImpuestosTrasladados}
#     Impuesto=[002,002,003]
#     TipoFactor=[Tasa,Tasa,Tasa]
#     TasaOCuota=[0.000000,0.160000,0.080000]
#     Importe=[0.00,{TotalIva},{TotalIeps}]
# """.format(**locals())
#   elif tieneieps and tieneiva:
#     cfdif += """[Traslados]
#     TotalImpuestosTrasladados={TotalImpuestosTrasladados}
#     Impuesto=[002,003]
#     TipoFactor=[Tasa,Tasa]
#     TasaOCuota=[0.160000,0.080000]
#     Importe=[{TotalIva},{TotalIeps}]
# """.format(**locals())
#   elif tieneieps and notieneiva:
#     cfdif += """[Traslados]
#     TotalImpuestosTrasladados={TotalImpuestosTrasladados}
#     Impuesto=[002,003]
#     TipoFactor=[Tasa,Tasa]
#     TasaOCuota=[0.000000,0.080000]
#     Importe=[0.00,{TotalIeps}]
# """.format(**locals())
#   elif notieneiva and tieneiva:
#     cfdif += """[Traslados]
#     TotalImpuestosTrasladados={TotalImpuestosTrasladados}
#     Impuesto=[002,002]
#     TipoFactor=[Tasa,Tasa]
#     TasaOCuota=[0.000000,0.160000]
#     Importe=[0.00,{TotalIva}]
# """.format(**locals())
#   elif tieneieps:
#     cfdif += """[Traslados]
# 	TotalImpuestosTrasladados={TotalImpuestosTrasladados}
# 	Impuesto=[003]
# 	TipoFactor=[Tasa]
# 	TasaOCuota=[0.080000]
# 	Importe=[{TotalIeps}]
# """.format(**locals())
#   elif notieneiva:
#     cfdif += """[Traslados]
# 	TotalImpuestosTrasladados={TotalImpuestosTrasladados}
# 	Impuesto=[002]
# 	TipoFactor=[Tasa]
# 	TasaOCuota=[0.000000]
# 	Importe=[0.00]
# """.format(**locals())
#   else:
#     cfdif += """[Traslados]
# 	TotalImpuestosTrasladados={TotalImpuestosTrasladados}
# 	Impuesto=[002]
# 	TipoFactor=[Tasa]
# 	TasaOCuota=[0.160000]
# 	Importe=[{TotalIva}]
# """.format(**locals())
#   frappe.errprint(cfdif)     #RG-esto es nomas pa ver que es lo que estoy mandando
#   return cfdif;
#
# if __name__ == '__main__':
#   timbrado()
#
# #RG- Inicia seccion de nota de credito - egreso
# @frappe.whitelist()
# def timbrado_egreso(docname, debug = True):
#
#   c = frappe.get_doc("CFDI Nota de Credito", docname)
#
#   rfc_emisor = c.rfc_emisor
#   url_timbrado = c.url_timbrado
#   user_id = c.user_id
#   user_password = c.user_password
#
#   cfdif = genera_layout_egreso(docname,rfc_emisor)
#
#   params = {'emisorRFC': rfc_emisor, 'UserID': user_id, 'UserPass': user_password}
#   options = {'generarCBB': True, 'generarPDF': True, 'generarTXT': True}
#   cliente = Cliente(url_timbrado, params, debug)
#   source = '/home/frappe/frappe-bench/sites/comprobantes/'
#   webfolder =c.folder
#   dest ='/home/frappe/frappe-bench/sites/' + webfolder + '/public/files/'
#   # dest = '/home/frappe/frappe-bench/sites/facturas.posix.mx/public/files/'
#
#   if cliente.timbrar(cfdif, options):
#     folder = 'comprobantes'
#     if not os.path.exists(folder): os.makedirs(folder)
#     comprobante = os.path.join(folder, cliente.uuid)
#     for extension in ['xml', 'pdf', 'png', 'txt']:
#       if hasattr(cliente, extension):
#         with open(("%s.%s" % (comprobante, extension)), 'wb' if extension in ['pdf','png'] else 'w') as f: f.write(getattr(cliente, extension))
#
#     uuid=comprobante[13:]
#
#     shutil.move(source + uuid  + ".xml", dest) # RG-Muevo el file de donde lo deja factmoderna a donde lo quiero
#     shutil.move(source + uuid  + ".png", dest)
#     save_url("/files/" + uuid + ".xml",  uuid + ".xml", "CFDI Nota de Credito",c.name, "Home/Attachments", 0) # RG-agrego el file como attachment # save_url (file_url, filename, dt, dn, folder, is_private)
#     frappe.db.set_value("CFDI Nota de Credito",c.name, 'cfdi_status', 'Timbrado')  #RG-asi cambio el status del timbrado
#     frappe.db.set_value("CFDI Nota de Credito",c.name, 'SelloCFD', cliente.SelloCFD)  #RG-Asi inserto los valores del xml
#     frappe.db.set_value("CFDI Nota de Credito",c.name, 'FechaTimbrado', cliente.FechaTimbrado)
#     frappe.db.set_value("CFDI Nota de Credito",c.name, 'uuid', cliente.uuid)
#     frappe.db.set_value("CFDI Nota de Credito",c.name, 'NoCertificadoSAT', cliente.NoCertificadoSAT)
#     frappe.db.set_value("CFDI Nota de Credito",c.name, 'SelloSAT', cliente.SelloSAT)
#     frappe.db.set_value("CFDI Nota de Credito",c.name, 'qr', '/files/' + uuid + ".png")
#     frappe.msgprint(str(c.name) + " Timbrada exitosamente " + "    "  + "<a href='javascript:void(0)' onclick='window.location.reload()'><button class='btn btn-primary btn-sm primary-action' > Agregar XML a Factura</button></a>")
#
#   else:
#     frappe.msgprint("ERROR EN TIMBRADO: " + "[%s] - %s" % (cliente.codigo_error, cliente.error))
#
# @frappe.whitelist()
# def genera_layout_egreso(docname,rfc_emisor):
#   tieneiva = 0
#   notieneiva = 0
#   mytime = datetime.strptime('0800','%H%M').time()
#   fecha_actual = datetime.combine(c.posting_date,mytime).isoformat()[0:19] #dacosta - para hacer que se timbre con la fecha de posting_date
#
#   #fecha_actual = (datetime.now()- timedelta(minutes=360)).isoformat()[0:19]
#   c = frappe.get_doc("CFDI Nota de Credito", docname)
#   serie = c.naming_series
#   folio = c.name
#   nombre_receptor = c.customer_name.replace('&','Y').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('À','a').replace('É','e').replace('Í','i').replace('Ó','o').replace('Ú','u').replace('@',' ')
#   SubTotal='%.2f' % c.total_neto
#   Total='%.2f' % c.total
#   FormaPago=c.forma_de_pago
#   TipoDeComprobante=c.tipo_de_comprobante
#   MetodoPago=c.metodo_pago
#   LugarExpedicion=c.lugar_expedicion
#   NoCertificado=c.no_certificado
#   Rfc=c.tax_id.replace('&','&amp;')
#   TotalImpuestosTrasladados='%.2f' % c.total_impuestos
#   TotalIva = '%.2f' % c.total_iva
#   TotalIeps = '%.2f' % c.total_ieps
#   UsoCFDI = c.uso_cfdi
#   Nombre = c.nombre_emisor
#   RegimenFiscal = c.regimen_fiscal
#   TipoRelacion = c.tipo_de_relacion
#   UUID= c.uuid_relacionado
#   cfdif = """[ComprobanteFiscalDigital]
# Version=3.3
# Serie={serie}
# Folio={folio}
# Fecha={fecha_actual}
# FormaPago={FormaPago}
# NoCertificado={NoCertificado}
# Moneda=MXN
# TipoDeComprobante={TipoDeComprobante}
# MetodoPago={MetodoPago}
# LugarExpedicion={LugarExpedicion}
#
# SubTotal={SubTotal}
# Descuento=0
# Total={Total}
#
# [CfdiRelacionados]
# TipoRelacion={TipoRelacion}
# UUID=[{UUID}]
#
# [Emisor]
# Rfc={rfc_emisor}
# Nombre={Nombre}
# RegimenFiscal={RegimenFiscal}
#
# [Receptor]
# Rfc={Rfc}
# Nombre={nombre_receptor}
#
# UsoCFDI={UsoCFDI}
#
# """.format(**locals())
#   for d in c.items:
#     NoIdentificacion=d.item_code
#     ClaveProdServ=d.clave_producto
#     ClaveUnidad=d.clave_unidad
#     Cantidad=d.qty
#     Unidad=d.stock_uom
#     ValorUnitario='%.2f' % d.precio_unitario_neto
#     Importe= '%.2f' % d.precio_neto
#     idx=d.idx
#     Descripcion=d.item_name
#     if d.tax == 16:
#         tieneiva = 1
#         ImpuestosTrasladosBase= '%.2f' % d.precio_neto
#         ImpuestosTrasladosImpuesto="002"
#         ImpuestosTrasladosTasaOCuota="0.160000"
#         ImpuestosTrasladosImporte='%.2f' % d.impuestos_totales
#     elif d.tax == 8:
#         ImpuestosTrasladosBase= '%.2f' % d.precio_neto
#         ImpuestosTrasladosImpuesto="003"
#         ImpuestosTrasladosTasaOCuota="0.080000"
#         ImpuestosTrasladosImporte='%.2f' % d.impuestos_totales
#     else:
#         notieneiva = 1
#         ImpuestosTrasladosImporte = "0.00"
#         ImpuestosTrasladosImpuesto = "002"
#         ImpuestosTrasladosTasaOCuota ="0.000000"
#         ImpuestosTrasladosBase= '%.2f' % d.precio_neto
#     cfdif += """[Concepto#{idx}]
# ClaveProdServ={ClaveProdServ}
# NoIdentificacion={NoIdentificacion}
# Cantidad={Cantidad}
# ClaveUnidad={ClaveUnidad}
# Unidad={Unidad}
# ValorUnitario={ValorUnitario}
# Descuento=0
# Importe={Importe}
# Impuestos.Traslados.Base=[{ImpuestosTrasladosBase}]
# Impuestos.Traslados.Impuesto=[{ImpuestosTrasladosImpuesto}]
# Impuestos.Traslados.TipoFactor=[Tasa]
# Impuestos.Traslados.TasaOCuota=[{ImpuestosTrasladosTasaOCuota}]
# Impuestos.Traslados.Importe=[{ImpuestosTrasladosImporte}]
# Descripcion={Descripcion}
#
# """.format(**locals())
#     if notieneiva and tieneiva:
#         cfdif += """[Traslados]
# TotalImpuestosTrasladados={TotalImpuestosTrasladados}
# Impuesto=[002,002]
# TipoFactor=[Tasa,Tasa]
# TasaOCuota=[0.000000,0.160000]
# Importe=[0.00,{TotalIva}]
# """.format(**locals())
#     elif notieneiva:
# 		cfdif += """[Traslados]
# 	TotalImpuestosTrasladados={TotalImpuestosTrasladados}
# 	Impuesto=[002]
# 	TipoFactor=[Tasa]
# 	TasaOCuota=[0.000000]
# 	Importe=[0.00]
# """.format(**locals())
#     else:
# 		cfdif += """[Traslados]
# 	TotalImpuestosTrasladados={TotalImpuestosTrasladados}
# 	Impuesto=[002]
# 	TipoFactor=[Tasa]
# 	TasaOCuota=[0.160000]
# 	Importe=[{TotalIva}]
# """.format(**locals())
#   frappe.errprint(cfdif)     #RG-esto es nomas pa ver que es lo que estoy mandando
#   return cfdif;
#
# if __name__ == '__main__':
#   timbrado_egreso()
#
# # RG-Termina seccion nota de credito
#
#
# @frappe.whitelist()
# def timbrado_pago_cfdi(docname, invoice, debug = True):
#
#   c = frappe.get_doc("Payment Entry", docname)
#
#   si = frappe.get_doc("CFDI", invoice)
#   rfc_emisor = si.rfc_emisor
#   url_timbrado = si.url_timbrado
#   user_id = si.user_id
#   user_password = si.user_password
#   webfolder =si.folder
#
#   cfdif = genera_layout_pago_cfdi(docname, invoice, rfc_emisor)
#
#   params = {'emisorRFC': rfc_emisor, 'UserID': user_id, 'UserPass': user_password}
#   options = {'generarCBB': True, 'generarPDF': True, 'generarTXT': True}
#   cliente = Cliente(url_timbrado, params, debug)
#   source = '/home/frappe/frappe-bench/sites/comprobantes/'
#   dest ='/home/frappe/frappe-bench/sites/' + webfolder + '/public/files/'
#
#   if cliente.timbrar(cfdif, options):
#     folder = 'comprobantes'
#     if not os.path.exists(folder): os.makedirs(folder)
#     comprobante = os.path.join(folder, cliente.uuid)
#     for extension in ['xml', 'pdf', 'png', 'txt']:
#       if hasattr(cliente, extension):
#         with open(("%s.%s" % (comprobante, extension)), 'wb' if extension in ['pdf','png'] else 'w') as f: f.write(getattr(cliente, extension))
#         # frappe.errprint("%s almacenado correctamente en %s.%s" % (extension.upper(), comprobante, extension))
#     # print 'Timbrado exitoso'
#     uuid=comprobante[13:]
#
#     shutil.move(source + uuid  + ".xml", dest) # RG-Muevo el file de donde lo deja factmoderna a donde lo quiero
#     shutil.move(source + uuid  + ".png", dest) # RG-Muevo el file de donde lo deja factmoderna a donde lo quiero
#     save_url("/files/" + uuid + ".xml",  uuid + ".xml", "Payment Entry",c.name, "Home/Attachments", 0) # RG-agrego el file como attachment # save_url (file_url, filename, dt, dn, folder, is_private)
#     frappe.db.set_value("Payment Entry",c.name, 'cfdi_status', 'Timbrado')  #RG-asi cambio el status del timbrado
#     frappe.db.set_value("Payment Entry",c.name, 'uuid_pago', uuid)
#     frappe.db.set_value("Payment Entry",c.name, 'SelloCFD', cliente.SelloCFD)  #RG-Asi inserto los valores del xml
#     frappe.db.set_value("Payment Entry",c.name, 'FechaTimbrado', cliente.FechaTimbrado)
#     frappe.db.set_value("Payment Entry",c.name, 'NoCertificadoSAT', cliente.NoCertificadoSAT)
#     frappe.db.set_value("Payment Entry",c.name, 'SelloSAT', cliente.SelloSAT)
#     frappe.db.set_value("Payment Entry",c.name, 'qr', '/files/' + uuid + ".png")
#     frappe.msgprint(str(c.name) + " Timbrada exitosamente " + "\n\n"  + "<a href='javascript:void(0)' onclick='window.location.reload()'><button class='btn btn-primary btn-sm primary-action' > Agregar XML a Pago</button></a>")
#
#   else:
#     # print("[%s] - %s" % (cliente.codigo_error, cliente.error))
#     frappe.msgprint("ERROR EN TIMBRADO: " + "[%s] - %s" % (cliente.codigo_error, cliente.error))
#
#
# @frappe.whitelist()
# def genera_layout_pago_cfdi(docname,invoice,rfc_emisor):
#   FechaPago = (datetime.now()- timedelta(minutes=360)).isoformat()[0:19]
#
#   c = frappe.get_doc("Payment Entry", docname)
#
#   si = frappe.get_doc("CFDI", invoice)
#   rfc_emisor = si.rfc_emisor
#   url_timbrado = si.url_timbrado
#   user_id = si.user_id
#   user_password = si.user_password
#   webfolder =si.folder
#   RegimenFiscal = si.regimen_fiscal
#   RfcReceptor = si.tax_id.replace('&','&amp;')
#   LugarExpedicion = si.lugar_expedicion
#
#   FormaDePagoP = c.forma_de_pago
#   Monto = '%.2f' %  c.received_amount
#   IdDocumento = c.documento_relacionado
#   MetodoDePagoDR = c.metodo_pago_cfdi
#   # ImpSaldoAnt = '%.2f' % c.references[0].outstanding_amount
#   ImpSaldoAnt = '%.2f' % c.impsaldoanterior
#   # ImpSaldoInsoluto = '%.2f' % (c.references[0].outstanding_amount - c.received_amount )
#   ImpSaldoInsoluto = '%.2f' % (c.impsaldoanterior - c.received_amount )
#   cfdif = """[ReciboPagos]
# LugarExpedicion={LugarExpedicion}
# Fecha={FechaPago}
# [Emisor]
# Rfc={rfc_emisor}
# RegimenFiscal={RegimenFiscal}
# [Receptor]
# Rfc={RfcReceptor}
# [ComplementoPagos]
# Version=1.0
# [Pago#1]
# FechaPago={FechaPago}
# FormaDePagoP={FormaDePagoP}
# MonedaP=MXN
# Monto={Monto}
# DoctoRelacionado.IdDocumento=[{IdDocumento}]
# DoctoRelacionado.MonedaDR=[MXN]
# DoctoRelacionado.MetodoDePagoDR=[{MetodoDePagoDR}]
# DoctoRelacionado.NumParcialidad=[1]
# DoctoRelacionado.ImpSaldoAnt=[{ImpSaldoAnt}]
# DoctoRelacionado.ImpPagado=[{Monto}]
# DoctoRelacionado.ImpSaldoInsoluto=[{ImpSaldoInsoluto}]
# """.format(**locals())
#   frappe.errprint(cfdif)
#   return cfdif;
#
#
# if __name__ == '__main__':
#   timbrado_pago()
#
# @frappe.whitelist()
# def cancelar_pago_cfdi(docname, invoice,debug = True):
#
#   c = frappe.get_doc("Payment Entry", docname)
#
#   si = frappe.get_doc("CFDI", invoice)
#   rfc_emisor = si.rfc_emisor
#   url_timbrado = si.url_timbrado
#   user_id = si.user_id
#   user_password = si.user_password
#
#   params = {'emisorRFC': rfc_emisor, 'UserID': user_id, 'UserPass': user_password}
#   cliente = Cliente(url_timbrado, params, debug)
#
#   # UUID del comprobante a cancelar
#   # uuid = c.documento_relacionado
#   uuid = c.uuid_pago
#
#   if cliente.cancelar(uuid):
#     frappe.msgprint("Cancelacion Exitosa")
#     frappe.db.set_value("Payment Entry",c.name, 'cfdi_status', 'Cancelado')  #RG-asi cambio el status del timbrado
#   else:
#     frappe.msgprint("[%s] - %s" % (cliente.codigo_error, cliente.error))
#
# if __name__ == '__main__':
#   cancelar_pago_cfdi()
# RG-TERMINA MODULO CFDI - Facturacion MODERNA
