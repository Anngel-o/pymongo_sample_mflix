# sample_mflix: app síncrona vs. asíncrona (PyMongo + MongoDB Atlas)

Proyecto de aprendizaje que administra la colección `movies` de la base `sample_mflix`
de dos formas y compara su desempeño:

- `app_sync.py`: PyMongo normal (`MongoClient`).
- `app_async.py`: PyMongo Async (`AsyncMongoClient`) con `asyncio.gather()`,
  `asyncio.TaskGroup`, `asyncio.Semaphore` y `bulk_write()`.

Las dos son administradores con menú y hacen lo mismo: **carga masiva**, **CRUD** y **consultas**.

## Archivos

| Archivo | Qué hace |
|---|---|
| `config.py` | Lee el `.env` y define los parámetros (tamaño de lote, concurrencia, etc.) |
| `app_sync.py` | Aplicación síncrona |
| `app_async.py` | Aplicación asíncrona |
| `comparar.py` | Ejecuta la prueba de rendimiento de las dos y muestra una tabla de tiempos (`resultados.md`) |
| `test_conexion.py` | Prueba rápida de conexión |
| `REPORTE.md` | Reporte del proyecto |

## Cómo ejecutarlo

Requiere **Python 3.11 o superior** (por `asyncio.TaskGroup`).

1. Instalar dependencias:
   ```
   python -m pip install -r requirements.txt
   ```
2. Copiar `.env.example` a `.env` y poner la cadena de conexión con tu usuario y contraseña.
   Usa un `TEST_COLLECTION` propio (por ejemplo `movies_test_ana`).
3. Probar la conexión:
   ```
   python test_conexion.py
   ```
4. Usar cada app (abre un menú: eliges una opción y la app te pregunta los datos):
   ```
   python app_sync.py
   python app_async.py
   ```
   Sugerencia de recorrido: opción **1** (cargar películas), luego **2, 3, 4, 5** (CRUD de una película),
   **7 a 10** (consultas) y por último **12** (prueba de rendimiento).
5. Ejecutar la comparación (corre la prueba de rendimiento de las dos y genera `resultados.md`):
   ```
   python comparar.py
   ```

## Importante

- La colección original `movies` **solo se lee**. Todo lo que se escribe (carga masiva y CRUD)
  va a la colección indicada en `TEST_COLLECTION`, que se borra y se vuelve a crear en cada corrida.
- El archivo `.env` tiene contraseñas: **no se sube a GitHub** (ya está en `.gitignore`).
