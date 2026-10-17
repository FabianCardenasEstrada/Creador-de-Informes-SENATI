"""Asistente de informes SENATI: te pregunta qué hiciste y llena los documentos.

Uso:   python main.py            (con Ollama encendido)
       python main.py --sin-ia   (sin IA: usa tus textos tal cual)
"""
import json
import sys

try:  # evita errores de acentos en la consola de Windows
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from datetime import date, timedelta
from pathlib import Path

from informes.util import (cargar_config, parse_fecha, f_larga, f_corta, nombre_dia,
                           pedir, si_no, RAIZ)
from informes.almacen import PEA, Diario, EstadoPEA, TIPOS
from informes.llm import OllamaLLM, Redactor
from informes.generador import Generador, convertir_pdf

TIPO_POR_DIA = {0: "empresa", 1: "empresa", 2: "tecnologia", 3: "seminario", 4: "empresa", 5: "empresa"}


# ------------------------------------------------------------------ entrada
def multilinea(msg):
    print(f"{msg}  (escribe y presiona Enter; termina con una línea vacía)")
    lineas = []
    while True:
        l = input("  > ").rstrip()
        if not l:
            break
        lineas.append(l)
    return " ".join(lineas).strip()


def elegir(msg, opciones, defecto=1):
    for i, o in enumerate(opciones, 1):
        print(f"  {i}) {o}")
    while True:
        r = pedir(msg, str(defecto))
        if r.isdigit() and 1 <= int(r) <= len(opciones):
            return int(r) - 1
        print("  Opción no válida.")


def pedir_fecha(msg, anio, defecto=None):
    while True:
        r = pedir(msg, defecto)
        try:
            return parse_fecha(r, anio)
        except Exception:
            print("  Fecha no válida. Usa dd/mm o dd/mm/aaaa.")


def parse_nums(texto, pea):
    nums = []
    for p in texto.replace(";", ",").replace(" ", ",").split(","):
        if p.strip().isdigit():
            nums.append(int(p))
    return pea.validar(nums)


def confirmar_texto(titulo, texto, regenerar=None):
    """Muestra un texto y deja aceptarlo, escribir uno propio o regenerarlo."""
    while True:
        print(f"\n--- {titulo} ---\n{texto}\n")
        op = "Enter = aceptar, e = escribir el mío"
        if regenerar:
            op += ", r = regenerar"
        r = input(f"{op}: ").strip().lower()
        if r == "":
            return texto
        if r == "e":
            nuevo = multilinea("Escribe el texto final")
            if nuevo:
                return nuevo
        if r == "r" and regenerar:
            texto = regenerar()


def confirmar_ops(pea, propuestas):
    print("\nOperaciones del PEA propuestas para este día:")
    if propuestas:
        for n in propuestas:
            print(f"  {n}. {pea.texto(n)}")
    else:
        print("  (ninguna)")
    r = input("Enter = aceptar | números separados por coma para cambiar | 0 = ninguna | ? = ver PEA: ").strip()
    while r == "?":
        print(pea.listado())
        r = input("Enter = aceptar | números separados por coma | 0 = ninguna: ").strip()
    if r == "":
        return propuestas
    if r == "0":
        return []
    return parse_nums(r, pea)


def leer_codigo(ruta_txt):
    p = Path(ruta_txt.strip().strip('"').strip("'"))
    if not p.exists():
        return None, None
    if p.suffix.lower() == ".ipynb":
        nb = json.loads(p.read_text(encoding="utf8"))
        celdas = ["".join(c.get("source", [])) for c in nb.get("cells", []) if c.get("cell_type") == "code"]
        return p.name, "\n\n".join(celdas)
    return p.name, p.read_text(encoding="utf8", errors="replace")


