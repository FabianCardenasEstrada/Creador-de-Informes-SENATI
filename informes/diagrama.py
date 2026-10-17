"""Dibuja el diagrama de flujo de la tarea más significativa como imagen PNG."""
import math
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

AZUL = "#0B3C8C"
AZUL_CLARO = "#E8EEF9"
VERDE = "#1F7A4D"
VERDE_CLARO = "#E6F4EC"


def dibujar(nodos, salida, ancho_cm=16.0, alto_cm=10.0, titulo=None):
    """nodos: lista de {'t': titulo, 'd': detalle}. Se agregan 'Inicio' y 'Fin'."""
    pasos = [{"t": "Inicio", "d": "", "tipo": "borde"}]
    pasos += [{"t": n.get("t", ""), "d": n.get("d", ""), "tipo": "paso"} for n in nodos]
    pasos += [{"t": "Fin", "d": "", "tipo": "borde"}]
    n = len(pasos)

    columnas = 1 if (n <= 7 or alto_cm / ancho_cm > 1.1) else 2
    filas = math.ceil(n / columnas)
    fig_w, fig_h = ancho_cm / 2.54, alto_cm / 2.54
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    margen_y = 0.04
    util_h = 1 - 2 * margen_y
    paso_y = util_h / filas
    alto_caja = min(paso_y * 0.72, 0.13)
    ancho_caja = 0.66 if columnas == 1 else 0.44
    xs = [0.5] if columnas == 1 else [0.26, 0.74]

    # Serpentina: columna 1 de arriba a abajo; columna 2 de abajo a arriba
    pos = []
    for i in range(n):
        col = i // filas
        k = i % filas
        if col % 2 == 1:
            k = filas - 1 - k
        y = 1 - margen_y - paso_y * (k + 0.5)
        pos.append((xs[col], y))

    for (x, y), p in zip(pos, pasos):
        borde = p["tipo"] == "borde"
        color_l = VERDE if borde else AZUL
        relleno = VERDE_CLARO if borde else AZUL_CLARO
        h = alto_caja * (0.62 if borde else 1)
        w = ancho_caja * (0.45 if borde else 1)
        caja = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                              boxstyle="round,pad=0.004,rounding_size=%s" % (0.03 if borde else 0.012),
                              linewidth=1.1, edgecolor=color_l, facecolor=relleno)
        ax.add_patch(caja)
        if borde:
            ax.text(x, y, p["t"], ha="center", va="center", fontsize=9.5, fontweight="bold", color=color_l)
        else:
            t = textwrap.fill(p["t"], 32 if columnas == 1 else 24)
            d = textwrap.fill(p["d"], 44 if columnas == 1 else 32) if p["d"] else ""
            if d:
                ax.text(x, y + h * 0.18, t, ha="center", va="center", fontsize=9, fontweight="bold", color=AZUL)
                ax.text(x, y - h * 0.22, d, ha="center", va="center", fontsize=7.2, color="#333333")
            else:
                ax.text(x, y, t, ha="center", va="center", fontsize=9, fontweight="bold", color=AZUL)

    for i in range(n - 1):
        (x1, y1), (x2, y2) = pos[i], pos[i + 1]
        h1 = alto_caja * (0.62 if pasos[i]["tipo"] == "borde" else 1) / 2
        h2 = alto_caja * (0.62 if pasos[i + 1]["tipo"] == "borde" else 1) / 2
        if abs(x1 - x2) < 1e-6:
            if y2 < y1:
                a, b = (x1, y1 - h1 - 0.004), (x2, y2 + h2 + 0.004)
            else:
                a, b = (x1, y1 + h1 + 0.004), (x2, y2 - h2 - 0.004)
        else:  # salto entre columnas (misma altura)
            w1 = ancho_caja * (0.45 if pasos[i]["tipo"] == "borde" else 1) / 2
            w2 = ancho_caja * (0.45 if pasos[i + 1]["tipo"] == "borde" else 1) / 2
            a, b = (x1 + w1 + 0.004, y1), (x2 - w2 - 0.004, y2)
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=8, linewidth=1.0, color="#444444"))

    if titulo:
        ax.text(0.5, 0.995, titulo, ha="center", va="top", fontsize=7.5, color="#555555", style="italic")
    fig.savefig(salida, bbox_inches=None, pad_inches=0, facecolor="white")
    plt.close(fig)
    return salida
