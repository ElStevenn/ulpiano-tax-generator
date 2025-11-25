from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
from xml.dom import minidom
from typing import Any, Optional

from .versions import MODEL_XML_NAMESPACE, MODEL_XSD_VERSION
from .normalization import (
    normalize_date,
    normalize_decimal,
    decimal_to_xml_text,
)


def _pretty_xml(elem: Element) -> str:
    rough_string = tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def render_xml_650(data: dict, generation_id: str, timestamp_iso: str) -> str:
    ns = MODEL_XML_NAMESPACE["650"]
    def E(tag: str) -> str:
        return f"{{{ns}}}{tag}"

    root = Element(E("ISD650"), attrib={
        "schemaVersion": MODEL_XSD_VERSION["650"],
        "generatedAt": timestamp_iso,
        "declaracionId": generation_id,
    })

    # Presentador
    presenter = data.get("presenter") or {}
    pres_el = SubElement(root, E("Presentador"))
    SubElement(pres_el, E("NIF")).text = _txt(presenter.get("nif"))
    SubElement(pres_el, E("NombreRazonSocial")).text = _txt(_name_or_business(presenter))
    dom = presenter.get("domicilio") or {}
    dom_el = SubElement(pres_el, E("Domicilio"))
    _opt_text(dom_el, E("Via"), dom.get("via"))
    _opt_text(dom_el, E("Numero"), dom.get("numero"))
    _opt_text(dom_el, E("Piso"), dom.get("piso"))
    _opt_text(dom_el, E("CP"), dom.get("cp"))
    _opt_text(dom_el, E("Municipio"), dom.get("municipio"))
    _opt_text(dom_el, E("Provincia"), dom.get("provincia"))
    _opt_text(dom_el, E("Pais"), dom.get("pais"))

    # Decujus
    dec = data.get("decedent") or {}
    dec_el = SubElement(root, E("Decujus"))
    _opt_text(dec_el, E("NIF"), dec.get("nif"))
    _opt_text(dec_el, E("FechaDevengo"), normalize_date(dec.get("fechaFallecimiento")))
    _opt_text(dec_el, E("CADevengo"), dec.get("caDevengo"))

    # Heir List
    heirs = data.get("heirs") or []
    heirs_el = SubElement(root, E("HeirList"))
    for h in heirs:
        h_el = SubElement(heirs_el, E("Heir"))
        _opt_text(h_el, E("NIF"), h.get("nif"))
        _opt_text(h_el, E("NombreCompleto"), _full_name(h))
        _opt_text(h_el, E("Parentesco"), h.get("parentesco"))
        _opt_text(h_el, E("GradoDiscapacidadPct"), _dec_xml(h.get("gradoDiscapacidadPct")))
        _opt_text(h_el, E("PorcentajeParticipacionPct"), _dec_xml(h.get("porcentajeParticipacionPct")))

    # Asset List
    assets = data.get("assets") or []
    assets_el = SubElement(root, E("AssetList"))
    for a in assets:
        a_el = SubElement(assets_el, E("Asset"))
        _opt_text(a_el, E("Tipo"), a.get("tipo"))
        _opt_text(a_el, E("Descripcion"), a.get("descripcion"))
        _opt_text(a_el, E("Valor"), _dec_xml(a.get("valor")))
        _opt_text(a_el, E("CargasODebenes"), _dec_xml(a.get("cargasODebenes")))
        _opt_text(a_el, E("EsViviendaHabitual"), _bool_xml(a.get("esViviendaHabitual")))
        _opt_text(a_el, E("PorcentajeTitularidadDecujusPct"), _dec_xml(a.get("porcentajeTitularidadDecujusPct")))

    # Reducciones
    deds = data.get("deductions") or {}
    reds_el = SubElement(root, E("Reducciones"))
    _opt_text(reds_el, E("Parentesco"), _dec_xml(deds.get("reduccionParentesco")))
    _opt_text(reds_el, E("Discapacidad"), _dec_xml(deds.get("reduccionDiscapacidad")))
    _opt_text(reds_el, E("EmpresaFamiliar"), _dec_xml(deds.get("reduccionEmpresaFamiliar")))
    _opt_text(reds_el, E("SeguroVida"), _dec_xml(deds.get("reduccionSeguroVida")))

    # Autoliquidacion
    aut = data.get("autoliquidation") or {}
    aut_el = SubElement(root, E("Autoliquidacion"))
    _opt_text(aut_el, E("BaseImponible"), _dec_xml(aut.get("baseImponible")))
    _opt_text(aut_el, E("Reducciones"), _dec_xml(aut.get("reducciones")))
    _opt_text(aut_el, E("BaseLiquidable"), _dec_xml(aut.get("baseLiquidable")))
    _opt_text(aut_el, E("CuotaIntegra"), _dec_xml(aut.get("cuotaIntegra")))
    _opt_text(aut_el, E("Bonificaciones"), _dec_xml(aut.get("bonificaciones")))
    _opt_text(aut_el, E("CuotaLiquida"), _dec_xml(aut.get("cuotaLiquida")))
    _opt_text(aut_el, E("Resultado"), _dec_xml(aut.get("resultado")))

    # Pago
    pay_el = SubElement(root, E("Pago"))
    _opt_text(pay_el, E("Forma"), aut.get("formaPago"))
    _opt_text(pay_el, E("IBAN"), (aut.get("iban") or None))
    _opt_text(pay_el, E("NRC"), (aut.get("nrc") or None))

    return _pretty_xml(root)


