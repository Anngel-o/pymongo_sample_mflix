# Reporte: aplicación síncrona vs. asíncrona con PyMongo y MongoDB Atlas

**Equipo:** _(nombres de los integrantes)_
**Materia / fecha:** _(completar)_

## 1. Objetivo

Crear dos aplicaciones en Python que administren la colección `movies` de la base
`sample_mflix` en MongoDB Atlas, una **síncrona** (PyMongo) y una **asíncrona**
(PyMongo Async con `AsyncMongoClient`), y comparar cómo se comportan.

## 2. Base de datos

- Clúster gratuito (M0) en MongoDB Atlas con el dataset de muestra `sample_mflix`.
- Colección `movies`: 21,349 documentos (título, año, géneros, calificación IMDb, etc.).
- La colección `movies` **solo se lee**. Para no dañarla, la carga masiva y el CRUD se hacen en una
  colección de pruebas (`movies_test`) que se vacía y se vuelve a llenar en cada ejecución.

## 3. Qué hace cada aplicación

Cada app es un **administrador de películas con menú**: el usuario elige qué hacer y la app le pregunta
los datos. Las dos tienen exactamente las mismas opciones.

| Funcionalidad | Opciones del menú | Qué hace |
|---|---|---|
| **Carga masiva** | 1 | Copia películas de `movies` a `movies_test` (el usuario elige cuántas; por defecto 2,000) en lotes de 200 con `bulk_write()` y `InsertOne`. |
| **CRUD** | 2, 3, 4, 5 | **C**rear una película (`insert_one`), **L**eer/buscarla por título (`find_one`), **A**ctualizar su año (`update_one`) y **E**liminarla (`delete_one`). |
| **CRUD masivo** | 6 | Repite el ciclo crear → leer → actualizar → eliminar con varias películas inventadas (el usuario elige cuántas). Sirve para ver qué pasa cuando hay muchas operaciones. |
| **Consultas** | 7, 8, 9, 10 | Cuatro consultas, cada una con una función distinta de MongoDB: películas de un año (filtro), cuántas hay de un género (conteo), las 5 mejor calificadas (ordenar y limitar) y géneros con más películas (agregación). |
| **Consultas juntas** | 11 | Las 4 consultas a la vez (en la asíncrona) o una tras otra (en la síncrona). |
| **Prueba de rendimiento** | 12 | Mide el tiempo de carga masiva, CRUD masivo y consultas (ver sección 5). |

Las consultas se hacen sobre `movies` (la original, que solo se lee). La carga y el CRUD se hacen sobre
`movies_test`.

### Por qué esos números en la prueba de rendimiento

Los números no tienen una razón matemática; son valores por defecto que se pueden cambiar en `config.py`:

| Valor | Por qué |
|---|---|
| 2,000 películas, lotes de 200 | Una muestra suficiente (10 lotes) para comparar, sin llenar el clúster gratuito de 512 MB. |
| 50 películas en el CRUD masivo | 50 × 4 = 200 operaciones: suficientes para que se note la diferencia entre hacerlas una por una o varias a la vez, sin tardar demasiado. |
| 4 consultas × 5 rondas = 20 | Con una sola consulta no hay nada que paralelizar; repetir el grupo da 20 consultas para medir. |
| Semaphore de 5 | Máximo de operaciones simultáneas, para no saturar el clúster gratuito. |

### Cómo se usó cada herramienta de asyncio (app asíncrona)

| Herramienta | Dónde se usa | Para qué |
|---|---|---|
| `AsyncMongoClient` | Toda la app | Cliente de MongoDB que funciona con `await`. |
| `bulk_write()` | Carga masiva | Manda un lote completo de inserciones en una sola petición. |
| `asyncio.TaskGroup` | Carga masiva | Cada lote es una tarea; el grupo espera a que todas terminen y, si una falla, cancela las demás. |
| `asyncio.gather()` | CRUD masivo y consultas | Lanza muchas operaciones juntas y entrega los resultados en el mismo orden. |
| `asyncio.Semaphore` | Carga masiva, CRUD masivo y consultas | Limita a 5 las operaciones simultáneas, para no saturar el clúster gratuito. |

