# Lector de voz (radio novela con Kokoro)

Aplicación local que lee libros y textos en español con voces de [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M). Carga un archivo `.txt`, `.md`, `.docx` o `.pdf`, lo divide en capítulos y genera el audio por párrafo en el navegador. Puede asignar voces por personaje, mezclar ambientes generados por código (lluvia, viento, pasos, fuego) y descargar capítulos en MP3 o WAV.

No necesita ninguna clave de API ni servicios externos. Todo corre en la máquina del usuario.

## Requisitos

- Python 3.12.
- Conexión a internet solo la primera vez, para descargar el modelo de Kokoro (unos cientos de MB).
- Paquetes de Python:

```bash
pip install kokoro torch numpy soundfile python-docx pypdf lameenc
```

## Archivos del proyecto

| Archivo | Para qué sirve |
|---|---|
| `interfaz_voz.py` | Servidor HTTP y página web. Es el archivo que se ejecuta. |
| `analisis.py` | Detecta diálogos, personajes y ambientes con reglas (sin IA externa). |
| `ambientes.py` | Genera los ambientes (lluvia, viento, pasos, fuego) y los mezcla bajo la voz. |
| `icono-180.png`, `icono-512.png` | Iconos de la página y del manifiesto. Deben estar en la misma carpeta. |
| `icono_1024.png`, `AppIcon.icns`, `AppIcon.iconset/` | Iconos para la app de macOS. No los necesita el servidor. |
| `crear_icono.py` | Genera los iconos a partir de `icono_1024.png`. |
| `leer_ia.py`, `que_es_la_ia.txt` | Ejemplo sencillo de lectura de un texto sin la interfaz. |

Todos los archivos `.py` deben estar en la misma carpeta, porque `interfaz_voz.py` importa `analisis` y `ambientes`.

## Cómo correrla

Desde la carpeta del proyecto:

```bash
python interfaz_voz.py
```

Después abre `http://localhost:8765` en el navegador.

Para usarla desde otro equipo de la misma red Wi-Fi:

```bash
LECTOR_RED=1 python interfaz_voz.py
```

Luego abre `http://IP_DEL_EQUIPO:8765`. Esta opción **no tiene contraseña**: cualquiera en la red puede usarla.

Por defecto el servidor solo escucha en `127.0.0.1`.

## Uso

1. Pulsa **Archivo**, elige el libro y pulsa **Cargar**. El texto se divide en capítulos.
2. Elige un capítulo en la barra lateral. La reproducción empieza sola con el primer párrafo.
3. Haz clic en cualquier párrafo para empezar desde ahí.
4. En cada párrafo hay un selector de voz: **Narrador (voz general)**, Dora, Alex o Santa.
5. **Analizar capítulo** detecta los personajes por las rayas de diálogo y las frases tipo "dijo Ana", asigna una voz a cada uno y pone ambientes según palabras clave. Esto reemplaza las voces asignadas a mano en ese capítulo.
6. En **Descargas** puedes bajar el capítulo actual, los capítulos marcados con la casilla o todos, en MP3 o WAV. Varios capítulos llegan en un ZIP. La parte actual solo se descarga en WAV.

## Voces disponibles

- `ef_dora`: femenina, español (Dora).
- `em_alex`: masculina, español (Alex).
- `em_santa`: masculina, español (Santa).

El pipeline está configurado con `lang_code="e"` (español). Otras voces del modelo, como las de portugués, necesitan otro `lang_code`.

## Endpoints HTTP

Todos son `POST`, salvo `GET /` y los archivos estáticos.

| Ruta | Campos | Respuesta |
|---|---|---|
| `/subir` | cuerpo con el archivo, cabecera `X-Nombre` | JSON con los capítulos |
| `/trozos` | `indice`, `voz` | JSON con los párrafos, su total y la voz asignada a cada uno |
| `/trozo` | `indice`, `n`, `voz` | WAV del párrafo `n`, con ambiente si lo tiene |
| `/asignar` | `indice`, `n`, `voz` (vacío = narrador) | JSON `{ok: true}` |
| `/analizar` | `indice` | JSON con personajes y número de ambientes |
| `/texto` | `texto`, `voz` | WAV del texto libre |
| `/descargar` | `indices` (separados por coma), `formato` (`mp3` o `wav`), `voz` | MP3/WAV, o ZIP si son varios |

## Notas técnicas

- El documento cargado vive en memoria del servidor. Si lo reinicias, hay que volver a subir el archivo.
- La generación es secuencial y usa un bloqueo: cada párrafo tarda unos 4 a 5 segundos en una Mac común. Un capítulo largo puede tardar varios minutos en descargarse completo.
- Las asignaciones de voz y ambientes se guardan en memoria. Se pierden al reiniciar el servidor.
- El análisis por reglas funciona bien con diálogos que usan raya (`—`). Con comillas casi no detecta diálogos.
- Cada personaje recibe una de las tres voces en orden de aparición. Si hay más de tres personajes, algunos comparten voz.
- Las palabras clave de ambiente pueden activarse por error. Por ejemplo, "pasos" aparece en expresiones como "dos pasos".
- No hay pausas entre cambios de personaje.
- MP4/M4A no está soportado: la conversión usa `lameenc`, que solo genera MP3.
- El servidor no tiene autenticación ni límites de tamaño de archivo.
- La interfaz se probó solo en el navegador integrado de Claude. No se ha probado en Chrome ni en Safari.

## Solución de problemas

- **La página sale en blanco:** recarga con fuerza (Cmd+Shift+R) y revisa la consola del navegador (Cmd+Option+J en Chrome).
- **Error `No module named 'kokoro'` o similar:** instala los paquetes de la sección de requisitos con el mismo Python que ejecuta el servidor.
- **El primer párrafo tarda mucho:** es normal, porque el modelo se carga en memoria al arrancar y la primera síntesis es más lenta.
- **Puerto ocupado:** cambia `PORT` en `interfaz_voz.py` o detén el proceso que usa el puerto 8765.
