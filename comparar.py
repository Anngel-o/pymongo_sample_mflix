"""Ejecuta las dos aplicaciones y compara sus tiempos.

Uso:  python comparar.py
Guarda la tabla en resultados.md para pegarla en el reporte.
"""
import asyncio
from datetime import datetime

import app_async
import app_sync
from config import (
    CANTIDAD_CARGA, CANTIDAD_CRUD, MAX_CONCURRENTES, REPETICIONES_CONSULTAS, TAM_LOTE,
)

PASOS = [
    ("carga_masiva", f"Carga masiva ({CANTIDAD_CARGA} películas, lotes de {TAM_LOTE})"),
    ("crud", f"CRUD de {CANTIDAD_CRUD} películas"),
    ("consultas", f"Consultas ({REPETICIONES_CONSULTAS} rondas de 4)"),
]


def main():
    print("=== APLICACIÓN SÍNCRONA ===")
    tiempos_sync = app_sync.correr_prueba()
    print()
    print("=== APLICACIÓN ASÍNCRONA ===")
    tiempos_async = asyncio.run(app_async.correr_prueba())

    lineas = [
        "| Operación | Síncrona (s) | Asíncrona (s) | Veces más rápida la asíncrona |",
        "|---|---|---|---|",
    ]
    for clave, nombre in PASOS:
        s, a = tiempos_sync[clave], tiempos_async[clave]
        lineas.append(f"| {nombre} | {s:.2f} | {a:.2f} | {s / a:.2f}x |")
    total_s, total_a = sum(tiempos_sync.values()), sum(tiempos_async.values())
    lineas.append(f"| **Total** | **{total_s:.2f}** | **{total_a:.2f}** | **{total_s / total_a:.2f}x** |")

    tabla = "\n".join(lineas)
    print("\n=== COMPARACIÓN ===")
    print(tabla)

    with open("resultados.md", "w", encoding="utf-8") as archivo:
        archivo.write(f"# Resultados ({datetime.now():%Y-%m-%d %H:%M})\n\n")
        archivo.write(f"Concurrencia máxima (Semaphore): {MAX_CONCURRENTES}\n\n")
        archivo.write(tabla + "\n")
    print("\nTabla guardada en resultados.md")


if __name__ == "__main__":
    main()