## 4. Diferencias en el código

| Aspecto | Síncrona | Asíncrona |
|---|---|---|
| Cliente | `MongoClient` | `AsyncMongoClient` |
| Funciones | `def` | `async def` |
| Llamadas a la base | `coleccion.insert_one(...)` | `await coleccion.insert_one(...)` |
| Cursores | `list(coleccion.find(...))` | `await coleccion.find(...).to_list()` |
| `aggregate` | `coleccion.aggregate(...)` | `await coleccion.aggregate(...)` |
| Cerrar conexión | `cliente.close()` | `await cliente.close()` |
| Arranque | Se llama directo | `asyncio.run(...)` |
| Varias operaciones | Una tras otra (`for`) | A la vez (`gather`, `TaskGroup`) |
| Python mínimo | 3.8 | 3.11 (por `TaskGroup`) |

## 5. Resultados

Se ejecutó `python comparar.py`, que corre la opción 12 (prueba de rendimiento) de las dos apps con los
mismos datos y parámetros (2,000 películas, lotes de 200, CRUD masivo de 50 películas, 20 consultas y
concurrencia máxima 5). Pegar aquí la tabla de `resultados.md`:

| Operación | Síncrona (s) | Asíncrona (s) | Veces más rápida la asíncrona |
|---|---|---|---|
| Carga masiva | _(pegar)_ | _(pegar)_ | _(pegar)_ |
| CRUD masivo de 50 películas | _(pegar)_ | _(pegar)_ | _(pegar)_ |
| Consultas | _(pegar)_ | _(pegar)_ | _(pegar)_ |
| **Total** | _(pegar)_ | _(pegar)_ | _(pegar)_ |

_Conviene correrlo 3 veces y anotar el promedio, porque el clúster gratuito y el internet cambian de una corrida a otra._

## 6. Análisis

**Por qué puede ganar la asíncrona.** Casi todo el tiempo de estas operaciones es *espera de red*
(el programa manda la petición a Atlas y espera la respuesta). La app síncrona se queda parada en cada
espera. La asíncrona aprovecha ese tiempo para mandar otras peticiones, así que cuantas más operaciones
independientes haya (muchas consultas, muchas películas en el CRUD, varios lotes), más tiempo se ahorra.

**Dónde no se nota (o puede perder).**
- Con una sola operación la asíncrona no gana nada: no hay otra cosa que hacer mientras espera.
- `bulk_write()` ya ahorra mucho en la síncrona, porque manda 200 inserciones en un solo viaje. Por eso
  la diferencia en la carga masiva suele ser menor que en el CRUD.
- El clúster gratuito (M0) limita las operaciones por segundo, y la concurrencia máxima (Semaphore) está
  en 5: si el servidor se satura, la mejora se reduce.

**Comentario sobre los resultados.** _(Completar con los números de la tabla: en qué operación fue
más grande la diferencia y si coincide con lo explicado arriba.)_

**Complejidad del código.** La versión asíncrona es un poco más difícil de leer: hay que usar
`async`/`await`, `gather`, `TaskGroup` y `Semaphore`, y requiere Python 3.11 o superior. La síncrona es más
simple y suficiente cuando se hacen pocas operaciones.

## 7. Conclusiones

- Las dos apps tienen la misma funcionalidad y trabajan sobre los mismos datos.
- La versión asíncrona conviene cuando hay **muchas operaciones independientes** que pueden esperar a la red
  al mismo tiempo; la síncrona, cuando el programa es simple o secuencial.
- `Semaphore` es necesario para no mandar demasiadas peticiones juntas, y `bulk_write()` es la mejor
  opción para cargas masivas en cualquiera de las dos versiones.
- _(Agregar una conclusión propia del equipo.)_

## 8. Cómo reproducirlo

Ver `README.md`.
