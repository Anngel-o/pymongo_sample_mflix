"""Aplicación ASÍNCRONA con PyMongo Async (AsyncMongoClient).

Es un administrador de películas con menú, igual que app_sync.py, pero cuando
hay muchas operaciones las lanza a la vez en lugar de una por una:
  - asyncio.TaskGroup -> carga masiva (cada lote es una tarea)
  - asyncio.gather()  -> CRUD masivo y consultas
  - asyncio.Semaphore -> limita cuántas operaciones van al mismo tiempo
  - bulk_write()      -> inserta cada lote de películas
Requiere Python 3.11 o superior (por TaskGroup).

Colecciones:
  - 'movies'      (la original)  -> solo se CONSULTA
  - 'movies_test' (de pruebas)   -> aquí se carga, crea, actualiza y elimina
"""
import asyncio
import time

from pymongo import AsyncMongoClient, InsertOne

from config import (
    CANTIDAD_CARGA, CANTIDAD_CRUD, COLECCION_ORIGEN, COLECCION_PRUEBA,
    DB_NAME, MAX_CONCURRENTES, PIPELINE_GENEROS, REPETICIONES_CONSULTAS,
    TAM_LOTE, URI, dividir_en_lotes, generar_peliculas, imprimir_consultas,
    leer_entero, leer_texto, resumen_pelicula,
)


async def con_limite(semaforo, corrutina):
    """Espera un 'lugar' en el semáforo y luego ejecuta la operación."""
    async with semaforo:
        return await corrutina


async def preguntar_texto(mensaje, defecto=""):
    # input() bloquea, así que se ejecuta en otro hilo para no frenar asyncio
    return await asyncio.to_thread(leer_texto, mensaje, defecto)


async def preguntar_entero(mensaje, defecto):
    return await asyncio.to_thread(leer_entero, mensaje, defecto)


# ---------------------------------------------------------------
# CARGA MASIVA: TaskGroup + Semaphore + bulk_write()
# ---------------------------------------------------------------
async def insertar_lote(coleccion, lote):
    operaciones = [InsertOne(pelicula) for pelicula in lote]
    resultado = await coleccion.bulk_write(operaciones)
    return resultado.inserted_count


async def carga_masiva(coleccion, peliculas):
    semaforo = asyncio.Semaphore(MAX_CONCURRENTES)
    async with asyncio.TaskGroup() as grupo:
        # Cada lote es una tarea; el semáforo deja correr solo unas cuantas a la vez
        tareas = [
            grupo.create_task(con_limite(semaforo, insertar_lote(coleccion, lote)))
            for lote in dividir_en_lotes(peliculas, TAM_LOTE)
        ]
    # Al salir del 'async with' todas las tareas ya terminaron
    return sum(tarea.result() for tarea in tareas)


# ---------------------------------------------------------------
# CRUD: Create (crear), Read (leer), Update (actualizar), Delete (eliminar)
# ---------------------------------------------------------------
async def crear_pelicula(coleccion, pelicula):
    resultado = await coleccion.insert_one(pelicula)
    return resultado.inserted_id


async def leer_pelicula(coleccion, titulo):
    return await coleccion.find_one({"title": titulo})


async def actualizar_anio(coleccion, titulo, anio):
    resultado = await coleccion.update_one({"title": titulo}, {"$set": {"year": anio}})
    return resultado.modified_count


async def eliminar_pelicula(coleccion, titulo):
    resultado = await coleccion.delete_one({"title": titulo})
    return resultado.deleted_count


async def ciclo_crud(coleccion, pelicula):
    """Crear, leer, actualizar y eliminar UNA película (en ese orden)."""
    titulo = pelicula["title"]
    await crear_pelicula(coleccion, pelicula)
    await leer_pelicula(coleccion, titulo)
    await actualizar_anio(coleccion, titulo, 2027)
    await eliminar_pelicula(coleccion, titulo)


async def crud_masivo(coleccion, cantidad):
    """El ciclo CRUD de varias películas, todas a la vez (gather + Semaphore)."""
    semaforo = asyncio.Semaphore(MAX_CONCURRENTES)
    ciclos = [
        con_limite(semaforo, ciclo_crud(coleccion, pelicula))
        for pelicula in generar_peliculas(cantidad)
    ]
    await asyncio.gather(*ciclos)


