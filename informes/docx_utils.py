"""Funciones para editar las plantillas .docx sin alterar su formato original."""
import copy
from lxml import etree
from docx.oxml.ns import qn

NS_WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
NS_V = "urn:schemas-microsoft-com:vml"
NS_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"


def W(tag):
    return qn("w:" + tag)


# ---------------------------------------------------------------- creación
def mk_run(texto="", bold=False, sz=18, italic=False, tab=False):
    r = etree.Element(W("r"))
    rpr = etree.SubElement(r, W("rPr"))
    if bold:
        etree.SubElement(rpr, W("b"))
    else:
        etree.SubElement(rpr, W("b")).set(W("val"), "0")
    if italic:
        etree.SubElement(rpr, W("i"))
    etree.SubElement(rpr, W("sz")).set(W("val"), str(sz))
    etree.SubElement(rpr, W("szCs")).set(W("val"), str(sz))
    etree.SubElement(rpr, W("lang")).set(W("val"), "es-MX")
    if tab:
        etree.SubElement(r, W("tab"))
    if texto:
        t = etree.SubElement(r, W("t"))
        t.text = texto
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return r


def mk_par(runs, jc=None, left=None, hanging=None, before=0, after=0, line=252, keep_next=False):
    p = etree.Element(W("p"))
    ppr = etree.SubElement(p, W("pPr"))
    if keep_next:
        etree.SubElement(ppr, W("keepNext"))
    if left is not None:
        tabs = etree.SubElement(ppr, W("tabs"))
        tb = etree.SubElement(tabs, W("tab"))
        tb.set(W("val"), "left")
        tb.set(W("pos"), str(left))
    sp = etree.SubElement(ppr, W("spacing"))
    sp.set(W("before"), str(before))
    sp.set(W("after"), str(after))
    sp.set(W("line"), str(line))
    sp.set(W("lineRule"), "auto")
    if left is not None:
        ind = etree.SubElement(ppr, W("ind"))
        ind.set(W("left"), str(left))
        if hanging:
            ind.set(W("hanging"), str(hanging))
    if jc:
        etree.SubElement(ppr, W("jc")).set(W("val"), jc)
    for r in runs:
        p.append(r)
    return p


def par_simple(texto, bold=False, sz=18, jc="both", after=60, **kw):
    return mk_par([mk_run(texto, bold=bold, sz=sz)], jc=jc, after=after, **kw)


def par_vineta(texto, sz=18, nivel_left=360, caracter="•", after=20):
    return mk_par([mk_run(caracter, sz=sz), mk_run("", sz=sz, tab=True), mk_run(texto, sz=sz)],
                  jc="left", left=nivel_left, hanging=360, after=after)


def par_salto_pagina():
    """Párrafo mínimo con salto de página antes (no deja línea vacía arriba)."""
    p = etree.Element(W("p"))
    ppr = etree.SubElement(p, W("pPr"))
    etree.SubElement(ppr, W("pageBreakBefore"))
    sp = etree.SubElement(ppr, W("spacing"))
    sp.set(W("before"), "0")
    sp.set(W("after"), "0")
    sp.set(W("line"), "20")
    sp.set(W("lineRule"), "exact")
    rpr = etree.SubElement(ppr, W("rPr"))
    etree.SubElement(rpr, W("sz")).set(W("val"), "2")
    return p


# ---------------------------------------------------------------- consulta
def texto_de(el):
    return "".join(t.text or "" for t in el.iter(W("t")))


def es_vacio(p):
    """Párrafo sin texto, sin dibujos, sin saltos de página ni secciones."""
    if p.tag != W("p"):
        return False
    if texto_de(p).strip():
        return False
    for tag in ("drawing", "pict", "sectPr", "fldChar", "object"):
        if next(p.iter(W(tag)), None) is not None:
            return False
    for br in p.iter(W("br")):
        if br.get(W("type")) in ("page", "column"):
            return False
    if next(p.iter("{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent"), None) is not None:
        return False
    return True


def parrafos_cuerpo(doc):
    return [e for e in doc.element.body.iterchildren() if e.tag == W("p")]


def buscar_parrafo(doc, inicio):
    """Primer párrafo del cuerpo cuyo texto empieza con `inicio`."""
    for p in parrafos_cuerpo(doc):
        if texto_de(p).strip().startswith(inicio):
            return p
    raise KeyError(f"No se encontró el párrafo «{inicio}» en la plantilla")


def keep_next(p):
    """Agrega keepNext a un párrafo respetando el orden de los elementos de pPr."""
    ppr = p.find(W("pPr"))
    if ppr is None:
        ppr = etree.Element(W("pPr"))
        p.insert(0, ppr)
    if ppr.find(W("keepNext")) is not None:
        return
    estilo = ppr.find(W("pStyle"))
    if estilo is not None:
        estilo.addnext(etree.Element(W("keepNext")))
    else:
        ppr.insert(0, etree.Element(W("keepNext")))