def render_xml_651(data: dict, generation_id: str, timestamp_iso: str) -> str:
    ns = MODEL_XML_NAMESPACE["651"]
    def E(tag: str) -> str:
        return f"{{{ns}}}{tag}"

    root = Element(E("ISD651"), attrib={
        "schemaVersion": MODEL_XSD_VERSION["651"],
        "generatedAt": timestamp_iso,
        "declaracionId": generation_id,
    })

    # Presentador
    presenter = data.get("presenter") or {}
    pres_el = SubElement(root, E("Presentador"))
    SubElement(pres_el, E("NIF")).text = _txt(presenter.get("nif"))
    SubElement(pres_el, E("NombreRazonSocial")).text = _txt(_name_or_business(presenter))

    # Donante
    donor = data.get("donor") or {}
    donor_el = SubElement(root, E("Donante"))
    _opt_text(donor_el, E("NIF"), donor.get("nif"))
    _opt_text(donor_el, E("NombreCompleto"), _full_name(donor))
    _opt_text(donor_el, E("EsResidente"), _bool_xml(donor.get("esResidente")))

    # Donatarios
    donees = data.get("donees") or []
    donees_el = SubElement(root, E("Donatarios"))
    for d in donees:
        d_el = SubElement(donees_el, E("Donatario"))
        _opt_text(d_el, E("NIF"), d.get("nif"))
        _opt_text(d_el, E("NombreCompleto"), _full_name(d))
        _opt_text(d_el, E("Parentesco"), d.get("parentesco"))
        _opt_text(d_el, E("GradoDiscapacidadPct"), _dec_xml(d.get("gradoDiscapacidadPct")))
        _opt_text(d_el, E("PorcentajeParticipacionPct"), _dec_xml(d.get("porcentajeParticipacionPct")))

    # Donaciones
    donations = data.get("donations") or []
    dons_el = SubElement(root, E("DonacionList"))
    for dn in donations:
        dn_el = SubElement(dons_el, E("Donacion"))
        _opt_text(dn_el, E("Tipo"), dn.get("tipo"))
        _opt_text(dn_el, E("Descripcion"), dn.get("descripcion"))
        _opt_text(dn_el, E("Valor"), _dec_xml(dn.get("valor")))
        _opt_text(dn_el, E("Fecha"), normalize_date(dn.get("fechaDonacion")))

    # Documentación notarial
    doc = data.get("documentacionNotarial") or {}
    if doc:
        doc_el = SubElement(root, E("DocumentacionNotarial"))
        _opt_text(doc_el, E("TipoDocumento"), doc.get("tipoDocumento"))
        _opt_text(doc_el, E("Notario"), doc.get("notario"))
        _opt_text(doc_el, E("Protocolo"), doc.get("protocolo"))
        _opt_text(doc_el, E("FechaEscritura"), normalize_date(doc.get("fechaEscritura")))

    # Autoliquidacion
    aut = data.get("autoliquidation") or {}
    aut_el = SubElement(root, E("Autoliquidacion"))
    _opt_text(aut_el, E("BaseImponible"), _dec_xml(aut.get("baseImponible")))
    _opt_text(aut_el, E("Reducciones"), _dec_xml(aut.get("reducciones")))
    _opt_text(aut_el, E("BaseLiquidable"), _dec_xml(aut.get("baseLiquidable")))
    _opt_text(aut_el, E("CuotaIntegra"), _dec_xml(aut.get("cuotaIntegra")))
    _opt_text(aut_el, E("Bonificaciones"), _dec_xml(aut.get("bonificaciones")))
    _opt_text(aut_el, E("CuotaLiquida"), _dec_xml(aut.get("cuotaLiquida")))
    _opt_text(aut_el, E("Resultado"), _dec_xml(aut.get("resultado")))

    # Pago
    pay_el = SubElement(root, E("Pago"))
    _opt_text(pay_el, E("Forma"), aut.get("formaPago"))
    _opt_text(pay_el, E("IBAN"), (aut.get("iban") or None))
    _opt_text(pay_el, E("NRC"), (aut.get("nrc") or None))

    return _pretty_xml(root)


def _txt(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _opt_text(parent: Element, tag: str, value: Any) -> None:
    text = _txt(value)
    if text is not None:
        SubElement(parent, tag).text = text


def _full_name(person: dict) -> Optional[str]:
    parts = [
        person.get("primerApellido"),
        person.get("segundoApellido"),
        person.get("nombre"),
    ]
    parts = [p for p in parts if p]
    if not parts:
        return None
    return " ".join(str(p).strip() for p in parts if str(p).strip())


def _name_or_business(presenter: dict) -> Optional[str]:
    razon = presenter.get("razonSocial")
    if razon:
        return str(razon).strip()
    return _full_name(presenter)


def _dec_xml(value: Any) -> Optional[str]:
    dec = normalize_decimal(value, digits=2)
    return decimal_to_xml_text(dec)


def _bool_xml(value: Any) -> Optional[str]:
    if value is None:
        return None
    return "true" if bool(value) else "false"


