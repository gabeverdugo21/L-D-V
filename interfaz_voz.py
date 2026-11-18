import io
import json
import re
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote

import docx
import lameenc
import numpy as np
import pypdf
import soundfile as sf
from kokoro import KPipeline

import analisis
from ambientes import mezclar as mezclar_ambiente

PORT = 8765
VOCES = ("ef_dora", "em_alex", "em_santa")
pipeline = KPipeline(lang_code="e")
documento = {"nombre": "", "capitulos": [], "voces": {}, "ambientes": {}}

PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lector de voz</title>
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icono-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Lector de voz">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0f0f10">
<style>
:root { --fondo:#0f0f10; --panel:#1a1a1d; --texto:#f5f5f5; --suave:#b8b8c0; --acento:#ffd400; --sobre:#000; --foco:#00e5ff; --borde:#3a3a40; }
[data-tema="claro"] { --fondo:#fafafa; --panel:#ffffff; --texto:#111; --suave:#4a4a52; --acento:#1d4ed8; --sobre:#fff; --foco:#0369a1; --borde:#d4d4d8; }
* { box-sizing: border-box; }
body { margin:0; font-family: -apple-system, Arial, sans-serif; font-size:20px; line-height:1.6; background:var(--fondo); color:var(--texto); }
header { display:flex; flex-wrap:wrap; align-items:center; gap:12px; padding:14px 20px; background:var(--panel); border-bottom:1px solid var(--borde); position:sticky; top:0; z-index:2; }
header h1 { font-size:22px; margin:0 auto 0 0; }
button, select, input[type=file]::file-selector-button { font:inherit; font-size:18px; padding:10px 16px; min-height:48px; border-radius:10px; border:2px solid var(--borde); background:var(--panel); color:var(--texto); cursor:pointer; }
button.primario { background:var(--acento); color:var(--sobre); border-color:var(--acento); font-weight:bold; }
button:disabled { opacity:.45; cursor:default; }
button:focus-visible, select:focus-visible, textarea:focus-visible, #lectura p:focus-visible { outline:4px solid var(--foco); outline-offset:2px; }
.layout { display:grid; grid-template-columns: 280px 1fr; min-height: calc(100vh - 150px); }
aside { border-right:1px solid var(--borde); padding:18px; background:var(--panel); overflow-y:auto; }
aside h2, main h2 { font-size:16px; text-transform:uppercase; letter-spacing:.08em; color:var(--suave); margin:8px 0 12px; }
#capitulos { display:flex; flex-direction:column; gap:8px; }
#capitulos button { text-align:left; width:100%; }
#capitulos button.activo { border-color:var(--acento); box-shadow: inset 4px 0 0 var(--acento); }
.fila { display:flex; align-items:center; gap:8px; }
.fila button { flex:1; }
.fila input[type=checkbox] { width:24px; height:24px; min-height:24px; accent-color:var(--acento); flex:0 0 auto; }
main { padding:24px 28px 40px; max-width: 820px; width:100%; }
#titulo-capitulo { font-size:26px; margin:0 0 16px; }
#lectura { font-size:21px; line-height:1.75; }
#lectura p { padding:10px 14px; border-radius:10px; cursor:pointer; margin:6px 0; border-left:4px solid transparent; }
#lectura p:hover { background: rgba(127,127,127,.12); }
#lectura p.actual { background: var(--acento); color:var(--sobre); border-left-color:var(--sobre); font-weight:600; }
.renglon { display:flex; align-items:flex-start; gap:10px; }
.renglon p { flex:1 1 auto; min-width:0; }
.renglon select { flex:0 0 auto; width:auto; min-width:150px; font-size:16px; margin-top:8px; }
.vacio { color:var(--suave); font-size:20px; padding:30px 0; }
.tarjeta { background:var(--panel); border:1px solid var(--borde); border-radius:12px; padding:14px; margin-bottom:14px; }
textarea { width:100%; height:120px; font:inherit; font-size:18px; padding:12px; border-radius:10px; border:2px solid var(--borde); background:var(--fondo); color:var(--texto); }
.reproductor { position:sticky; bottom:0; background:var(--panel); border-top:1px solid var(--borde); padding:12px 20px; display:flex; flex-wrap:wrap; align-items:center; gap:10px 14px; z-index:2; }
.reproductor .ctrl { min-width:56px; min-height:56px; border-radius:50%; font-size:22px; padding:0; }
.reproductor .ctrl.grande { min-width:68px; min-height:68px; font-size:28px; background:var(--acento); color:var(--sobre); border-color:var(--acento); }
#progreso { flex:1 1 220px; min-width:160px; accent-color:var(--acento); }
#tiempo, #parte { font-variant-numeric: tabular-nums; color:var(--suave); font-size:17px; }
#estado { color:var(--suave); font-size:17px; width:100%; min-height:1.4em; }
.mensaje-subida { color:var(--suave); font-size:17px; }
@media (max-width: 760px) {
  .layout { grid-template-columns: 1fr; }
  aside { border-right:0; border-bottom:1px solid var(--borde); max-height: 40vh; }
  header h1 { width:100%; }
}
</style></head>
<body>
<header>
  <h1>Lector de voz</h1>
  <label class="tarjeta" style="padding:8px 12px; margin:0;">
    Archivo
    <input type="file" id="archivo" accept=".txt,.md,.docx,.pdf" aria-label="Elegir archivo">
  </label>
  <button id="subir" class="primario">Cargar</button>
  <button id="tema" aria-label="Cambiar tema claro u oscuro">Tema claro</button>
  <span id="estado-subida" class="mensaje-subida" role="status" aria-live="polite"></span>
</header>

<div class="layout">
  <aside>
    <h2>Capítulos</h2>
    <label for="voz" class="mensaje-subida">Voz</label>
    <select id="voz" style="width:100%; margin:6px 0 16px;">
      <option value="ef_dora">Dora (femenina)</option>
      <option value="em_alex">Alex (masculina)</option>
      <option value="em_santa">Santa (masculina)</option>
    </select>
    <button id="analizar" style="width:100%; margin:0 0 16px;" disabled>Analizar capítulo (personajes y ambientes)</button>
    <div id="capitulos" role="list" aria-label="Capítulos"></div>
    <h2 style="margin-top:24px;">Texto suelto</h2>
    <textarea id="texto" aria-label="Pega un texto para escucharlo" placeholder="Pega aquí un texto..."></textarea>
    <button id="generar-texto" style="margin-top:8px; width:100%;">Generar audio del texto</button>
    <button id="bajar-texto" style="margin-top:8px; width:100%;" title="Descargar el audio del texto (.wav)" disabled>&#11015; Descargar audio del texto</button>
    <h2 style="margin-top:24px;">Descargas</h2>
    <label for="formato" class="mensaje-subida">Formato</label>
    <select id="formato" style="width:100%; margin:6px 0 10px;">
      <option value="mp3">MP3</option>
      <option value="wav">WAV</option>
    </select>
    <button id="bajar-capitulo" style="width:100%;" disabled>&#11015; Capítulo actual</button>
    <button id="bajar-seleccion" style="margin-top:8px; width:100%;" disabled>&#11015; Seleccionados (0)</button>
    <button id="bajar-todos" style="margin-top:8px; width:100%;" disabled>&#11015; Todos los capítulos</button>
    <button id="bajar-parte" style="margin-top:8px; width:100%;" title="Descargar la parte actual (siempre en WAV)" disabled>&#11015; Parte actual (WAV)</button>
  </aside>

  <main>
    <h2 id="titulo-capitulo">Sin capítulo seleccionado</h2>
    <p class="vacio" id="vacio">Sube un archivo y elige un capítulo para empezar. Haz clic en cualquier párrafo para empezar desde ahí.</p>
    <div id="lectura" aria-label="Texto del capítulo"></div>
  </main>
</div>

<div class="reproductor" role="region" aria-label="Controles de reproducción">
  <button class="ctrl" id="anterior" aria-label="Parte anterior" disabled>&#9664;&#9664;</button>
  <button class="ctrl grande" id="reproducir" aria-label="Reproducir o pausar" disabled>&#9654;</button>
  <button class="ctrl" id="siguiente" aria-label="Parte siguiente" disabled>&#9654;&#9654;</button>
  <input type="range" id="progreso" min="0" max="100" value="0" aria-label="Progreso de la parte" disabled>
  <span id="tiempo">0:00 / 0:00</span>
  <span id="parte"></span>
  <select id="velocidad" aria-label="Velocidad">
    <option value="0.75">0.75x</option>
    <option value="1" selected>1x</option>
    <option value="1.25">1.25x</option>
    <option value="1.5">1.5x</option>
  </select>
  <button id="detener" aria-label="Detener">Detener</button>
  <div id="estado" role="status" aria-live="polite"></div>
</div>
<audio id="reproductor" preload="auto"></audio>

<script>
let elegido = null, cargado = null, sesion = 0, urls = [], blobs = [], audioTexto = null, actual = -1, esperando = null, total = 0, capitulos = [];
const $ = (id) => document.getElementById(id);
const r = $('reproductor');
const estado = (x) => $('estado').textContent = x;
const formato = (s) => { s = Math.floor(s || 0); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };

function actualizarControles() {
  const hay = total > 0;
  $('anterior').disabled = !hay || actual <= 0;
  $('siguiente').disabled = !hay || actual >= total - 1;
  $('reproducir').disabled = !hay;
  $('progreso').disabled = !hay;
  $('reproducir').innerHTML = r.paused ? '&#9654;' : '&#10074;&#10074;';
  $('reproducir').setAttribute('aria-label', r.paused ? 'Reproducir' : 'Pausar');
  $('parte').textContent = hay && actual >= 0 ? 'Parte ' + (actual + 1) + ' de ' + total : '';
  $('bajar-parte').disabled = !(actual >= 0 && urls[actual]);
  actualizarDescargas();
}

function seleccion() {
  return [...document.querySelectorAll('#capitulos input:checked')].map(x => Number(x.dataset.i));
}

function actualizarDescargas() {
  const marcados = seleccion();
  $('bajar-capitulo').disabled = elegido === null;
  $('bajar-seleccion').disabled = marcados.length === 0;
  $('bajar-seleccion').textContent = '⬇ Seleccionados (' + marcados.length + ')';
  $('bajar-todos').disabled = capitulos.length === 0;
}

function guardar(url, nombre) {
  const a = document.createElement('a');
  a.href = url; a.download = nombre;
  document.body.appendChild(a); a.click(); a.remove();
}
const limpio = (s) => (s || 'audio').replace(/[\\/:*?"<>|]+/g, '').trim().slice(0, 80) || 'audio';

function marcar(n) {
  document.querySelectorAll('#lectura p').forEach((p, i) => {
    p.classList.toggle('actual', i === n);
    p.setAttribute('aria-current', i === n ? 'true' : 'false');
  });
  const p = $('p' + n);
  if (p) p.scrollIntoView({ block: 'center', behavior: 'smooth' });
}

function reproducir(n) {
  actual = n; esperando = null;
  r.src = urls[n];
  r.playbackRate = parseFloat($('velocidad').value);
  r.play();
  marcar(n);
  actualizarControles();
}

function irA(n) {
  if (n < 0 || n >= total) return;
  if (urls[n]) reproducir(n);
  else { actual = n; esperando = n; marcar(n); actualizarControles(); completar(n); }
}

r.onended = () => {
  const s = actual + 1;
  if (s >= total) { estado('Capítulo terminado'); actualizarControles(); return; }
  if (urls[s]) reproducir(s); else { esperando = s; actual = s; marcar(s); actualizarControles(); completar(s); }
};
r.onplay = r.onpause = actualizarControles;
r.ontimeupdate = () => {
  const d = r.duration || 0;
  $('progreso').value = d ? (r.currentTime / d) * 100 : 0;
  $('tiempo').textContent = formato(r.currentTime) + ' / ' + formato(d);
};
$('progreso').oninput = (e) => { if (r.duration) r.currentTime = (e.target.value / 100) * r.duration; };
$('velocidad').onchange = (e) => { r.playbackRate = parseFloat(e.target.value); };
$('analizar').onclick = async () => {
  if (cargado === null) return;
  $('analizar').disabled = true;
  estado('Analizando capítulo…');
  const resp = await fetch('/analizar', { method: 'POST', body: new URLSearchParams({ indice: cargado }) });
  if (!resp.ok) { estado('Error al analizar el capítulo'); $('analizar').disabled = false; return; }
  const datos = await resp.json();
  const info = await (await fetch('/trozos', { method: 'POST', body: new URLSearchParams({ indice: cargado }) })).json();
  r.pause();
  urls.forEach((u, n) => invalidar(n));
  mostrarTextos(info.textos, info.voces);
  const lista = datos.personajes.map(p => p[0] + ' (' + p[1] + ')').join(', ');
  estado('Personajes: ' + (lista || 'ninguno') + '. Ambientes en ' + datos.ambientes + ' párrafos.');
  $('analizar').disabled = false;
  completar(Math.max(actual, 0));
};
$('voz').onchange = () => {
  if (cargado === null) return;
  r.pause();
  urls.forEach((u, n) => invalidar(n));
  completar(Math.max(actual, 0));
};
$('reproducir').onclick = () => {
  if (actual < 0) { irA(0); return; }
  if (r.paused) { if (urls[actual]) r.play(); else irA(actual); } else r.pause();
};
$('anterior').onclick = () => irA(actual - 1);
$('siguiente').onclick = () => irA(actual + 1);

function mostrarTextos(lista, voces) {
  const cont = $('lectura');
  cont.innerHTML = '';
  lista.forEach((t, i) => {
    const renglon = document.createElement('div');
    renglon.className = 'renglon';
    const p = document.createElement('p');
    p.id = 'p' + i; p.textContent = t; p.tabIndex = 0;
    p.onclick = () => empezarDesde(i);
    p.onkeydown = (e) => { if (e.key === 'Enter') empezarDesde(i); };
    const sel = document.createElement('select');
    sel.setAttribute('aria-label', 'Voz del párrafo ' + (i + 1));
    sel.innerHTML = '<option value="">Narrador (voz general)</option>' + $('voz').innerHTML;
    sel.value = voces[i] || '';
    sel.onchange = () => asignar(i, sel.value);
    renglon.append(p, sel);
    cont.appendChild(renglon);
  });
  $('vacio').hidden = true;
}

function invalidar(n) {
  if (urls[n]) URL.revokeObjectURL(urls[n]);
  urls[n] = undefined; blobs[n] = undefined;
}

let peticion = null;
async function completar(desde) {
  const mia = ++sesion;
  if (peticion) peticion.abort();
  const base = $('voz').value;
  for (let k = 0; k < total; k++) {
    const n = (desde + k) % total;
    if (mia !== sesion) return;
    if (urls[n]) continue;
    estado('Generando parte ' + (n + 1) + ' de ' + total + '…');
    peticion = new AbortController();
    let resp;
    try {
      resp = await fetch('/trozo', { method: 'POST', signal: peticion.signal, body: new URLSearchParams({ indice: cargado, n: n, voz: base }) });
    } catch (e) { return; }
    if (mia !== sesion) return;
    if (!resp.ok) { estado('Error en la parte ' + (n + 1) + '. Prueba de nuevo.'); return; }
    const blob = await resp.blob();
    blobs[n] = blob;
    urls[n] = URL.createObjectURL(blob);
    if (esperando === n) reproducir(n);
    else actualizarControles();
  }
  if (mia === sesion) estado('Listo: ' + total + ' partes');
}

async function empezarDesde(desde, cap = elegido) {
  if (cap !== cargado) {
    urls.forEach(u => u && URL.revokeObjectURL(u));
    urls = []; blobs = []; cargado = cap;
  }
  r.pause();
  if (urls[desde]) reproducir(desde);
  else { actual = desde; esperando = desde; marcar(desde); actualizarControles(); }
  completar(desde);
}

async function asignar(n, voz) {
  await fetch('/asignar', { method: 'POST', body: new URLSearchParams({ indice: cargado, n: n, voz: voz }) });
  if (n === actual) r.pause();
  invalidar(n);
  completar(Math.max(actual, 0));
}

$('subir').onclick = async () => {
  const f = $('archivo').files[0];
  if (!f) { $('estado-subida').textContent = 'Primero elige un archivo.'; return; }
  $('estado-subida').textContent = 'Leyendo…';
  const resp = await fetch('/subir', { method: 'POST', headers: { 'X-Nombre': encodeURIComponent(f.name) }, body: f });
  const datos = await resp.json();
  if (!resp.ok) { $('estado-subida').textContent = datos.error; return; }
  $('estado-subida').textContent = datos.capitulos.length + ' capítulos cargados';
  capitulos = datos.capitulos;
  cargado = null; elegido = null;
  const cont = $('capitulos');
  cont.innerHTML = '';
  datos.capitulos.forEach((c, i) => {
    const fila = document.createElement('div');
    fila.className = 'fila';
    fila.setAttribute('role', 'listitem');
    const marca = document.createElement('input');
    marca.type = 'checkbox';
    marca.dataset.i = i;
    marca.setAttribute('aria-label', 'Seleccionar ' + c);
    marca.onchange = actualizarDescargas;
    const b = document.createElement('button');
    b.textContent = c;
    b.onclick = async () => {
      elegido = i;
      sesion++;
      if (peticion) peticion.abort();
      cont.querySelectorAll('button').forEach(x => x.classList.remove('activo'));
      b.classList.add('activo');
      $('titulo-capitulo').textContent = c;
      estado('Preparando capítulo…');
      const info = await (await fetch('/trozos', { method: 'POST', body: new URLSearchParams({ indice: i }) })).json();
      total = info.total;
      $('analizar').disabled = false;
      mostrarTextos(info.textos, info.voces);
      if (total) empezarDesde(0, i); else estado('El capítulo está vacío');
      actualizarDescargas();
    };
    fila.append(marca, b);
    cont.appendChild(fila);
  });
  actualizarDescargas();
};

$('detener').onclick = () => { sesion++; r.pause(); estado('Detenido'); };

$('tema').onclick = () => {
  const claro = document.documentElement.getAttribute('data-tema') === 'claro';
  document.documentElement.setAttribute('data-tema', claro ? 'oscuro' : 'claro');
  $('tema').textContent = claro ? 'Tema claro' : 'Tema oscuro';
};

$('generar-texto').onclick = async () => {
  const texto = $('texto').value.trim();
  if (!texto) return;
  estado('Generando…');
  const resp = await fetch('/texto', { method: 'POST', body: new URLSearchParams({ texto, voz: $('voz').value }) });
  if (!resp.ok) { estado('Error al generar'); return; }
  audioTexto = await resp.blob();
  r.src = URL.createObjectURL(audioTexto);
  r.play();
  $('bajar-texto').disabled = false;
  estado('Listo');
};

$('bajar-texto').onclick = () => {
  if (audioTexto) guardar(URL.createObjectURL(audioTexto), 'texto.wav');
};
$('bajar-parte').onclick = () => {
  if (actual >= 0 && urls[actual]) guardar(urls[actual], limpio($('titulo-capitulo').textContent) + ' - parte ' + (actual + 1) + '.wav');
};
async function descargar(indices) {
  const botones = ['bajar-capitulo', 'bajar-seleccion', 'bajar-todos'].map($);
  botones.forEach(b => b.disabled = true);
  estado('Generando descarga… puede tardar varios minutos');
  try {
    const formato = $('formato').value;
    const resp = await fetch('/descargar', { method: 'POST', body: new URLSearchParams({ indices: indices.join(','), formato, voz: $('voz').value }) });
    if (!resp.ok) {
      const datosError = await resp.json().catch(() => ({}));
      estado('Error al descargar: ' + (datosError.error || resp.status));
      return;
    }
    const blob = await resp.blob();
    const nombre = indices.length > 1 ? 'capitulos.zip' : limpio(capitulos[indices[0]]) + '.' + formato;
    const url = URL.createObjectURL(blob);
    guardar(url, nombre);
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    estado('Descarga lista');
  } catch (e) {
    estado('Error de conexión al descargar');
  } finally {
    actualizarDescargas();
  }
}
$('bajar-capitulo').onclick = () => descargar([elegido]);
$('bajar-seleccion').onclick = () => descargar(seleccion());
$('bajar-todos').onclick = () => descargar(capitulos.map((_, i) => i));

document.addEventListener('keydown', (e) => {
  if (['TEXTAREA', 'INPUT', 'SELECT', 'BUTTON', 'A'].includes(document.activeElement.tagName)) return;
  if (e.code === 'Space') { e.preventDefault(); $('reproducir').click(); }
  if (e.key === 'ArrowRight') $('siguiente').click();
  if (e.key === 'ArrowLeft') $('anterior').click();
});
</script>
</body></html>"""

PATRON_CAPITULO = re.compile(r"^\s*(cap[ií]tulo|chapter)\s+[\w\d.:-]+.*$", re.IGNORECASE)


def extraer_texto(nombre, data):
    ext = nombre.lower().rsplit(".", 1)[-1]
    if ext in ("txt", "md"):
        return data.decode("utf-8", errors="replace")
    if ext == "docx":
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    if ext == "pdf":
        lector = pypdf.PdfReader(io.BytesIO(data))
        return "\n".join(p.extract_text() or "" for p in lector.pages)
    raise ValueError("Formato no soportado. Usa .txt, .md, .docx o .pdf")


def dividir_capitulos(texto):
    capitulos, titulo, lineas = [], "Inicio", []
    for linea in texto.splitlines():
        if PATRON_CAPITULO.match(linea):
            if "".join(lineas).strip():
                capitulos.append((titulo, "\n".join(lineas).strip()))
            titulo, lineas = linea.strip(), []
        else:
            lineas.append(linea)
    if "".join(lineas).strip():
        capitulos.append((titulo, "\n".join(lineas).strip()))
    if len(capitulos) <= 1:
        palabras = texto.split()
        bloques = [" ".join(palabras[i:i + 2000]) for i in range(0, len(palabras), 2000)]
        capitulos = [(f"Parte {n + 1}", b) for n, b in enumerate(bloques)]
    return capitulos


def parrafos(texto):
    return [linea.strip() for linea in texto.splitlines() if linea.strip()]


def voz_parte(indice, n, base):
    return documento["voces"].get(indice, {}).get(n, base)


cerrojo = threading.Lock()


def generar_wav(texto, voz):
    with cerrojo:
        audio = [c for _, _, c in pipeline(texto, voice=voz)]
    return a_wav(np.concatenate(audio))


def generar_audio(texto, voz):
    with cerrojo:
        return np.concatenate([c for _, _, c in pipeline(texto, voice=voz)])


def aplicar_ambiente(indice, n, audio):
    nombre = documento["ambientes"].get(indice, {}).get(n)
    return mezclar_ambiente(audio, nombre) if nombre else audio


def audio_capitulo(indice, base):
    _, texto = documento["capitulos"][indice]
    audios = [
        aplicar_ambiente(indice, n, generar_audio(parte, voz_parte(indice, n, base)))
        for n, parte in enumerate(parrafos(texto))
    ]
    return np.concatenate(audios)


def a_wav(audio):
    buf = io.BytesIO()
    sf.write(buf, audio, 24000, format="WAV")
    return buf.getvalue()


def a_mp3(audio):
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
    codificador = lameenc.Encoder()
    codificador.set_bit_rate(128)
    codificador.set_in_sample_rate(24000)
    codificador.set_channels(1)
    codificador.set_quality(2)
    return codificador.encode(pcm) + codificador.flush()


class Handler(BaseHTTPRequestHandler):
    def _enviar(self, codigo, tipo, data):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, codigo, obj):
        self._enviar(codigo, "application/json", json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _leer(self):
        largo = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(largo)

    def _campos(self):
        return {k: v[0] for k, v in parse_qs(self._leer().decode("utf-8")).items()}

    def do_GET(self):
        if self.path == "/":
            self._enviar(200, "text/html; charset=utf-8", PAGINA.encode("utf-8"))
        elif self.path == "/manifest.webmanifest":
            manifiesto = {
                "name": "Lector de voz",
                "short_name": "Lector",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#0f0f10",
                "theme_color": "#0f0f10",
                "icons": [
                    {"src": "/icono-180.png", "sizes": "180x180", "type": "image/png"},
                    {"src": "/icono-512.png", "sizes": "512x512", "type": "image/png"},
                ],
            }
            self._enviar(200, "application/manifest+json", json.dumps(manifiesto).encode("utf-8"))
        elif self.path in ("/icono-180.png", "/icono-512.png"):
            with open(self.path.lstrip("/"), "rb") as f:
                self._enviar(200, "image/png", f.read())
        else:
            self.send_error(404)

    def do_POST(self):
        try:
            if self.path == "/subir":
                nombre = unquote(self.headers.get("X-Nombre", "archivo.txt"))
                texto = extraer_texto(nombre, self._leer())
                documento["nombre"] = nombre
                documento["capitulos"] = dividir_capitulos(texto)
                documento["voces"] = {}
                documento["ambientes"] = {}
                self._json(200, {"capitulos": [t for t, _ in documento["capitulos"]]})
            elif self.path == "/trozos":
                campos = self._campos()
                indice = int(campos["indice"])
                _, texto = documento["capitulos"][indice]
                textos = parrafos(texto)
                asignadas = [documento["voces"].get(indice, {}).get(n, "") for n in range(len(textos))]
                self._json(200, {"total": len(textos), "textos": textos, "voces": asignadas})
            elif self.path == "/trozo":
                campos = self._campos()
                indice, n = int(campos["indice"]), int(campos["n"])
                _, texto = documento["capitulos"][indice]
                trozo = parrafos(texto)[n]
                audio = generar_audio(trozo, voz_parte(indice, n, campos.get("voz", "ef_dora")))
                self._enviar(200, "audio/wav", a_wav(aplicar_ambiente(indice, n, audio)))
            elif self.path == "/analizar":
                indice = int(self._campos()["indice"])
                _, texto = documento["capitulos"][indice]
                resultado = analisis.analizar(parrafos(texto))
                documento["voces"][indice] = resultado["voces"]
                documento["ambientes"][indice] = resultado["ambientes"]
                self._json(200, {"personajes": resultado["personajes"], "ambientes": len(resultado["ambientes"])})
            elif self.path == "/asignar":
                campos = self._campos()
                indice, n, voz = int(campos["indice"]), int(campos["n"]), campos.get("voz", "")
                if voz and voz not in VOCES:
                    raise ValueError("Voz no soportada")
                asignaciones = documento["voces"].setdefault(indice, {})
                if voz:
                    asignaciones[n] = voz
                else:
                    asignaciones.pop(n, None)
                self._json(200, {"ok": True})
            elif self.path == "/texto":
                campos = self._campos()
                self._enviar(200, "audio/wav", generar_wav(campos.get("texto", ""), campos.get("voz", "ef_dora")))
            elif self.path == "/descargar":
                campos = self._campos()
                formato = campos.get("formato", "mp3")
                if formato not in ("mp3", "wav"):
                    raise ValueError("Formato no soportado. Usa mp3 o wav")
                codificar = a_mp3 if formato == "mp3" else a_wav
                voz = campos.get("voz", "ef_dora")
                archivos = {}
                for i in (int(x) for x in campos["indices"].split(",")):
                    nombre = re.sub(r'[\\/:*?"<>|]+', "", documento["capitulos"][i][0]).strip()[:80] or "capitulo"
                    archivos[f"{i + 1:02d} - {nombre}.{formato}"] = codificar(audio_capitulo(i, voz))
                if len(archivos) == 1:
                    (_, datos), = archivos.items()
                    self._enviar(200, "audio/mpeg" if formato == "mp3" else "audio/wav", datos)
                else:
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
                        for nombre, datos in archivos.items():
                            z.writestr(nombre, datos)
                    self._enviar(200, "application/zip", buf.getvalue())
            else:
                self.send_error(404)
        except Exception as e:
            self._json(500, {"error": str(e)})


if __name__ == "__main__":
    print(f"Interfaz en http://localhost:{PORT}")
    import os
    host = "0.0.0.0" if os.environ.get("LECTOR_RED") == "1" else "127.0.0.1"
    ThreadingHTTPServer((host, PORT), Handler).serve_forever()
