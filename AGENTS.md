# Entrega 7
La *Entrega 7* debe ser un sistema de grado de producción. Debes construir una pieza de ingeniería capaz de razonar, recordar y escalar.

## Criterios de Aceptación

1. *Arquitectura y Coherencia del Sistema*: Evalúa la integración de las capas de los módulos anteriores (LLMs, RAG, Agentes) en un flujo unificado y lógico. Porcentaje 30 %.
2. *Robustez Técnica: Asincronía y Validación*: Uso de patrones async/await en Python 3.12+ con `uv` y validación de datos con Pydantic. Porcentaje 25 %.
3. *Persistencia y Observabilidad*: Implementación de Checkpointers en LangGraph y trazado de ejecución con herramientas externas. Porcentaje 20 %.
4. *Documentación y Despliegue*: Claridad del README, diagrama de arquitectura y facilidad de ejecución (Docker/Scripts). Porcentaje 15 %.
5. *Configuración de Entorno y Estándares de Código*: Uso de Python 3.12+, gestión de dependencias mediante `uv` y variables de entorno. Porcentaje 10 %.


La entrega debe cumplir con **todos los criterios** para ser considerada como *aceptable*.

---

## Descripción de la solución

¿Qué vamos a construir en la *Entrega 7*? Vamos a construir un sistema de grado de producción.

Produciremos un repositorio de GitHub con el sistema completo en Python 3.12+ utilizando **`uv`** para la gestión ultrarrápida de dependencias y entornos virtuales. El sistema accede a su base documental vía RAG, realiza razonamiento multi-paso (los agentes deciden, delegan y corrigen sus errores), cuenta con una interfaz de API profesional y documentada (no un script de consola), y ofrece trazabilidad completa de cada ejecución.

### Lo esencial en 3 líneas

Esto es lo que se espera del sistema que vamos a construir.

1. *Qué entregar:* un repositorio de GitHub con un sistema de IA completo que integra RAG + agentes (con Supervisor) + API profesional + trazabilidad, gestionado con `uv`.
2. *De dónde sale:* ensamblar y refactorizar tus pre-entregas de los módulos anteriores (todo async, con Checkpointer de LangGraph, validación con Pydantic y `uv` para dependencias).
3. *¿Cómo se evalúa?:* con la rúbrica de la *Entrega 7* (más abajo en esta unidad).


#### Lineamientos generales

1. *Cimientos Asíncronos & Abstracción:* Implementar clientes robustos que manejan streaming y latencia.
2. *RAG Avanzado:* Diseñar estrategias de recuperación híbrida y gestión de metadatos utilizando Pinecone como base de datos vectorial, reduciendo alucinaciones.
3. *Inteligencia Colectiva:* Crear una arquitectura de agentes donde un *Supervisor* delega tareas de forma autónoma.
4. *Robustez & Despliegue:* Preparar el entorno para producción con observabilidad (Arize Phoenix) y escalabilidad (Redis/FastAPI).


#### Instrucciones generales

Entregar un repositorio GitHub que contenga el sistema de IA completo. Este sistema debe permitir a un usuario final (o proceso automatizado) resolver una tarea compleja que requiera:

- Acceso a conocimiento específico (vía RAG).
- Razonamiento multi-paso (vía Agentes).
- Interfaz de API profesional y documentada.
- Trazabilidad completa de lo que ocurre "bajo el capó".

#### Errores Comunes a Evitar

- **Hard-coding de Pinecone:** Evita poner IDs de índices de Pinecone o API keys directamente en el código; utiliza obligatoriamente variables de entorno (PINECONE_API_KEY, PINECONE_INDEX_NAME).
- **Sincronicidad:** No mezclar llamadas síncronas (requests) dentro de funciones async def; usa httpx o los SDKs asíncronos oficiales.
- **Falta de Trazas:** Entregar un sistema que "funciona" pero cuya ejecución es una caja negra (sin integración de logs o traces).
- **Alcance del despliegue:** Este entregable se evalúa con despliegue local (Docker Compose o scripts optimizados con `uv`).
- **No se pide CI/CD (GitHub Actions, pipelines de integración continua) ni infraestructura en la nube:** No suma ni resta en la rúbrica.

---

# Detalles del Entregable

El **capstone** no es un proyecto nuevo, es el ensamblado y el refactor de lo que ya entregaste como *Módulo 6* y *Módulo 7 Ejemplo REDIS*.

Entonces, la base del Entregable son las pre-entregas de:

