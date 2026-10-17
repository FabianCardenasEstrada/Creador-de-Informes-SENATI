"""Genera ambos informes con datos de ejemplo, sin Ollama, para probar el formato."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from informes.util import cargar_config, RAIZ
from informes.almacen import PEA
from informes.generador import Generador, convertir_pdf

cfg = cargar_config()
pea = PEA(cfg)
gen = Generador(cfg, pea)

ej1 = {"titulo": "Clasificación de casos de cáncer de mama mediante Regresión Logística",
       "operaciones": [10], "descripcion": "Se entrenó un modelo de Regresión Logística con el dataset de cáncer de mama de scikit-learn y se evaluó su exactitud con datos de prueba.",
       "librerias": ["scikit-learn", "numpy", "pandas"], "pasos": []}
ej2 = {"titulo": "Clasificación de vinos mediante una red neuronal con TensorFlow",
       "operaciones": [4, 12], "descripcion": "Se creó una red neuronal con Keras para clasificar tipos de vino y se comprobó su funcionamiento con una predicción individual.",
       "librerias": ["tensorflow", "keras"], "pasos": []}

R = [
    (date(2026, 10, 12), {"tipo": "empresa", "horas": 6.5, "operaciones": [1],
        "descripcion": "Se organizaron y limpiaron listados de datos de cursos mediante Pandas para su posterior envío. Se obtuvo un archivo ordenado y listo para su uso en el proceso de envío de correos."}),
    (date(2026, 10, 13), {"tipo": "empresa", "horas": 6.5, "operaciones": [],
        "descripcion": "Se revisó el funcionamiento de un programa de envío de mensajes y se corrigieron errores de formato. Se logró que el envío de prueba se realizara sin fallas."}),
    (date(2026, 10, 14), {"tipo": "tecnologia", "horas": 6, "operaciones": [], "turno": "M", "asistencia": "temprano",
        "descripcion": "Se desarrolló la clase de Tecnología sobre redes neuronales artificiales: estructura de una neurona, funciones de activación y capas. Se comprendió el flujo de información en una red."}),
    (date(2026, 10, 15), {"tipo": "seminario", "horas": 6.5, "turno": "M", "asistencia": "tarde", "ejercicios": [ej1, ej2], "operaciones": []}),
    (date(2026, 10, 16), {"tipo": "empresa", "horas": 6.5, "operaciones": [5],
        "descripcion": "Se elaboraron gráficos de seguimiento con Matplotlib a partir de los datos de la semana. Se obtuvieron gráficos claros para el reporte interno."}),
    (date(2026, 10, 17), {"tipo": "empresa", "horas": 4, "operaciones": [],
        "descripcion": "Se probó un script de automatización de reportes y se documentaron los pasos de uso. Se dejó el script funcionando para su uso diario."}),
    (date(2026, 10, 19), {"tipo": "falta", "lugar": "empresa", "horas": 0, "asistencia": "falta_justificada", "motivo": "un permiso personal"}),
    (date(2026, 10, 21), {"tipo": "falta", "lugar": "senati", "horas": 0, "turno": "M", "asistencia": "falta_injustificada", "motivo": ""}),
    (date(2026, 10, 22), {"tipo": "seminario", "horas": 6.5, "turno": "M", "asistencia": "temprano", "ejercicios": [ej1], "operaciones": []}),
]

narr = {
    "tarea": ej1["titulo"],
    "por_que": "La tarea más significativa fue el desarrollo de un programa de aprendizaje supervisado para clasificar casos de cáncer de mama mediante Regresión Logística. Se eligió porque permitió aplicar los conocimientos adquiridos sobre preparación de datos, entrenamiento de modelos y evaluación de resultados. Cumplió la operación «Crea programas con algoritmos de aprendizaje supervisado» del PEA. Su ejecución consistió en cargar el dataset, entrenar el modelo y evaluar su exactitud.",
    "proceso": ["Importar las librerías necesarias", "Cargar el conjunto de datos de cáncer de mama", "Identificar variables y objetivo", "Dividir los datos en entrenamiento y prueba", "Escalar las características", "Entrenar el modelo de Regresión Logística", "Realizar predicciones con los datos de prueba", "Calcular la exactitud y el reporte de clasificación", "Realizar una predicción individual"],
    "herramientas": ["Computadora de escritorio o laptop", "Python 3", "Visual Studio Code", "scikit-learn", "numpy y pandas"],
    "diagrama": [{"t": "Importar librerías", "d": "sklearn, numpy, pandas"}, {"t": "Cargar dataset", "d": "load_breast_cancer()"},
                 {"t": "Separar variables", "d": "X (características), y (clase)"}, {"t": "Análisis exploratorio", "d": "forma, nombres, clases"},
                 {"t": "Dividir train / test", "d": "80 % / 20 %"}, {"t": "Escalar datos", "d": "StandardScaler"},
                 {"t": "Entrenar modelo", "d": "LogisticRegression.fit()"}, {"t": "Predecir en test", "d": "model.predict()"},
                 {"t": "Evaluar modelo", "d": "exactitud y reporte"}, {"t": "Predicción individual", "d": "un registro nuevo"}],
}
cierre = {"resultados": "Se logró desarrollar y ejecutar correctamente el modelo de clasificación. El programa permitió entrenar, evaluar y realizar predicciones, cumpliendo el objetivo planteado.",
          "recomendaciones": ["Probar distintos parámetros del modelo.", "Evaluar con métricas adicionales.", "Mantener el código organizado."]}

out = RAIZ / "salida"
out.mkdir(exist_ok=True)

estado_e = {1: 4, 5: 4, 10: 4, 12: 2, 4: 2}
d = {"inicio": date(2026, 10, 10), "fin": date(2026, 10, 23), "registros": R, "estado": estado_e,
     "narr": narr, "cierre": cierre,
     "seguridad": "La charla de 5 minutos trató sobre la Vida Plástica y el impacto ambiental del uso inadecuado de plásticos. Se recomendó reducir su uso y segregar correctamente los residuos.",
     "comentario_monitora": "", "nota": "", "firmar_monitora": False}
gen.empresa(d, out / "demo_empresa.docx")

d2 = {"inicio": date(2026, 10, 15), "fin": date(2026, 10, 22), "registros": R, "estado": {4: 4, 10: 4, 12: 2},
      "narr": narr}
gen.seminario(d2, out / "demo_seminario.docx")
print("OK")
for f in ("demo_empresa.docx", "demo_seminario.docx"):
    print(f, convertir_pdf(out / f))
