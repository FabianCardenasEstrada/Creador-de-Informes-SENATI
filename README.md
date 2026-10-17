# Informes SENATI automáticos (Python + Ollama)

Te pregunta qué hiciste cada día y llena los dos informes oficiales (**Empresa** y **Seminario**)
usando tus plantillas en `plantillas/`. La IA (Ollama, local) solo redacta los textos; las fechas,
horas, totales, marcas del PEA y colores de asistencia los calcula Python.

## Instalación (una sola vez, en la PC de tu casa)
1. Python 3.10 o superior (https://www.python.org, marca "Add Python to PATH").
2. En esta carpeta: `pip install -r requirements.txt`
3. Ollama (https://ollama.com) y el modelo: `ollama pull qwen2.5:7b`
   - Laptop con poca RAM (4–8 GB): `ollama pull qwen2.5:3b` y cambia `"modelo"` en `config.json`.

## Uso
`python main.py`   (o `python main.py --sin-ia` para usar tus textos sin IA)

1. **Registrar un día**: fecha, tipo de día, qué hiciste, horas. Para el seminario pasas la ruta de cada
   ejercicio (.py / .ipynb) y la IA le pone título y lo describe. Siempre puedes aceptar, editar o regenerar.
2. **Generar informe**: indicas fecha de inicio y fin; el programa pregunta lo que falta
   (estado del PEA, tarea más significativa, charla de 5 minutos, comentario de la monitora, nota).
3. Los archivos quedan en `salida/` (.docx y, si hay Word o LibreOffice, también .pdf).

## Archivos que puedes editar
- `config.json`: tus datos, fechas del semestre, modelo de Ollama, texto del área de rotación, colores.
- `datos/pea_piad_iv.json`: operaciones del PEA.
- `datos/diario.json`: lo que registraste cada día. `datos/estado_pea.json`: PEA acumulado (4 = completada, 2 = en desarrollo).
- `recursos/`: imágenes de las firmas. `plantillas/`: formatos oficiales en blanco.

## Importante
- La firma de la monitora solo se coloca si respondes que ya revisó y validó el informe.
- No pegues código ni datos internos de la empresa: los textos de empresa se redactan a nivel general.
- Revisa siempre el documento final antes de entregarlo.
