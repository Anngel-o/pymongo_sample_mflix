"""Prueba de conexion a MongoDB Atlas (sample_mflix), version sincrona y asincrona."""

import asyncio

# asyncio librería de Python para programación asíncrona
import os

# dotenv librería para leer variables de entorno desde un archivo .env
from dotenv import load_dotenv

# load_dotenv() lee el  archivo .env y carga MONGODB_URI, DB_NAME y COLLECTION_NAME
from pymongo import AsyncMongoClient, MongoClient

# MongoClient: el cliente síncrono (cada llamada bloquea hasta tener respuesta
# AsyncMongoClient: el cliente asíncrono (las llamadas se “esperan” con await).

load_dotenv()
URI = os.environ["MONGODB_URI"]
DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "movies")
# el orden ("", "") es importante: primero la variable de entorno, luego el valor por defecto.


def prueba_sync():
    client = MongoClient(URI, serverSelectionTimeoutMS=8000)
    try:
        client.admin.command("ping")
        # admin es el nombre de una base de datos, una de las que MongoDB trae por defecto en cualquier clúster
        # ping responde {ok: 1} si el servidor está vivo. Es una forma de comprobar conexión.
        coleccion = client[DB_NAME][COLLECTION_NAME]
        total = coleccion.count_documents({})
        # Cuenta documentos. {} es el filtro vacío, es decir, “todos”. Aquí el programa se queda bloqueado esperando la respuesta.
        ejemplo = coleccion.find_one({}, {"title": 1, "year": 1})
        # {} es un filtro que significa "cualquiera" y title:1 y year:1 son proyecciones, es decir, que solo queremos esos campos en el resultado.
        print(f"SYNC  OK -> {total} documentos en {DB_NAME}.{COLLECTION_NAME}")
        print(f"            ejemplo: {ejemplo}")
    finally:
        # Cierra la conexión al servidor de MongoDB. Esto es importante para liberar recursos.
        # Siempre se ejecuta, incluso si ocurre un error en el bloque try.
        client.close()


async def prueba_async():
    client = AsyncMongoClient(URI, serverSelectionTimeoutMS=8000)
    try:
        # await pausa la funcion hasta que llegue el resultado de la llamada asíncrona. Mientras tanto, el event loop puede ejecutar otras tareas.
        await client.admin.command("ping")
        coleccion = client[DB_NAME][COLLECTION_NAME]
        total = await coleccion.count_documents({})
        ejemplo = await coleccion.find_one({}, {"title": 1, "year": 1})
        print(f"ASYNC OK -> {total} documentos en {DB_NAME}.{COLLECTION_NAME}")
        print(f"            ejemplo: {ejemplo}")
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        prueba_sync()
        asyncio.run(prueba_async())
    except KeyError:
        print("Falta MONGODB_URI: revisa que el archivo .env este en esta carpeta.")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
