"""Configuración y funciones comunes para la app síncrona y la asíncrona."""
import os

from dotenv import load_dotenv

load_dotenv()

# --- Conexión (viene del archivo .env) ---
URI = os.environ["MONGODB_URI"]
DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLECCION_ORIGEN = os.getenv("COLLECTION_NAME", "movies")        # solo se LEE
COLECCION_PRUEBA = os.getenv("TEST_COLLECTION", "movies_test")   # aquí se ESCRIBE

# --- Parámetros (valores por defecto; en el menú puedes escribir otros) ---
# No son números "mágicos": solo hay que usar suficientes datos para que se note
# la diferencia entre síncrono y asíncrono sin llenar el clúster gratuito (512 MB).
CANTIDAD_CARGA = int(os.getenv("CANTIDAD_CARGA", "2000"))  # películas a copiar
TAM_LOTE = 200               # películas por cada bulk_write (2000 / 200 = 10 lotes)
MAX_CONCURRENTES = 5         # máximo de operaciones al mismo tiempo (Semaphore)

# Solo para la prueba de rendimiento:
CANTIDAD_CRUD = 50           # películas con las que se hace el CRUD masivo
REPETICIONES_CONSULTAS = 5   # veces que se repiten las 4 consultas (= 20 consultas)

# Protección: nunca borrar ni escribir sobre la colección original
if COLECCION_PRUEBA == COLECCION_ORIGEN:
    raise SystemExit(
        "TEST_COLLECTION no puede ser igual a COLLECTION_NAME: "
        "se borraría la colección original."
    )

# Consulta de agregación: cuántas películas hay por género (top 5)
PIPELINE_GENEROS = [
    {"$unwind": "$genres"},
    {"$group": {"_id": "$genres", "total": {"$sum": 1}}},
    {"$sort": {"total": -1}},
    {"$limit": 5},
]


def dividir_en_lotes(lista, tamano):
    """Parte una lista en pedazos de 'tamano' elementos."""
    for i in range(0, len(lista), tamano):
        yield lista[i:i + tamano]


def generar_peliculas(cantidad):
    """Crea películas inventadas para probar el CRUD."""
    return [
        {
            "title": f"Pelicula de prueba {i}",
            "year": 2026,
            "genres": ["Drama"],
            "plot": "Película creada para la práctica.",
        }
        for i in range(cantidad)
    ]


def leer_texto(mensaje, defecto=""):
    """Pregunta algo al usuario. Si solo presiona Enter, usa el valor por defecto."""
    texto = input(mensaje).strip()
    return texto or defecto


def leer_entero(mensaje, defecto):
    """Pregunta un número entero. Si no escribe un número, usa el valor por defecto."""
    texto = input(mensaje).strip()
    return int(texto) if texto.isdigit() else defecto


def resumen_pelicula(pelicula):
    """Convierte una película en una línea de texto legible."""
    generos = ", ".join(pelicula.get("genres", []))
    return f"{pelicula.get('title')} ({pelicula.get('year')}) - géneros: {generos}"


def imprimir_consultas(por_anio, comedias, mejores, generos):
    """Muestra el resultado de las 4 consultas."""
    print("  Películas del año 2000 (5 ejemplos):")
    for p in por_anio:
        print("   -", p["title"])
    print(f"  Total de películas de Comedy: {comedias}")
    print("  Las 5 mejor calificadas en IMDb:")
    for p in mejores:
        print(f"   - {p['title']} ({p['imdb']['rating']})")
    print("  Los 5 géneros con más películas:")
    for g in generos:
        print(f"   - {g['_id']}: {g['total']}")