def quitar(el):
    if el is not None and el.getparent() is not None:
        el.getparent().remove(el)


def vacios_siguientes(el):
    """Párrafos vacíos consecutivos justo después de `el`."""
    out = []
    sig = el.getnext()
    while sig is not None and es_vacio(sig):
        out.append(sig)
        sig = sig.getnext()
    return out


def rellenar_despues(par, elementos, quitar_vacios=True):
    """Inserta `elementos` tras `par`, eliminando los párrafos vacíos que había."""
    if quitar_vacios:
        for v in vacios_siguientes(par):
            quitar(v)
    ancla = par
    for e in elementos:
        ancla.addnext(e)
        ancla = e
    return ancla


# ---------------------------------------------------------------- celdas
def limpiar_celda(tc):
    for p in list(tc.findall(W("p"))):
        tc.remove(p)


def poner_en_celda(tc, parrafos):
    """Reemplaza el contenido de la celda por `parrafos` (lista de w:p)."""
    limpiar_celda(tc)
    if not parrafos:
        parrafos = [etree.Element(W("p"))]
    for p in parrafos:
        tc.append(p)


def pintar(tc, color_hex):
    tcpr = tc.find(W("tcPr"))
    if tcpr is None:
        tcpr = etree.Element(W("tcPr"))
        tc.insert(0, tcpr)
    shd = tcpr.find(W("shd"))
    if shd is None:
        shd = etree.SubElement(tcpr, W("shd"))
    shd.set(W("val"), "clear")
    shd.set(W("color"), "auto")
    shd.set(W("fill"), color_hex)


def celdas_unicas(fila):
    vistos, out = [], []
    for c in fila.cells:
        if c._tc not in vistos:
            vistos.append(c._tc)
            out.append(c)
    return out


def ancho_celda_twips(tc, defecto=9000):
    tcw = tc.find(W("tcPr") + "/" + W("tcW")) if tc.find(W("tcPr")) is not None else None
    try:
        return int(tcw.get(W("w")))
    except Exception:
        return defecto


def alto_fila_twips(tr, defecto=None):
    trpr = tr.find(W("trPr"))
    if trpr is not None:
        h = trpr.find(W("trHeight"))
        if h is not None:
            try:
                return int(h.get(W("val")))
            except Exception:
                pass
    return defecto


# ---------------------------------------------------------------- texto dentro de formas flotantes
def texto_en_formas(contenedor, textos, sz=16, clave=None):
    """Escribe `textos[i]` dentro de la i-ésima forma flotante del contenedor
    (ordenadas de arriba hacia abajo). Sirve para las casillas de conteo."""
    anchors = [a for a in contenedor.iter("{%s}anchor" % NS_WP)]
    # ordenar por posición vertical y luego horizontal
    def clave_defecto(a):
        try:
            v = int(a.find(".//{%s}positionV/{%s}posOffset" % (NS_WP, NS_WP)).text)
            h = int(a.find(".//{%s}positionH/{%s}posOffset" % (NS_WP, NS_WP)).text)
        except Exception:
            v = h = 0
        return (v, h)
    anchors_ord = sorted(anchors, key=clave or clave_defecto)
    # Fallback VML: mismos shapes, mismo orden documental
    vml = [e for e in contenedor.iter() if e.tag in ("{%s}rect" % NS_V, "{%s}roundrect" % NS_V)]
    orden_doc = {id(a): i for i, a in enumerate(anchors)}
    for k, a in enumerate(anchors_ord):
        if k >= len(textos) or textos[k] in (None, ""):
            continue
        txt = str(textos[k])
        wsp = a.find(".//{%s}wsp" % NS_WPS)
        if wsp is not None and wsp.find("{%s}txbx" % NS_WPS) is None:
            tx = etree.Element("{%s}txbx" % NS_WPS)
            tx.append(_contenido_caja(txt, sz))
            body_pr = wsp.find("{%s}bodyPr" % NS_WPS)
            body_pr.addprevious(tx)
            for atr in ("lIns", "tIns", "rIns", "bIns"):
                body_pr.set(atr, "0")
            body_pr.set("anchor", "ctr")
        i = orden_doc[id(a)]
        if i < len(vml) and vml[i].find("{%s}textbox" % NS_V) is None:
            tb = etree.SubElement(vml[i], "{%s}textbox" % NS_V)
            tb.set("inset", "0,0,0,0")
            tb.append(_contenido_caja(txt, sz))


def _contenido_caja(txt, sz):
    c = etree.Element(W("txbxContent"))
    c.append(mk_par([mk_run(txt, bold=True, sz=sz)], jc="center", line=240))
    return c
