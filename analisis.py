import re

VERBOS = "dijo|respondió|preguntó|murmuró|gritó|exclamó|susurró|añadió|contestó|replicó|musitó|suspiró|ordenó|repuso|insistió"
PRONOMBRES = {"El", "Ella", "Él", "Lo", "La", "Le", "Se", "Y", "Pero", "Yo", "Tú", "Te", "Me", "Nos", "Nosotros"}
RE_ATRIBUCION = re.compile(
    rf"\b({VERBOS})\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)|([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+({VERBOS})\b"
)
AMBIENTES_PALABRAS = {
    "lluvia": ("lluvia", "llovía", "lloviendo", "gotas"),
    "viento": ("viento", "ventisca", "brisa"),
    "pasos": ("pasos", "pisadas"),
    "fuego": ("fuego", "hoguera", "chimenea"),
}
# Cuántos párrafos dura un ambiente después de la palabra que lo activa.
DURACION_AMBIENTE = 3
VOCES_PERSONAJES = ("ef_dora", "em_alex", "em_santa")


def es_dialogo(parrafo):
    return parrafo.startswith(("—", "-"))


def hablante(parrafo):
    for m in RE_ATRIBUCION.finditer(parrafo):
        nombre = m.group(2) or m.group(3)
        if nombre and nombre not in PRONOMBRES:
            return nombre
    return None


def ambiente_de(parrafo):
    minusculas = parrafo.lower()
    for nombre, palabras in AMBIENTES_PALABRAS.items():
        if any(re.search(rf"\b{p}", minusculas) for p in palabras):
            return nombre
    return None


def analizar(parrafos):
    # Devuelve voces por párrafo (solo diálogos), ambientes por párrafo y la lista de personajes.
    voces, ambientes, personajes, recientes = {}, {}, [], []
    activo, restantes = None, 0
    for n, p in enumerate(parrafos):
        clave = ambiente_de(p)
        if clave:
            activo, restantes = clave, DURACION_AMBIENTE
        if activo and restantes > 0:
            ambientes[n] = activo
            restantes -= 1

        if not es_dialogo(p):
            continue
        nombre = hablante(p)
        if nombre is None and recientes:
            # Sin atribución: en una conversación suele responder el otro hablante reciente.
            ultimo = recientes[-1]
            distintos = [h for h in reversed(recientes) if h != ultimo]
            nombre = distintos[0] if distintos else ultimo
        if nombre:
            if nombre not in personajes:
                personajes.append(nombre)
            recientes.append(nombre)
            voces[n] = VOCES_PERSONAJES[personajes.index(nombre) % len(VOCES_PERSONAJES)]
    return {
        "voces": voces,
        "ambientes": ambientes,
        "personajes": [(nombre, VOCES_PERSONAJES[i % len(VOCES_PERSONAJES)]) for i, nombre in enumerate(personajes)],
    }