1. [Módulo 6](https://github.com/diegofziegler/entrega_6.git).
2. [Módulo 7 Ejemplo REDIS](https://github.com/diegofziegler/entrega_7_redis).


Adicionalmente queremos implementar técnicas y buenas prácticas que hemos visto en los módulos anteriores. Para cada una de las características que busco tener en esta entrega porque le aportan valor y calidad, te dejaré repositorios donde menciono cuáles características están allí ejemplificadas:

1. El cliente y las cadenas: [Módulo 1](https://github.com/diegofziegler/entrega_1.git) y el [Módulo 2](https://github.com/diegofziegler/entrega_2.git).
2. El conocimiento: El RAG del [Módulo 3](https://github.com/diegofziegler/entrega_3.git) y el [Módulo 4](https://github.com/diegofziegler/entrega_4.git) pasa a ser la tool del agente investigador.
3. El razonamiento: El grafo con supervisor del [Módulo 5](https://github.com/diegofziegler/entrega_5.git) y el [Módulo 6](https://github.com/diegofziegler/entrega_6.git) es el corazón del sistema.
4. La cáscara: La API, Redis y las trazas del [Módulo 7 Ejemplo REDIS](https://github.com/diegofziegler/entrega_7_redis) envuelven todo lo anterior.


Lo que buscamos es integrar los conocimientos para dejar de tener siete repositorios separados con los conceptos estudiados; queremos pasar a tener un repositorio nuevo con todo integrado. Básicamente, llevaremos la lógica del *Módulo 6* y del *Módulo 7 Ejemplo REDIS* a una estructura unificada. Separaremos por capas: agentes, grafo, API, observabilidad y configuración. Consolidaremos la gestión de dependencias y el entorno utilizando **`uv`** (con un archivo `pyproject.toml` moderno). Resultado esperado: un repo que se entiende sin conocer el historial de todas las entregas realizadas.

## Integración de Código:

Repito el siguiente lineamiento: El objetivo es consolidar *RAG*, el uso de *Agentes* y *API* en un único módulo nuevo:

- [entrega_7](https://github.com/diegofziegler/entrega_7.git)

La sugerencia es que, basado en las entregas de los siguientes dos módulos: [Módulo 6](https://github.com/diegofziegler/entrega_6.git) y [Módulo 7 Ejemplo REDIS](https://github.com/diegofziegler/entrega_7_redis), muevas la lógica de esas entregas para
**refactorizarlas** en una nueva estructura de proyecto unificada dentro del nuevo repositorio.

## Refactorización:

### Arquitectura y Asincronía

Toda la comunicación externa sea no bloqueante. Aplicar arquitectura limpia y desarrollo asíncrono de punta a punta con Python 3.12+.

Esto aplica para cada llamada al *LLM*, a la *vector DB* y a *Redis*. Reemplazar requests por httpx y los SDK síncronos por sus versiones async (`async/await`). Confirmar que no queda ningún bloqueo escondido en el event loop. Resultado esperado: el sistema sostiene peticiones concurrentes sin degradarse.

Referencia de cimientos asíncronos: [Módulo 1](https://github.com/diegofziegler/entrega_1.git).

### Orquestación Declarativa

Aplicar buenas prácticas sobre cadenas LCEL con contratos de datos y resiliencia. Referencia: [Módulo 2](https://github.com/diegofziegler/entrega_2.git).

### RAG Avanzado

Aplicar recuperación híbrida, gestión de metadatos y almacenamiento vectorial exclusivamente con Pinecone para reducir alucinaciones. Referencias: [Módulo 3](https://github.com/diegofziegler/entrega_3.git) y [Módulo 4](https://github.com/diegofziegler/entrega_4.git).

### Inteligencia Colectiva

Un supervisor que delega en agentes especializados. Referencia: [Módulo 5](https://github.com/diegofziegler/entrega_5.git).

### Robustez y Despliegue

Demostrar que el sistema es observable. Configurar y demostrar la observabilidad del sistema con trazas. Generaremos 5 pruebas unitarias del sistema y de esas pruebas debemos asegurar que las trazas se visualicen correctamente en *Arize Phoenix* o *LangSmith*.

Observabilidad y escala con Redis y FastAPI. Referencia: [Módulo 7 Ejemplo REDIS](https://github.com/diegofziegler/entrega_7_redis).

Guardar la evidencia en [trazas](./trazas). Lo que queremos guardar allí son  capturas del dashboard con las trazas activas. Queremos que cada ejecución tenga su árbol de spans y su costo asociado.

### Persistencia:

El sistema no pierde nada y no confíe en nada. Implementar el *Checkpointer* de *LangGraph* para que las conversaciones no se pierdan al reiniciar el servidor.

### Validación:

Usa *Pydantic* para validar todas las entradas y salidas de la API y de las herramientas de los agentes.

### Despliegue Local:

Asegúrate de que el proyecto pueda levantarse con una sola instrucción (ej. Docker Compose o un script optimizado con `uv run`).

### README y Gestión con `uv`:

Escribe la documentación incluyendo un diagrama de flujo del grafo de agentes (Mermaid). Documentar decisiones técnicas para una audiencia de ingeniería senior, detallando cómo inicializar y ejecutar el proyecto utilizando comandos de **`uv`** (ej. `uv sync`, `uv run`). El objetivo es que cualquiera pueda levantarlo sin preguntar nada, por eso escribir el README con el diagrama de flujo del grafo de agentes. Dejar el proyecto ejecutable con *Docker Compose* o un `run.sh`.

 
