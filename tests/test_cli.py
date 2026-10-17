"""Prueba de extremo a extremo del asistente con una IA simulada y respuestas automáticas."""
import builtins, json, sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main as M
from informes import almacen
from informes.util import RAIZ

# --- datos aislados para no tocar los reales
almacen.ARCH_DIARIO = RAIZ / "datos" / "_test_diario.json"
almacen.ARCH_ESTADO = RAIZ / "datos" / "_test_estado.json"
M.Diario.__init__.__globals__["ARCH_DIARIO"] = almacen.ARCH_DIARIO
M.EstadoPEA.__init__.__globals__["ARCH_ESTADO"] = almacen.ARCH_ESTADO
for f in (almacen.ARCH_DIARIO, almacen.ARCH_ESTADO):
    f.unlink(missing_ok=True)


class FakeLLM:
    modelo = "fake"
    def __init__(self, cfg): pass
    def disponible(self): return True, ["fake"]
    def chat_json(self, p):
        t = p.split("\n")[0]
        if "dia" in t:
            return {"operaciones": [1], "descripcion": "Se procesaron listados de cursos con Pandas para su envío. Se obtuvo un archivo ordenado y listo para usar."}
        if "ejercicio" in t:
            return {"titulo": "Clasificación de cáncer de mama con Regresión Logística", "operaciones": [10],
                    "descripcion": "Se entrenó un modelo de Regresión Logística con scikit-learn y se evaluó su exactitud.",
                    "librerias": ["scikit-learn"], "pasos": ["Cargar el dataset", "Dividir los datos", "Escalar", "Entrenar", "Evaluar"]}
        if "narrativa" in t:
            return {"tarea": "Clasificación de cáncer de mama", "por_que": "Se eligió porque integra todo el flujo de Machine Learning.",
                    "proceso": ["Cargar el dataset", "Dividir los datos", "Escalar", "Entrenar", "Evaluar"],
                    "herramientas": ["Python 3", "scikit-learn"],
                    "diagrama": [{"t": "Cargar dataset", "d": "load_breast_cancer"}, {"t": "Dividir datos", "d": "80/20"}, {"t": "Entrenar", "d": "fit"}]}
        if "cierre" in t:
            return {"resultados": "Se logró el objetivo y el programa quedó operativo.", "recomendaciones": ["Probar otros parámetros."]}
        if "seguridad" in t:
            return {"parrafo": "La charla trató sobre el uso responsable del plástico."}
        return {}

M.OllamaLLM = FakeLLM

colas = {
    "Fecha del día": ["12/10", "15/10"],
    "Ruta del ejercicio": [str(Path(__file__).parent / "ejemplo_cancer_mama.py"), ""],
    "  > ": ["Procesé listados de cursos con pandas", "", ],
    "resultado se obtuvo": ["archivo ordenado"],
    "Resultado/métrica": ["exactitud de 97 %"],
    "INICIO del periodo": ["10/10", "10/10"],
    "FIN del periodo": ["23/10", "23/10"],
    "Continuar de todos modos": ["s", "s"],
    "Tema de la charla": ["Vida Plástica"],
    "validó este informe": ["s"],
    "Comentario de la monitora": ["Buen desempeño."],
}
def fake_input(prompt=""):
    for clave, cola in colas.items():
        if clave in prompt and cola:
            r = cola.pop(0)
            print(f"{prompt}{r}   <-- auto")
            return r
    print(f"{prompt}<Enter>   <-- auto")
    return ""
builtins.input = fake_input

app = M.App()
app.registrar_dia()   # lunes empresa
app.registrar_dia()   # jueves seminario
app.generar("empresa")
app.generar("seminario")
print("ESTADO:", app.estado.datos)
