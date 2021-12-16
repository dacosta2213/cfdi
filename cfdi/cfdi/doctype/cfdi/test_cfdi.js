<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd http://www.sat.gob.mx/CartaPorte20 http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte20/CartaPorte20.xsd"
    xmlns:cartaporte20="http://www.sat.gob.mx/CartaPorte20" Version="3.3" Serie="MATDT.YYYY." Folio="MAT-DT-2021-00001" Fecha="2021-11-07T16:10:49" Sello="" FormaPago="01" NoCertificado=""
    xmlns:cfdi="http://www.sat.gob.mx/cfd/3"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Certificado="" CondicionesDePago="CONTADO" SubTotal="52500.0" Moneda="MXN" TipoCambio = "1" Total="60900.00" TipoDeComprobante="I" MetodoPago="PUE" LugarExpedicion="44800">
    <cfdi:Emisor Rfc="KIN110125V35" Nombre="KIRE INFORMATICA SA DE CV" RegimenFiscal="601"/>
    <cfdi:Receptor Rfc="XAXX010101000" Nombre="AGRAZ INDUSTRIAL" UsoCFDI="G01"/>
    <cfdi:Conceptos>
        <cfdi:Concepto ClaveProdServ="43201830" NoIdentificacion="DISCO DE ESTADO SOLIDO" Cantidad="5.0" ClaveUnidad="H87" Unidad="Nos." Descripcion="DISCO DE ESTADO SOLIDO" ValorUnitario="10500.00" Importe="52500.00">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado Base="52500.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="8400.00"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>
    </cfdi:Conceptos>
    <cfdi:Impuestos TotalImpuestosTrasladados="8400.0">
        <cfdi:Traslados>
                <cfdi:Traslado Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="8400.0"/>
        </cfdi:Traslados>
    </cfdi:Impuestos>
    <cfdi:Complemento>
        <cartaporte20:CartaPorte Version="2.0" TranspInternac="No" TotalDistRec="24.412">
            <cartaporte20:Ubicaciones>
            <cartaporte20:Ubicacion TipoUbicacion="Origen" RFCRemitenteDestinatario="KIN110125V35" FechaHoraSalidaLlegada="2021-11-07T10:00:00">
                <cartaporte20:Domicilio Calle="AV. LOPEZ MATEOS SUR " NumeroExterior="5359" Colonia="0347" Estado="JAL" Pais="MEX" CodigoPostal="45080" />
            </cartaporte20:Ubicacion>
            <cartaporte20:Ubicacion TipoUbicacion="Destino" RFCRemitenteDestinatario="XAXX010101000" FechaHoraSalidaLlegada="2021-11-07T10:15:19" DistanciaRecorrida="11.18">
               <cartaporte20:Domicilio Calle="GARBANZO No. " NumeroExterior="636" Estado="JAL" Pais="MEX" CodigoPostal="44470" />
            </cartaporte20:Ubicacion>
           </cartaporte20:Ubicaciones>
            <cartaporte20:Mercancias PesoBrutoTotal="5.0" UnidadPeso="XUN" NumTotalMercancias="5.0" >
                <cartaporte20:Mercancia BienesTransp="43201830" Descripcion="DISCO DE ESTADO SOLIDO" Cantidad="5.0" ClaveUnidad="XUN" PesoEnKg="5.0" MaterialPeligroso="None">
                     <cartaporte20:CantidadTransporta Cantidad="5.0"/>
                </cartaporte20:Mercancia>
                <cartaporte20:Autotransporte PermSCT="None" NumPermisoSCT="None">
                    <cartaporte20:IdentificacionVehicular ConfigVehicular="None" PlacaVM="JLE-1956" AnioModeloVM="2014" />
                    <cartaporte20:Seguros AseguraRespCivil="AXA Seguros" PolizaRespCivil="1956884725"/>
                </cartaporte20:Autotransporte>
            </cartaporte20:Mercancias>
            <cartaporte20:FiguraTransporte>
                <cartaporte20:TiposFigura TipoFigura="01" RFCFigura="VAAM130719H60" NumLicencia="a234567890">
                </cartaporte20:TiposFigura>
            </cartaporte20:FiguraTransporte>
        </cartaporte20:CartaPorte>
    </cfdi:Complemento>
</cfdi:Comprobante>
