# Idea a implementar

El usuario hace una pregunta en Español, hay un Agente que busca la información que puede responder a pregunta, luego otro Agente analiza el idioma original de la pregunta y la responde en ese mismo idioma (con los datos aportados por el agente de búsqueda).

Respecto del Agente que busca la información, lo hace en una Vector DB, esa información proviene de unos archivos que yo mismo proporciono, todos ellos están en español (y en formato markdown). Los archivos para el RAG están en el directorio [data](./data)

Tambien quiero añadir un parámetro de configuración de idioma (por ejemplo, `idioma: str = "Español"` o configurarlo a través del estado global / prompt del sistema) te permite demostrar un control avanzado de los agentes.

Aquí te detallo por qué es una gran práctica y cómo implementarla correctamente sin romper tu diseño:

## 1. ¿Por qué es una buena idea?

- **Desacoplamiento de fuentes:** Demuestra que el sistema es capaz de realizar recuperación de información en un idioma base (tus documentos y Vector DB en español) y realizar un procesamiento cognitivo y de síntesis en **otro** idioma destino (francés, inglés, portugués, etc.).
- **Escalabilidad del caso de uso:** Te permite reutilizar el mismo motor de investigación documental para usuarios internacionales sin necesidad de duplicar o traducir tus fuentes físicas en la Vector DB.

---

## 2. ¿Cómo implementarlo en la arquitectura de LangGraph?

Para que funcione de forma limpia y robusta, te sugiero integrarlo de la siguiente manera:

1. **Ampliar el Estado Compartido (`State`):** Añade el parámetro de idioma al esquema de control para que todos los nodos lo conozcan:

```python
class MultiAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next: str
    idioma_destino: str # <-- Nuevo parámetro global
```

1. **Inyección en el Prompt del Agente de Análisis/Síntesis:** El agente encargado de redactar la respuesta final debe recibir este parámetro en su prompt del sistema para que traduzca, adapte y responda rigurosamente en ese idioma:

```python
def analyst_node(state: MultiAgentState):
idioma = state.get("idioma_destino", "Español")
system_prompt = f"Sos un analista experto. Tu objetivo es procesar la información obtenida y redactar la respuesta final exclusivamente en idioma: {idioma}."
# ... lógica de invocación al agente ...

```

1. **Configuración inicial en la ejecución (`ainvoke` / `astream`):** Cuando un usuario inicie la consulta, pasas el idioma deseado como parte del estado inicial:

```python
initial_state = {
    "messages": [HumanMessage(content="¿De qué tratan los documentos sobre el proyecto?")],
    "idioma_destino": "Francés" # Aquí configuras el parámetro dinámicamente
}
```

---

## 3. Precaución a tener en cuenta (Buenas Prácticas)

- **Claridad en el rol de los agentes:** Asegúrate de que el **Agente de Búsqueda** (el que consulta la Vector DB) mantenga su consulta orientada a las fuentes en español (ya que tus documentos están ahí), y sea el **Agente Analista/Sintetizador** el responsable de hacer la traducción y adaptación cultural al idioma de destino configurado. ¡De esta forma evitas que el recuperador falle buscando términos traducidos que quizás no existan textualmente en tus archivos locales!

---

## 4. RAG


Las instrucciones respecto de esta funcionalidad las he dejado en el archivo [rag_vectordb.md](./rag_vectordb.md)

---

## 5. Logs para conprobar el comportamiento

Para todas las uncionalidades debemos tener un log que nos permita seguir la traza de las actividades del ejemplo a implementar.

Debes generar los archivos de log en el directorio [log](./log).

Un archivo de log (llamado *agentes*) debe estar destinado al *Orquestador Multi Agente*. Y otro archivo distinto (llamado *rag*) debe estar destinado al *Rag*.

---
