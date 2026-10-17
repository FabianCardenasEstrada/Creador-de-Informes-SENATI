"""Lectura/escritura de datos: PEA oficial, diario (qué hiciste cada día) y
estado acumulado del PEA (qué operaciones van completadas o en desarrollo)."""
import json
from .util import RAIZ, ruta

ARCH_DIARIO = RAIZ / "datos" / "diario.json"
ARCH_ESTADO = RAIZ / "datos" / "estado_pea.json"

# Tipos de día que se pueden registrar
TIPOS = {
    "empresa": "Día en la empresa",
    "tecnologia": "Clase de Tecnología en SENATI (miércoles)",
    "seminario": "Seminario de Complementación Práctica I (jueves)",
    "falta": "Falta (justificada o injustificada)",
    "feriado": "Feriado / sin actividad",
}


class PEA:
    def __init__(self, cfg):
        with open(ruta(cfg["pea"]), encoding="utf8") as f:
            self.datos = json.load(f)
        self.ops = {o["n"]: o for o in self.datos["operaciones"]}

    def texto(self, n):
        return self.ops[int(n)]["texto"]

    def listado(self):
        return "\n".join(f"{n}. {o['texto']}" for n, o in self.ops.items())

    def validar(self, nums):
        out = []
        for n in nums or []:
            try:
                n = int(n)
            except (TypeError, ValueError):
                continue
            if n in self.ops and n not in out:
                out.append(n)
        return sorted(out)


def _leer(path, defecto):
    if path.exists():
        with open(path, encoding="utf8") as f:
            return json.load(f)
    return defecto


def _guardar(path, datos):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)


class Diario:
    """Un registro por fecha (clave ISO aaaa-mm-dd)."""

    def __init__(self):
        self.datos = _leer(ARCH_DIARIO, {})

    def get(self, fecha):
        return self.datos.get(fecha.isoformat())

    def set(self, fecha, registro):
        self.datos[fecha.isoformat()] = registro
        self.guardar()

    def borrar(self, fecha):
        self.datos.pop(fecha.isoformat(), None)
        self.guardar()

    def guardar(self):
        _guardar(ARCH_DIARIO, self.datos)

    def rango(self, inicio, fin):
        """[(fecha, registro)] ordenado, solo días con registro dentro del rango."""
        from datetime import date
        out = []
        for k, v in sorted(self.datos.items()):
            d = date.fromisoformat(k)
            if inicio <= d <= fin:
                out.append((d, v))
        return out


class EstadoPEA:
    """{'empresa': {'5': 4, '10': 2}, 'seminario': {...}}  (4 = completada, 2 = en desarrollo)."""

    def __init__(self):
        self.datos = _leer(ARCH_ESTADO, {"empresa": {}, "seminario": {}})
        for k in ("empresa", "seminario"):
            self.datos.setdefault(k, {})

    def get(self, doc):
        return {int(n): int(v) for n, v in self.datos[doc].items()}

    def set_todo(self, doc, estado):
        self.datos[doc] = {str(n): int(v) for n, v in sorted(estado.items())}
        self.guardar()

    def guardar(self):
        _guardar(ARCH_ESTADO, self.datos)