# ------------------------------------------------------------------ app
class App:
    def __init__(self, sin_ia=False):
        self.cfg = cargar_config()
        self.anio = self.cfg["semestre"]["anio"]
        self.pea = PEA(self.cfg)
        self.diario = Diario()
        self.estado = EstadoPEA()
        self.gen = Generador(self.cfg, self.pea)
        self.llm = None
        if not sin_ia:
            ia = OllamaLLM(self.cfg)
            ok, modelos = ia.disponible()
            if ok:
                self.llm = ia
                print(f"IA local lista: {ia.modelo}")
            else:
                print("No encontré Ollama o el modelo configurado "
                      f"({self.cfg['ollama']['modelo']}).")
                if modelos:
                    print("  Modelos instalados:", ", ".join(modelos))
                print("  Continuaré SIN IA (usaré tus textos tal cual). Cambia el modelo en config.json si hace falta.")
        else:
            print("Modo sin IA.")
        self.red = Redactor(self.llm, self.pea)

    # -------------------------------------------------------------- registrar día
    def registrar_dia(self):
        fecha = pedir_fecha("Fecha del día (dd/mm)", self.anio)
        if fecha.weekday() == 6:
            print("  Es domingo: no hay hojas para ese día.")
            return
        previo = self.diario.get(fecha)
        if previo and not si_no(f"Ya hay un registro del {f_larga(fecha)} ({previo['tipo']}). ¿Reemplazarlo?", False):
            return
        tipos = list(TIPOS)
        print(f"\n{nombre_dia(fecha).capitalize()} {f_larga(fecha)}. ¿Qué tipo de día fue?")
        tipo = tipos[elegir("Tipo", [TIPOS[t] for t in tipos], tipos.index(TIPO_POR_DIA[fecha.weekday()]) + 1)]
        reg = {"tipo": tipo, "horas": 0}
        horas_def = {"empresa": "6.5", "tecnologia": "6", "seminario": "6.5"}.get(tipo)

        if tipo == "empresa":
            texto = multilinea("¿Qué hiciste hoy en la empresa? (descríbelo como quieras)")
            res = pedir("¿Qué resultado se obtuvo? (Enter para omitir)", "")
            self._redactar_dia(reg, fecha, texto, res)
        elif tipo == "tecnologia":
            texto = multilinea("¿Qué temas vieron hoy en la clase de Tecnología?")
            self._redactar_dia(reg, fecha, texto, "")
            self._asistencia(reg)
        elif tipo == "seminario":
            reg["ejercicios"] = self._ejercicios(fecha)
            reg["operaciones"] = []
            self._asistencia(reg)
        elif tipo == "falta":
            lugar = elegir("¿Falta a...?", ["La empresa", "SENATI"], 1)
            reg["lugar"] = "empresa" if lugar == 0 else "senati"
            just = si_no("¿Fue justificada?", True)
            reg["asistencia"] = "falta_justificada" if just else "falta_injustificada"
            reg["motivo"] = pedir("Motivo (ej. permiso personal; Enter para omitir)", "") if just else ""
            if reg["lugar"] == "senati":
                reg["turno"] = ["M", "T"][elegir("Turno de la falta", ["Mañana", "Tarde"], 1)]
            horas_def = "0"
        else:  # feriado
            reg["descripcion"] = pedir("Descripción (Enter = 'Día feriado / sin actividad.')", "")
            horas_def = "0"

        reg["horas"] = float(pedir("Horas del día", horas_def or "0").replace(",", ".").replace(" y media", ".5"))
        self.diario.set(fecha, reg)
        print(f"  [OK] Guardado: {nombre_dia(fecha)} {f_larga(fecha)}")

    def _redactar_dia(self, reg, fecha, texto, resultado):
        r = self.red.dia(reg["tipo"], fecha, texto, resultado)
        reg["operaciones"] = confirmar_ops(self.pea, r["operaciones"])
        reg["descripcion"] = confirmar_texto(
            "Descripción para el cuadro", r["descripcion"],
            regenerar=lambda: self.red.dia(reg["tipo"], fecha, texto, resultado)["descripcion"])
        reg["texto_original"] = texto

    def _ejercicios(self, fecha):
        lista = []
        print("\nPasa los ejercicios hechos en clase, uno por uno (archivo .py / .ipynb / .java / .txt).")
        while True:
            ruta_txt = input(f"Ruta del ejercicio {len(lista) + 1} (Enter para terminar): ").strip()
            if not ruta_txt:
                break
            nombre, codigo = leer_codigo(ruta_txt)
            if codigo is None:
                print("  No encontré ese archivo. Revisa la ruta (puedes arrastrar el archivo a esta ventana).")
                continue
            notas = pedir("¿Algo que quieras aclarar del ejercicio? (Enter para omitir)", "")
            res = pedir("¿Qué resultado/métrica obtuviste? (ej. exactitud 97 %; Enter para omitir)", "")
            ej = self.red.ejercicio(nombre, codigo, notas, res)
            ej["titulo"] = pedir("Título del ejercicio", ej["titulo"])
            ej["operaciones"] = confirmar_ops(self.pea, ej["operaciones"])
            ej["descripcion"] = confirmar_texto(
                "Descripción", ej["descripcion"],
                regenerar=lambda n=nombre, c=codigo, a=notas, b=res: self.red.ejercicio(n, c, a, b)["descripcion"])
            ej["codigo"] = codigo[:8000]
            ej["resultado"] = res
            ej["archivo"] = nombre
            lista.append(ej)
        return lista

    def _asistencia(self, reg):
        reg["turno"] = ["M", "T"][elegir("Turno en SENATI", ["Mañana (M)", "Tarde (T)"], 1)]
        reg["asistencia"] = ["temprano", "tarde"][elegir("¿Cómo llegaste?", ["A tiempo (verde)", "Con tardanza (amarillo)"], 1)]

    # -------------------------------------------------------------- ver días
    def ver_dias(self):
        ini = pedir_fecha("Desde (dd/mm)", self.anio)
        fin = pedir_fecha("Hasta (dd/mm)", self.anio, f_corta(ini))
        regs = dict(self.diario.rango(ini, fin))
        d = ini
        while d <= fin:
            if d.weekday() < 6:
                r = regs.get(d)
                if r:
                    extra = ""
                    if r["tipo"] == "seminario":
                        extra = f"{len(r.get('ejercicios', []))} ejercicio(s)"
                    elif r.get("descripcion"):
                        extra = r["descripcion"][:60] + "..."
                    print(f"  {nombre_dia(d):<10}{f_larga(d)}  {TIPOS[r['tipo']][:22]:<22} {r['horas']:>4} h  {extra}")
                else:
                    print(f"  {nombre_dia(d):<10}{f_larga(d)}  (sin registrar)")
            d += timedelta(days=1)
        if si_no("¿Borrar algún día?", False):
            f = pedir_fecha("Fecha a borrar", self.anio)
            self.diario.borrar(f)
            print("  Borrado.")

    # -------------------------------------------------------------- PEA
    def menu_pea(self):
        doc = ["empresa", "seminario"][elegir("¿PEA de qué informe?", ["Empresa", "Seminario"], 1)]
        while True:
            est = self.estado.get(doc)
            print(f"\nEstado actual del PEA ({doc}): 4 = completada, 2 = en desarrollo")
            for n in sorted(est):
                print(f"  {n:>2}. [{est[n]}] {self.pea.texto(n)}")
            if not est:
                print("  (vacío)")
            a = elegir("Acción", ["Marcar COMPLETADAS (4)", "Marcar EN DESARROLLO (2)", "Quitar operaciones", "Volver"], 4)
            if a == 3:
                return
            print(self.pea.listado())
            nums = parse_nums(pedir("Números separados por coma", ""), self.pea)
            for n in nums:
                if a == 0:
                    est[n] = 4
                elif a == 1:
                    est[n] = 2
                else:
                    est.pop(n, None)
            self.estado.set_todo(doc, est)

    # -------------------------------------------------------------- generar
    def generar(self, doc):
        titulo = "EMPRESA" if doc == "empresa" else "SEMINARIO"
        print(f"\n=== Informe de {titulo} ===")
        inicio = pedir_fecha("Fecha de INICIO del periodo (dd/mm)", self.anio)
        fin = pedir_fecha("Fecha de FIN del periodo (dd/mm)", self.anio)
        regs = self.diario.rango(inicio, fin)
        if doc == "seminario":
            regs = [(f, r) for f, r in regs if r["tipo"] == "seminario" or r.get("lugar") == "senati"
                    or r["tipo"] == "tecnologia"]
        if not regs:
            print("No hay días registrados en ese periodo. Usa la opción 1 del menú primero.")
            return

        # días sin registrar
        faltan = []
        d = inicio
        while d <= fin:
            if d.weekday() < 6 and not self.diario.get(d) and (doc == "empresa" or d.weekday() == 3):
                faltan.append(f_corta(d))
            d += timedelta(days=1)
        if faltan:
            print("Días sin registrar en ese periodo:", ", ".join(faltan))
            if not si_no("¿Continuar de todos modos?", False):
                return

        # PEA
        previo = self.estado.get(doc)
        tocadas = set()
        for f, r in regs:
            if doc == "seminario" and r["tipo"] != "seminario":
                continue
            tocadas.update(r.get("operaciones", []))
            for ej in r.get("ejercicios", []):
                tocadas.update(ej.get("operaciones", []))
        nuevo = dict(previo)
        if tocadas:
            print("\nOperaciones del PEA trabajadas en este periodo:")
            for n in sorted(tocadas):
                print(f"  {n}. {self.pea.texto(n)}  (antes: {previo.get(n, 'no registrada')})")
            r = pedir("¿Cuáles siguen EN DESARROLLO (2)? (números; Enter = todas completadas)", "")
            en_curso = set(parse_nums(r, self.pea)) if r else set()
            for n in tocadas:
                if n in en_curso:
                    nuevo[n] = 2 if previo.get(n) != 4 else 4
                else:
                    nuevo[n] = 4
        extra = pedir("¿Operaciones que ya completaste en informes anteriores y no aparecen? (números; Enter = ninguna)", "")
        for n in parse_nums(extra, self.pea):
            nuevo.setdefault(n, 4)
        if not nuevo:
            print("  Aviso: el PEA quedará vacío (no hay operaciones registradas).")

        # tarea más significativa
        ejercicios = [(f, ej) for f, r in regs if r["tipo"] == "seminario" for ej in r.get("ejercicios", [])]
        if ejercicios:
            print("\nEjercicios del seminario en este periodo (elige la tarea más significativa):")
            i = elegir("Ejercicio", [f"{ej['titulo']} ({f_corta(f)})" for f, ej in ejercicios], 1)
            ej = ejercicios[i][1]
        else:
            print("\nNo hay ejercicios de seminario registrados en este periodo.")
            desc = multilinea("Describe la tarea más significativa")
            ej = self.red.ejercicio("tarea", desc, "", "")
            ej["codigo"] = desc
        ops_txt = "; ".join(self.pea.texto(n) for n in ej.get("operaciones", []))
        narr = self.red.narrativa(ej, ops_txt)
        narr["por_que"] = confirmar_texto(
            "Por qué se eligió la tarea / qué operaciones cumplió", narr["por_que"],
            regenerar=lambda: self.red.narrativa(ej, ops_txt)["por_que"])
        print("\nPasos del proceso:")
        for s in narr["proceso"]:
            print("  -", s)
        if not si_no("¿Están bien los pasos?", True):
            narr["proceso"] = [l.strip() for l in multilinea("Escribe los pasos separados por ';'").split(";") if l.strip()]

        datos = {"inicio": inicio, "fin": fin, "registros": regs, "estado": nuevo, "narr": narr}

        if doc == "empresa":
            tema = pedir("Tema de la charla de 5 minutos (SST/SGA)", "")
            notas = pedir("¿Qué se dijo en la charla? (Enter para omitir)", "")
            seg = self.red.seguridad(tema, notas) if tema else "Se participó en la charla de cinco minutos de seguridad y medio ambiente."
            datos["seguridad"] = confirmar_texto("Seguridad e higiene", seg,
                                                 regenerar=(lambda: self.red.seguridad(tema, notas)) if tema else None)
            cierre = self.red.cierre(ej, narr)
            cierre["resultados"] = confirmar_texto("Resultados de la ejecución", cierre["resultados"],
                                                   regenerar=lambda: self.red.cierre(ej, narr)["resultados"])
            datos["cierre"] = cierre
            datos["comentario_monitora"] = pedir("Comentario de la monitora (Enter = ninguno)", "")
            datos["nota"] = pedir("Nota del instructor (Enter = vacía)", "")
            datos["firmar_monitora"] = si_no("¿La monitora ya revisó y validó este informe? (se colocará su firma)", False)

        nombre = f"Informe_{'Empresa' if doc == 'empresa' else 'Seminario'}_{inicio:%d-%m}_a_{fin:%d-%m}.docx"
        salida = RAIZ / "salida" / nombre
        salida.parent.mkdir(exist_ok=True)
        (self.gen.empresa if doc == "empresa" else self.gen.seminario)(datos, salida)
        self.estado.set_todo(doc, nuevo)
        print(f"\n[OK] Informe creado: {salida}")
        pdf = convertir_pdf(salida)
        print(f"[OK] PDF creado: {pdf}" if pdf else "  (No pude crear el PDF automáticamente: abre el .docx en Word y usa Guardar como PDF.)")
        print("  Revisa el documento antes de entregarlo.")

    # -------------------------------------------------------------- menú
    def menu(self):
        while True:
            print("\n=========== Informes SENATI ===========")
            op = elegir("¿Qué quieres hacer?", [
                "Registrar un día (qué hiciste)",
                "Ver / borrar días registrados",
                "Generar informe de EMPRESA",
                "Generar informe de SEMINARIO",
                "Ver / ajustar operaciones del PEA",
                "Salir"], 1)
            try:
                if op == 0:
                    self.registrar_dia()
                elif op == 1:
                    self.ver_dias()
                elif op == 2:
                    self.generar("empresa")
                elif op == 3:
                    self.generar("seminario")
                elif op == 4:
                    self.menu_pea()
                else:
                    return
            except (KeyboardInterrupt, EOFError):
                print("\n  (cancelado)")


if __name__ == "__main__":
    App(sin_ia="--sin-ia" in sys.argv).menu()
