"""Aplicación SÍNCRONA con PyMongo (MongoClient).

Es un administrador de películas con menú. Cada operación espera la respuesta
de Atlas antes de pasar a la siguiente. Hace lo mismo que app_async.py.

Colecciones:
  - 'movies'      (la original)  -> solo se CONSULTA
  - 'movies_test' (de pruebas)   -> aquí se carga, crea, actualiza y elimina
"""

import time

from pymongo import InsertOne, MongoClient

from config import (
    CANTIDAD_CARGA,
    CANTIDAD_CRUD,
    COLECCION_ORIGEN,
    COLECCION_PRUEBA,
    DB_NAME,
    PIPELINE_GENEROS,
    REPETICIONES_CONSULTAS,
    TAM_LOTE,
    URI,
    dividir_en_lotes,
    generar_peliculas,
    imprimir_consultas,
    leer_entero,
    leer_texto,
    resumen_pelicula,
)


# ---------------------------------------------------------------
# CARGA MASIVA: insertar muchas películas con bulk_write()
# ---------------------------------------------------------------
def carga_masiva(coleccion, peliculas):
    total = 0
    for lote in dividir_en_lotes(peliculas, TAM_LOTE):
        operaciones = [InsertOne(pelicula) for pelicula in lote]
        resultado = coleccion.bulk_write(operaciones)  # un viaje a Atlas por lote
        total += resultado.inserted_count
    return total


# ---------------------------------------------------------------
# CRUD: Create (crear), Read (leer), Update (actualizar), Delete (eliminar)
# ---------------------------------------------------------------
def crear_pelicula(coleccion, pelicula):
    return coleccion.insert_one(pelicula).inserted_id


def leer_pelicula(coleccion, titulo):
    return coleccion.find_one({"title": titulo})


def actualizar_anio(coleccion, titulo, anio):
    return coleccion.update_one(
        {"title": titulo}, {"$set": {"year": anio}}
    ).modified_count


def eliminar_pelicula(coleccion, titulo):
    return coleccion.delete_one({"title": titulo}).deleted_count


def crud_masivo(coleccion, cantidad):
    """Para cada película inventada: crear, leer, actualizar y eliminar (una por una)."""
    for pelicula in generar_peliculas(cantidad):
        titulo = pelicula["title"]
        crear_pelicula(coleccion, pelicula)
        leer_pelicula(coleccion, titulo)
        actualizar_anio(coleccion, titulo, 2027)
        eliminar_pelicula(coleccion, titulo)


# ---------------------------------------------------------------
# CONSULTAS (cada una usa una función distinta de MongoDB)
# ---------------------------------------------------------------
def consulta_por_anio(coleccion, anio):  # filtro simple
    return list(coleccion.find({"year": anio}, {"title": 1, "year": 1}).limit(5))


def consulta_por_genero(coleccion, genero):  # conteo con filtro
    return coleccion.count_documents({"genres": genero})


def consulta_mejores(coleccion):  # ordenar y limitar
    filtro = {
        "imdb.rating": {"$type": "number"}
    }  # solo películas con calificación numérica
    cursor = coleccion.find(filtro, {"title": 1, "imdb.rating": 1})
    return list(cursor.sort("imdb.rating", -1).limit(5))


def consulta_generos(coleccion):  # agregación (agrupar)
    return list(coleccion.aggregate(PIPELINE_GENEROS))


def consultas_varias(coleccion, veces):
    """Ejecuta las 4 consultas 'veces' veces, una tras otra."""
    for _ in range(veces):
        resultados = (
            consulta_por_anio(coleccion, 2000),
            consulta_por_genero(coleccion, "Comedy"),
            consulta_mejores(coleccion),
            consulta_generos(coleccion),
        )
    return resultados


# ---------------------------------------------------------------
# PRUEBA DE RENDIMIENTO (la usa también comparar.py)
# ---------------------------------------------------------------
def prueba_rendimiento(origen, prueba):
    tiempos = {}

    print("\nPASO 1 - CARGA MASIVA")
    print(
        f"  Qué hace: copia {CANTIDAD_CARGA} películas de '{COLECCION_ORIGEN}' a "
        f"'{COLECCION_PRUEBA}', en lotes de {TAM_LOTE} con bulk_write()."
    )
    peliculas = list(origen.find({}).limit(CANTIDAD_CARGA))
    prueba.drop()
    inicio = time.perf_counter()
    total = carga_masiva(prueba, peliculas)
    tiempos["carga_masiva"] = time.perf_counter() - inicio
    print(f"  Resultado: {total} películas en {tiempos['carga_masiva']:.2f} s")

    print("\nPASO 2 - CRUD MASIVO")
    print(
        f"  Qué hace: a {CANTIDAD_CRUD} películas inventadas les hace crear, leer, "
        f"actualizar y eliminar ({CANTIDAD_CRUD * 4} operaciones), una tras otra."
    )
    inicio = time.perf_counter()
    crud_masivo(prueba, CANTIDAD_CRUD)
    tiempos["crud"] = time.perf_counter() - inicio
    print(f"  Resultado: {tiempos['crud']:.2f} s")

    print("\nPASO 3 - CONSULTAS")
    print(
        f"  Qué hace: las 4 consultas (por año, por género, mejores calificadas y "
        f"conteo por género) repetidas {REPETICIONES_CONSULTAS} veces "
        f"({REPETICIONES_CONSULTAS * 4} consultas), una tras otra."
    )
    inicio = time.perf_counter()
    consultas_varias(origen, REPETICIONES_CONSULTAS)
    tiempos["consultas"] = time.perf_counter() - inicio
    print(f"  Resultado: {tiempos['consultas']:.2f} s")
    return tiempos