# ---------------------------------------------------------------
# CONSULTAS (cada una usa una función distinta de MongoDB)
# ---------------------------------------------------------------
async def consulta_por_anio(coleccion, anio):           # filtro simple
    # find() no lleva await; el cursor se convierte en lista con to_list()
    return await coleccion.find({"year": anio}, {"title": 1, "year": 1}).limit(5).to_list()


async def consulta_por_genero(coleccion, genero):       # conteo con filtro
    return await coleccion.count_documents({"genres": genero})


async def consulta_mejores(coleccion):                  # ordenar y limitar
    filtro = {"imdb.rating": {"$type": "number"}}        # solo calificaciones numéricas
    cursor = coleccion.find(filtro, {"title": 1, "imdb.rating": 1})
    return await cursor.sort("imdb.rating", -1).limit(5).to_list()


async def consulta_generos(coleccion):                  # agregación (agrupar)
    cursor = await coleccion.aggregate(PIPELINE_GENEROS)  # aggregate sí lleva await
    return await cursor.to_list()


async def consultas_varias(coleccion, veces):
    """Lanza las 4 consultas 'veces' veces, todas a la vez con gather()."""
    semaforo = asyncio.Semaphore(MAX_CONCURRENTES)
    pedidos = []
    for _ in range(veces):
        pedidos.append(con_limite(semaforo, consulta_por_anio(coleccion, 2000)))
        pedidos.append(con_limite(semaforo, consulta_por_genero(coleccion, "Comedy")))
        pedidos.append(con_limite(semaforo, consulta_mejores(coleccion)))
        pedidos.append(con_limite(semaforo, consulta_generos(coleccion)))
    resultados = await asyncio.gather(*pedidos)   # resultados en el mismo orden
    return resultados[-4:]                         # los de la última ronda


# ---------------------------------------------------------------
# PRUEBA DE RENDIMIENTO (la usa también comparar.py)
# ---------------------------------------------------------------
async def prueba_rendimiento(origen, prueba):
    tiempos = {}

    print("\nPASO 1 - CARGA MASIVA")
    print(f"  Qué hace: copia {CANTIDAD_CARGA} películas de '{COLECCION_ORIGEN}' a "
          f"'{COLECCION_PRUEBA}', en lotes de {TAM_LOTE} con bulk_write(), "
          f"hasta {MAX_CONCURRENTES} lotes a la vez.")
    peliculas = await origen.find({}).limit(CANTIDAD_CARGA).to_list()
    await prueba.drop()
    inicio = time.perf_counter()
    total = await carga_masiva(prueba, peliculas)
    tiempos["carga_masiva"] = time.perf_counter() - inicio
    print(f"  Resultado: {total} películas en {tiempos['carga_masiva']:.2f} s")

    print("\nPASO 2 - CRUD MASIVO")
    print(f"  Qué hace: a {CANTIDAD_CRUD} películas inventadas les hace crear, leer, "
          f"actualizar y eliminar ({CANTIDAD_CRUD * 4} operaciones), "
          f"{MAX_CONCURRENTES} películas a la vez.")
    inicio = time.perf_counter()
    await crud_masivo(prueba, CANTIDAD_CRUD)
    tiempos["crud"] = time.perf_counter() - inicio
    print(f"  Resultado: {tiempos['crud']:.2f} s")

    print("\nPASO 3 - CONSULTAS")
    print(f"  Qué hace: las 4 consultas (por año, por género, mejores calificadas y "
          f"conteo por género) repetidas {REPETICIONES_CONSULTAS} veces "
          f"({REPETICIONES_CONSULTAS * 4} consultas), {MAX_CONCURRENTES} a la vez.")
    inicio = time.perf_counter()
    await consultas_varias(origen, REPETICIONES_CONSULTAS)
    tiempos["consultas"] = time.perf_counter() - inicio
    print(f"  Resultado: {tiempos['consultas']:.2f} s")
    return tiempos


async def correr_prueba():
    """Conecta, ejecuta la prueba de rendimiento y devuelve los tiempos."""
    cliente = AsyncMongoClient(URI, serverSelectionTimeoutMS=8000)
    try:
        await cliente.admin.command("ping")
        return await prueba_rendimiento(cliente[DB_NAME][COLECCION_ORIGEN],
                                        cliente[DB_NAME][COLECCION_PRUEBA])
    finally:
        await cliente.close()


