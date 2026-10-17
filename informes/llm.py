"""Conexión con Ollama (IA local) y funciones de redacción.

Solo usa la librería estándar de Python (urllib), no necesita instalar nada.
Si la IA no responde, cada función devuelve un resultado simple basado en lo que
escribió el estudiante para que el proceso nunca se detenga.
"""
import json
import re
import urllib.error
import urllib.request

SISTEMA = """Eres un asistente que redacta informes de formación práctica de un estudiante de SENATI (Perú) de la carrera de Ingeniería de Software con Inteligencia Artificial.
Reglas obligatorias:
- Escribe en español, en tercera persona impersonal y en pasado ("Se desarrolló...", "Se configuró...").
- Usa ÚNICAMENTE los datos que entrega el estudiante. NO inventes herramientas, librerías, cifras, métricas, nombres de personas, clientes ni resultados que no estén en los datos.
- No incluyas información confidencial de la empresa (nombres de clientes, datos personales, credenciales ni código fuente).
- Redacción clara, técnica y sencilla, sin adornos ni frases de relleno.
- Responde SOLO con un objeto JSON válido, sin texto adicional ni markdown."""


class ErrorIA(Exception):
    pass


class OllamaLLM:
    def __init__(self, cfg):
        o = cfg["ollama"]
        self.url = o["url"].rstrip("/")
        self.modelo = o["modelo"]
        self.temp = o.get("temperatura", 0.3)
        self.timeout = o.get("timeout_segundos", 600)

    def disponible(self):
        try:
            with urllib.request.urlopen(self.url + "/api/tags", timeout=5) as r:
                nombres = [m["name"] for m in json.load(r).get("models", [])]
            return any(n == self.modelo or n.split(":")[0] == self.modelo for n in nombres), nombres
        except Exception:
            return False, []

    def chat_json(self, user):
        cuerpo = {
            "model": self.modelo,
            "stream": False,
            "format": "json",
            "options": {"temperature": self.temp, "num_ctx": 8192},
            "messages": [
                {"role": "system", "content": SISTEMA},
                {"role": "user", "content": user},
            ],
        }
        req = urllib.request.Request(
            self.url + "/api/chat",
            data=json.dumps(cuerpo).encode("utf8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                texto = json.load(r)["message"]["content"]
        except (urllib.error.URLError, TimeoutError, KeyError) as e:
            raise ErrorIA(f"No se pudo usar Ollama: {e}")
        return extraer_json(texto)


def extraer_json(texto):
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?|```$", "", texto, flags=re.M).strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", texto, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    raise ErrorIA("La IA no devolvió un JSON válido")


# --------------------------------------------------------------------------
class Redactor:
    """Convierte lo que cuenta el estudiante en los textos de cada cuadro."""

    def __init__(self, llm, pea):
        self.llm = llm          # OllamaLLM, un mock de pruebas o None (modo sin IA)
        self.pea = pea

    # ---- núcleo ----------------------------------------------------------
    def _pedir(self, prompt):
        if self.llm is None:
            return None
        for intento in range(2):
            try:
                return self.llm.chat_json(prompt)
            except ErrorIA as e:
                ultimo = e
        print(f"   (aviso: {ultimo}; se usa un texto básico que puedes corregir)")
        return None

    @staticmethod
    def _oracion(t):
        t = (t or "").strip()
        if not t:
            return ""
        t = t[0].upper() + t[1:]
        return t if t[-1] in ".!?" else t + "."

    # ---- días -----------------------------------------------------------
    def dia(self, tipo, fecha, texto, resultado=""):
        """Devuelve {'operaciones': [...], 'descripcion': '...'}"""
        lugar = {"empresa": "trabajo en la empresa", "tecnologia": "clase de Tecnología en SENATI"}.get(tipo, tipo)
        prompt = f"""#TAREA: dia
Registro del {fecha:%d/%m/%Y}: {lugar}.
Lo que contó el estudiante: "{texto}"
Resultado indicado por el estudiante (puede estar vacío): "{resultado}"

Operaciones del PEA (plan de aprendizaje) disponibles:
{self.pea.listado()}

Devuelve un JSON con exactamente estas claves:
"operaciones": lista con los números del PEA que se cumplieron CLARAMENTE ese día (lista vacía si ninguna aplica; no fuerces coincidencias),
"descripcion": 2 a 4 oraciones que expliquen qué se hizo, para qué se hizo y qué se obtuvo. Si el estudiante no indicó un resultado, cierra con una oración neutra sobre el avance logrado sin inventar datos."""
        r = self._pedir(prompt)
        if isinstance(r, dict) and r.get("descripcion"):
            return {"operaciones": self.pea.validar(r.get("operaciones")),
                    "descripcion": str(r["descripcion"]).strip()}
        base = self._oracion(texto)
        if resultado:
            base += " " + self._oracion("Resultado obtenido: " + resultado)
        return {"operaciones": [], "descripcion": base}

    def ejercicio(self, nombre, codigo, notas="", resultado=""):
        """Analiza el código de un ejercicio de clase."""
        prompt = f"""#TAREA: ejercicio
Ejercicio realizado en clase (archivo: {nombre}).
Código:
```
{codigo[:7000]}
```
Notas del estudiante (pueden estar vacías): "{notas}"
Resultado o métricas indicados por el estudiante (pueden estar vacíos): "{resultado}"

Operaciones del PEA disponibles:
{self.pea.listado()}

Devuelve un JSON con estas claves:
"titulo": título corto y descriptivo en una línea (ej. "Clasificación de casos de cáncer de mama mediante Regresión Logística"),
"operaciones": números del PEA que cumple claramente este ejercicio,
"descripcion": 1 o 2 oraciones: qué problema resuelve, con qué técnica o librerías y qué se obtuvo (solo menciona cifras si están en los datos del estudiante),
"librerias": lista de librerías realmente usadas en el código,
"pasos": 6 a 10 pasos en orden de ejecución, frases cortas, basados en el código."""
        r = self._pedir(prompt)
        if isinstance(r, dict) and r.get("titulo"):
            return {
                "titulo": str(r["titulo"]).strip(),
                "operaciones": self.pea.validar(r.get("operaciones")),
                "descripcion": str(r.get("descripcion", "")).strip(),
                "librerias": [str(x) for x in r.get("librerias", [])][:10],
                "pasos": [str(x) for x in r.get("pasos", [])][:12],
            }
        return {"titulo": nombre.rsplit(".", 1)[0].replace("_", " ").strip().capitalize(),
                "operaciones": [], "descripcion": self._oracion(notas or "Se desarrolló el ejercicio indicado en clase"),
                "librerias": [], "pasos": []}

    # ---- narrativa del informe -------------------------------------------
    def narrativa(self, ej, operaciones_txt):
        """Texto principal de la tarea más significativa + pasos + diagrama."""
        prompt = f"""#TAREA: narrativa
Tarea más significativa elegida (ejercicio de clase):
Título: {ej['titulo']}
Resumen: {ej.get('descripcion','')}
Librerías: {', '.join(ej.get('librerias', []))}
Pasos detectados: {json.dumps(ej.get('pasos', []), ensure_ascii=False)}
Código:
```
{ej.get('codigo','')[:6000]}
```
Operaciones del PEA que cumple: {operaciones_txt or 'no especificadas'}

Devuelve un JSON con estas claves:
"tarea": nombre de la tarea en una línea,
"por_que": un párrafo de 4 a 5 oraciones: por qué se eligió esta tarea, qué operaciones del PEA cumplió (nómbralas) y cómo se ejecutó,
"proceso": lista de 8 a 12 pasos de la secuencia lógica de ejecución (frases cortas que empiezan con verbo en infinitivo),
"herramientas": lista de equipos, software y librerías realmente usados (máximo 8),
"diagrama": lista de 9 a 12 nodos de un diagrama de flujo, cada uno {{"t": título de máximo 4 palabras, "d": detalle de máximo 6 palabras}}."""
        r = self._pedir(prompt)
        if isinstance(r, dict) and r.get("proceso"):
            return {
                "tarea": str(r.get("tarea") or ej["titulo"]).strip(),
                "por_que": str(r.get("por_que", "")).strip(),
                "proceso": [str(x).strip() for x in r["proceso"]][:14],
                "herramientas": [str(x).strip() for x in r.get("herramientas", [])][:10],
                "diagrama": [n for n in r.get("diagrama", []) if isinstance(n, dict) and n.get("t")][:14],
            }
        pasos = ej.get("pasos") or ["Desarrollar el ejercicio indicado en clase"]
        return {
            "tarea": ej["titulo"],
            "por_que": ej.get("descripcion", ""),
            "proceso": pasos,
            "herramientas": ["Computadora de escritorio o laptop", "Python 3", "Visual Studio Code"] + ej.get("librerias", []),
            "diagrama": [{"t": p[:28], "d": ""} for p in pasos[:10]],
        }

    def cierre(self, ej, narr):
        prompt = f"""#TAREA: cierre
Tarea realizada: {narr['tarea']}
Resumen: {ej.get('descripcion','')}
Pasos: {json.dumps(narr['proceso'], ensure_ascii=False)}
Resultado indicado por el estudiante (puede estar vacío): "{ej.get('resultado','')}"

Devuelve un JSON con estas claves:
"resultados": un párrafo de 3 a 4 oraciones sobre si se logró el objetivo y la operatividad del programa (sin inventar cifras),
"recomendaciones": lista de 3 a 4 recomendaciones breves y realistas para mejorar o mantener el trabajo."""
        r = self._pedir(prompt)
        if isinstance(r, dict) and r.get("resultados"):
            return {"resultados": str(r["resultados"]).strip(),
                    "recomendaciones": [str(x).strip() for x in r.get("recomendaciones", [])][:5]}
        return {"resultados": "Se logró desarrollar y ejecutar el programa correctamente, cumpliendo el objetivo planteado.",
                "recomendaciones": ["Continuar practicando con otros conjuntos de datos.",
                                    "Mantener ordenado el código fuente para facilitar mejoras."]}

    def seguridad(self, tema, notas):
        prompt = f"""#TAREA: seguridad
Charla de cinco minutos de seguridad (SST/SGA) recibida por el estudiante.
Tema: {tema}
Notas del estudiante (pueden estar vacías): "{notas}"

Devuelve un JSON con la clave "parrafo": 2 o 3 oraciones que describan el tema tratado y la medida o recomendación principal, usando solo lo indicado."""
        r = self._pedir(prompt)
        if isinstance(r, dict) and r.get("parrafo"):
            return str(r["parrafo"]).strip()
        return self._oracion(f"La charla de 5 minutos trató sobre «{tema}». {notas}".strip())
