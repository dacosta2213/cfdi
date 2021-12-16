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
    SubTotal = '%.2f' % c.precio_traslado
    Total = '%.2f' % c.precio_traslado * 1.16
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

        distancia = dest.distance
        suma_distancia += round(distancia, 2)
		##########################################
		#Obtener informacion de Notra de Entrega
        DN = frappe.get_doc("Delivery Note", dest.delivery_note)
        cant = len(DN.items)
        NumTotalMercancias = str(DN.total_qty).replace(".", "").replace("0", "")
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
                <cartaporte20:Mercancia BienesTransp="{articulo_cps}" Descripcion="{articulo_descripcion}" Cantidad="{articulo_qty}" ClaveUnidad="{articulo_claveUP}" PesoEnKg="{articulo_peso}" MaterialPeligroso="No">
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

    cfdi = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd http://www.sat.gob.mx/CartaPorte20 http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte20.xsd"
    xmlns:cartaporte20="http://www.sat.gob.mx/CartaPorte20" Version="3.3" Serie="{serie}" Folio="{folio}" Fecha="{fecha_actual}" Sello="" FormaPago="{FormaPago}" NoCertificado=""
    xmlns:cfdi="http://www.sat.gob.mx/cfd/3"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Certificado="" CondicionesDePago="CONTADO" SubTotal="{SubTotal}" Moneda="{Currency}" TipoCambio = "{TipoCambio}" Total="{Total}" TipoDeComprobante="{TipoDeComprobante}" MetodoPago="{MetodoPago}" LugarExpedicion="{LugarExpedicion}">""".format(**locals())


    cfdi+= """
    <cfdi:Emisor Rfc="{rfc_emisor}" Nombre="{nombre_emisor}" RegimenFiscal="{regimen_fiscal}"/>
    <cfdi:Receptor Rfc="{tax_id}" Nombre="{nombre_receptor}" UsoCFDI="{uso_cfdi}"/>
    <cfdi:Conceptos>""".format(**locals())

    cfdi += cfdi_items

    cfdi_conceptos = """
    </cfdi:Conceptos>
    <cfdi:Impuestos TotalImpuestosTrasladados="{TotalImpuestosTrasladados}">
        <cfdi:Traslados>""".format(**locals())
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
