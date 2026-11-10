# sample_mflix: app síncrona vs. asíncrona (PyMongo + MongoDB Atlas)

Repositorio: https://github.com/Anngel-o/pymongo_sample_mflix

Proyecto de aprendizaje que administra la colección `movies` de la base `sample_mflix`
(MongoDB Atlas) de dos formas y compara su desempeño:

- **`app_sync.py`**: PyMongo normal (`MongoClient`).
- **`app_async.py`**: PyMongo Async (`AsyncMongoClient`) con `asyncio.gather()`,
  `asyncio.TaskGroup`, `asyncio.Semaphore` y `bulk_write()`.

Las dos son administradores con menú y hacen lo mismo: **carga masiva**, **CRUD** y **consultas**.

> La guía completa (configuración de Atlas y PyMongo con capturas, cómo funciona cada parte y
> solución de problemas) está en **`Guia_del_Proyecto.docx`**.

## Archivos

| Archivo | Qué hace |
|---|---|
| `config.py` | Lee el `.env` y define los parámetros (tamaño de lote, concurrencia, etc.) |
| `app_sync.py` | Aplicación síncrona |
| `app_async.py` | Aplicación asíncrona |
| `comparar.py` | Ejecuta la prueba de rendimiento de las dos apps y compara los tiempos |
| `test_conexion.py` | Prueba rápida de conexión a Atlas |
| `requirements.txt` | Librerías necesarias |
| `REPORTE.md` | Reporte con la comparación entre las dos apps |
| `Guia_del_Proyecto.docx` | Guía del proyecto (manual) |
| `resultados.md` | Tabla de tiempos. **No viene en el repo desde el inicio: se crea al ejecutar `comparar.py`** |

## Cómo ejecutarlo

Requiere **Python 3.11 o superior** (por `asyncio.TaskGroup`).

1. Instalar las librerías:
   ```
   python -m pip install -r requirements.txt
   ```
2. Crear un archivo `.env` en la carpeta del proyecto con la conexión a Atlas
   (sin comillas; este archivo **no se sube a GitHub**):
   ```
   MONGODB_URI=mongodb+srv://USUARIO:PASSWORD@clustersamplemflix.uluz8c0.mongodb.net/
   DB_NAME=sample_mflix
   COLLECTION_NAME=movies
   TEST_COLLECTION=movies_test_TUNOMBRE
   ```
   Cada integrante debe usar un `TEST_COLLECTION` distinto (por ejemplo `movies_test_ana`).
3. Probar la conexión:
   ```
   python test_conexion.py
   ```
   Debe mostrar `SYNC OK` y `ASYNC OK` con 21349 documentos.
4. Usar cada app (abre un menú: eliges una opción y la app te pregunta los datos):
   ```
   python app_sync.py
   python app_async.py
   ```

## Menú de las apps

| Opción | Qué hace |
|---|---|
| 1 | Carga masiva: copia películas de `movies` a `movies_test` (con `bulk_write`) |
| 2 a 5 | CRUD de una película: crear, buscar, cambiar el año, eliminar |
| 6 | CRUD masivo (varias películas) |
| 7 a 10 | Consultas: por año, por género, mejor calificadas, géneros con más películas |
| 11 | Las consultas 7, 8, 9 y 10 juntas |
| 12 | Prueba de rendimiento |
| 13 | Borrar todo lo de `movies_test` (la deja vacía) |
| 0 | Salir |

Recorrido sugerido: **13** (dejar vacía), **1** (cargar), **2 a 5** (CRUD), **7 a 10** (consultas), **12** (rendimiento).

## Comparación y `resultados.md`

```
python comparar.py
```

Corre la prueba de rendimiento (opción 12) de las dos apps con los mismos datos, imprime una tabla
con los tiempos y **crea el archivo `resultados.md`** en la misma carpeta. Ese archivo **no existe hasta
que se ejecuta `comparar.py`**. La tabla se copia a la sección 5 de `REPORTE.md`.

## Importante

- La colección original `movies` **solo se lee**. Todo lo que se escribe (carga masiva y CRUD)
  va a la colección indicada en `TEST_COLLECTION`, que la opción 1 borra y vuelve a crear.
- El archivo `.env` tiene contraseñas: **no se sube a GitHub** (ya está en `.gitignore`).
- `0.0.0.0/0` en Network Access de Atlas abre el clúster a cualquier IP: bórralo al terminar el proyecto.