# ---------------------------------------------------------------
# MENÚ
# ---------------------------------------------------------------
MENU = f"""
===== ADMINISTRADOR DE PELÍCULAS (asíncrono) =====
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


async def ejecutar_opcion(opcion, origen, prueba):
    if opcion == "1":
        cantidad = await preguntar_entero(f"¿Cuántas películas copiar? (Enter = {CANTIDAD_CARGA}): ", CANTIDAD_CARGA)
        print(f"Se borrará lo que haya en '{COLECCION_PRUEBA}' y se copiarán {cantidad} películas.")
        peliculas = await origen.find({}).limit(cantidad).to_list()
        await prueba.drop()
        inicio = time.perf_counter()
        total = await carga_masiva(prueba, peliculas)
        print(f"Listo: {total} películas copiadas en {time.perf_counter() - inicio:.2f} s.")

    elif opcion == "2":
        titulo = await preguntar_texto("Título: ")
        anio = await preguntar_entero("Año (Enter = 2026): ", 2026)
        genero = await preguntar_texto("Género (Enter = Drama): ", "Drama")
        nueva_id = await crear_pelicula(prueba, {"title": titulo, "year": anio, "genres": [genero]})
        print("Película creada con _id:", nueva_id)

    elif opcion == "3":
        pelicula = await leer_pelicula(prueba, await preguntar_texto("Título exacto a buscar: "))
        print(resumen_pelicula(pelicula) if pelicula else "No se encontró esa película.")

    elif opcion == "4":
        titulo = await preguntar_texto("Título de la película: ")
        anio = await preguntar_entero("Nuevo año: ", 2026)
        print(await actualizar_anio(prueba, titulo, anio), "película(s) actualizada(s).")

    elif opcion == "5":
        titulo = await preguntar_texto("Título de la película a eliminar: ")
        print(await eliminar_pelicula(prueba, titulo), "película(s) eliminada(s).")

    elif opcion == "6":
        cantidad = await preguntar_entero(f"¿Con cuántas películas? (Enter = {CANTIDAD_CRUD}): ", CANTIDAD_CRUD)
        print(f"A cada una se le hace: crear, leer, actualizar y eliminar ({cantidad * 4} operaciones).")
        inicio = time.perf_counter()
        await crud_masivo(prueba, cantidad)
        print(f"Listo en {time.perf_counter() - inicio:.2f} s.")

    elif opcion == "7":
        anio = await preguntar_entero("Año (Enter = 2000): ", 2000)
        for p in await consulta_por_anio(origen, anio):
            print(" -", resumen_pelicula(p))

    elif opcion == "8":
        genero = await preguntar_texto("Género en inglés (Enter = Comedy): ", "Comedy")
        print(f"Hay {await consulta_por_genero(origen, genero)} películas de {genero}.")

    elif opcion == "9":
        for p in await consulta_mejores(origen):
            print(f" - {p['title']} ({p['imdb']['rating']})")

    elif opcion == "10":
        for g in await consulta_generos(origen):
            print(f" - {g['_id']}: {g['total']}")

    elif opcion == "11":
        inicio = time.perf_counter()
        resultados = await consultas_varias(origen, 1)
        print(f"Las 4 consultas tardaron {time.perf_counter() - inicio:.2f} s:")
        imprimir_consultas(*resultados)

    elif opcion == "12":
        await prueba_rendimiento(origen, prueba)

    elif opcion == "13":
        respuesta = await preguntar_texto(f"Se borrará TODO en '{COLECCION_PRUEBA}'. ¿Seguro? (s/n): ", "n")
        if respuesta.lower() == "s":
            await prueba.drop()
            print(f"'{COLECCION_PRUEBA}' quedó vacía.")
        else:
            print("Cancelado.")

    else:
        print("Opción no válida.")


async def main():
    cliente = AsyncMongoClient(URI, serverSelectionTimeoutMS=8000)
    try:
        await cliente.admin.command("ping")   # confirma que hay conexión antes de empezar
        origen = cliente[DB_NAME][COLECCION_ORIGEN]
        prueba = cliente[DB_NAME][COLECCION_PRUEBA]
        print(f"Conectado a Atlas. Base: {DB_NAME}")
        while True:
            print(MENU)
            opcion = await preguntar_texto("Elige una opción: ")
            if opcion == "0":
                break
            try:
                await ejecutar_opcion(opcion, origen, prueba)
            except Exception as error:
                print("Ocurrió un error:", error)
    finally:
        await cliente.close()


if __name__ == "__main__":
    asyncio.run(main())