def correr_prueba():
    """Conecta, ejecuta la prueba de rendimiento y devuelve los tiempos."""
    cliente = MongoClient(URI, serverSelectionTimeoutMS=8000)
    try:
        cliente.admin.command("ping")
        return prueba_rendimiento(
            cliente[DB_NAME][COLECCION_ORIGEN], cliente[DB_NAME][COLECCION_PRUEBA]
        )
    finally:
        cliente.close()


# ---------------------------------------------------------------
# MENÚ
# ---------------------------------------------------------------
MENU = f"""
===== ADMINISTRADOR DE PELÍCULAS (síncrono) =====
CARGA MASIVA
  1. Copiar películas de '{COLECCION_ORIGEN}' a '{COLECCION_PRUEBA}'
CRUD (sobre '{COLECCION_PRUEBA}')
  2. Crear una película
  3. Buscar una película por título
  4. Cambiar el año de una película
  5. Eliminar una película
  6. CRUD masivo (crear, leer, actualizar y eliminar varias películas)
CONSULTAS (sobre '{COLECCION_ORIGEN}')
  7. Películas de un año
  8. Cuántas películas hay de un género
  9. Las 5 mejor calificadas
 10. Los 5 géneros con más películas
 11. Las consultas 7, 8, 9 y 10 juntas (año 2000 y género Comedy)
PRUEBA
 12. Prueba de rendimiento
 13. Borrar todo lo de '{COLECCION_PRUEBA}' (dejarla vacía)
  0. Salir"""


def ejecutar_opcion(opcion, origen, prueba):
    if opcion == "1":
        cantidad = leer_entero(
            f"¿Cuántas películas copiar? (Enter = {CANTIDAD_CARGA}): ", CANTIDAD_CARGA
        )
        print(
            f"Se borrará lo que haya en '{COLECCION_PRUEBA}' y se copiarán {cantidad} películas."
        )
        peliculas = list(origen.find({}).limit(cantidad))
        prueba.drop()
        inicio = time.perf_counter()
        total = carga_masiva(prueba, peliculas)
        print(
            f"Listo: {total} películas copiadas en {time.perf_counter() - inicio:.2f} s."
        )

    elif opcion == "2":
        titulo = leer_texto("Título: ")
        anio = leer_entero("Año (Enter = 2026): ", 2026)
        genero = leer_texto("Género (Enter = Drama): ", "Drama")
        nueva_id = crear_pelicula(
            prueba, {"title": titulo, "year": anio, "genres": [genero]}
        )
        print("Película creada con _id:", nueva_id)

    elif opcion == "3":
        pelicula = leer_pelicula(prueba, leer_texto("Título exacto a buscar: "))
        print(
            resumen_pelicula(pelicula) if pelicula else "No se encontró esa película."
        )

    elif opcion == "4":
        titulo = leer_texto("Título de la película: ")
        anio = leer_entero("Nuevo año: ", 2026)
        print(actualizar_anio(prueba, titulo, anio), "película(s) actualizada(s).")

    elif opcion == "5":
        print(
            eliminar_pelicula(prueba, leer_texto("Título de la película a eliminar: ")),
            "película(s) eliminada(s).",
        )

    elif opcion == "6":
        cantidad = leer_entero(
            f"¿Con cuántas películas? (Enter = {CANTIDAD_CRUD}): ", CANTIDAD_CRUD
        )
        print(
            f"A cada una se le hace: crear, leer, actualizar y eliminar ({cantidad * 4} operaciones)."
        )
        inicio = time.perf_counter()
        crud_masivo(prueba, cantidad)
        print(f"Listo en {time.perf_counter() - inicio:.2f} s.")

    elif opcion == "7":
        anio = leer_entero("Año (Enter = 2000): ", 2000)
        for p in consulta_por_anio(origen, anio):
            print(" -", resumen_pelicula(p))

    elif opcion == "8":
        genero = leer_texto("Género en inglés (Enter = Comedy): ", "Comedy")
        print(f"Hay {consulta_por_genero(origen, genero)} películas de {genero}.")

    elif opcion == "9":
        for p in consulta_mejores(origen):
            print(f" - {p['title']} ({p['imdb']['rating']})")

    elif opcion == "10":
        for g in consulta_generos(origen):
            print(f" - {g['_id']}: {g['total']}")

    elif opcion == "11":
        inicio = time.perf_counter()
        resultados = consultas_varias(origen, 1)
        print(f"Las 4 consultas tardaron {time.perf_counter() - inicio:.2f} s:")
        imprimir_consultas(*resultados)

    elif opcion == "12":
        prueba_rendimiento(origen, prueba)

    elif opcion == "13":
        if (
            leer_texto(
                f"Se borrará TODO en '{COLECCION_PRUEBA}'. ¿Seguro? (s/n): ", "n"
            ).lower()
            == "s"
        ):
            prueba.drop()
            print(f"'{COLECCION_PRUEBA}' quedó vacía.")
        else:
            print("Cancelado.")

    else:
        print("Opción no válida.")


def main():
    cliente = MongoClient(URI, serverSelectionTimeoutMS=8000)
    try:
        cliente.admin.command("ping")  # confirma que hay conexión antes de empezar
        origen = cliente[DB_NAME][COLECCION_ORIGEN]
        prueba = cliente[DB_NAME][COLECCION_PRUEBA]
        print(f"Conectado a Atlas. Base: {DB_NAME}")
        while True:
            print(MENU)
            opcion = leer_texto("Elige una opción: ")
            if opcion == "0":
                break
            try:
                ejecutar_opcion(opcion, origen, prueba)
            except Exception as error:
                print("Ocurrió un error:", error)
    finally:
        cliente.close()


if __name__ == "__main__":
    main()
