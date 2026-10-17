"""Utilidades generales: rutas, fechas en español, formato de horas."""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO"]


def cargar_config():
    with open(RAIZ / "config.json", encoding="utf8") as f:
        return json.load(f)


def ruta(rel):
    """Ruta absoluta a partir de una relativa a la carpeta del proyecto."""
    p = Path(rel)
    return p if p.is_absolute() else RAIZ / p


def parse_fecha(texto, anio):
    """Acepta dd/mm, dd/mm/aaaa o aaaa-mm-dd."""
    texto = texto.strip()
    if "-" in texto and len(texto.split("-")[0]) == 4:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    partes = texto.replace("-", "/").split("/")
    d, m = int(partes[0]), int(partes[1])
    a = int(partes[2]) if len(partes) > 2 else anio
    if a < 100:
        a += 2000
    return date(a, m, d)


def f_corta(d):
    return d.strftime("%d/%m")


def f_larga(d):
    return d.strftime("%d/%m/%Y")


def nombre_dia(d):
    return DIAS[d.weekday()] if d.weekday() < 6 else "DOMINGO"


def fmt_horas(h):
    """6.5 -> '6 y media'; 4 -> '4'; 0.5 -> 'media'."""
    if h is None or h == "":
        return ""
    h = float(h)
    ent = int(h)
    frac = round(h - ent, 4)
    if frac == 0:
        return str(ent)
    if frac == 0.5:
        return "media" if ent == 0 else f"{ent} y media"
    return f"{h:g}"


def lunes_de(d):
    return d - timedelta(days=d.weekday())


def semanas_lun_sab(inicio, fin):
    """Lista de lunes de las semanas (lun-sáb) que tocan el rango [inicio, fin]."""
    lunes = lunes_de(inicio)
    out = []
    while lunes <= fin:
        out.append(lunes)
        lunes += timedelta(days=7)
    return out


def trozos_rotacion(inicio, fin):
    """10/10 a 23/10 -> [(10/10, 17/10), (17/10, 23/10)] (tramos de 7 días)."""
    out, a = [], inicio
    while a < fin:
        b = min(a + timedelta(days=7), fin)
        out.append((a, b))
        a = b
    return out or [(inicio, fin)]


def pedir(texto, defecto=None):
    """input() con valor por defecto."""
    suf = f" [{defecto}]" if defecto not in (None, "") else ""
    r = input(f"{texto}{suf}: ").strip()
    return r if r else (defecto if defecto is not None else "")


def si_no(texto, defecto=True):
    d = "S/n" if defecto else "s/N"
    r = input(f"{texto} ({d}): ").strip().lower()
    if not r:
        return defecto
    return r in ("s", "si", "sí", "y", "yes")
