import io
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote

import docx
import numpy as np
import pypdf
import soundfile as sf
from kokoro import KPipeline

PORT = 8765
pipeline = KPipeline(lang_code="e")
documento = {"nombre": "", "capitulos": []}

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
:root { --fondo:#0f0f10; --panel:#1a1a1d; --texto:#f5f5f5; --suave:#b8b8c0; --acento:#ffd400; --foco:#00e5ff; --borde:#3a3a40; }
[data-tema="claro"] { --fondo:#fafafa; --panel:#ffffff; --texto:#111; --suave:#4a4a52; --acento:#1d4ed8; --foco:#0369a1; --borde:#d4d4d8; }
* { box-sizing: border-box; }
body { margin:0; font-family: -apple-system, Arial, sans-serif; font-size:20px; line-height:1.6; background:var(--fondo); color:var(--texto); }
header { display:flex; flex-wrap:wrap; align-items:center; gap:12px; padding:14px 20px; background:var(--panel); border-bottom:1px solid var(--borde); position:sticky; top:0; z-index:2; }
header h1 { font-size:22px; margin:0 auto 0 0; }
button, select, input[type=file]::file-selector-button { font:inherit; font-size:18px; padding:10px 16px; min-height:48px; border-radius:10px; border:2px solid var(--borde); background:var(--panel); color:var(--texto); cursor:pointer; }
button.primario { background:var(--acento); color:#000; border-color:var(--acento); font-weight:bold; }
button:disabled { opacity:.45; cursor:default; }
button:focus-visible, select:focus-visible, textarea:focus-visible, #lectura p:focus-visible { outline:4px solid var(--foco); outline-offset:2px; }
.layout { display:grid; grid-template-columns: 280px 1fr; min-height: calc(100vh - 150px); }
aside { border-right:1px solid var(--borde); padding:18px; background:var(--panel); overflow-y:auto; }
aside h2, main h2 { font-size:16px; text-transform:uppercase; letter-spacing:.08em; color:var(--suave); margin:8px 0 12px; }
#capitulos { display:flex; flex-direction:column; gap:8px; }
#capitulos button { text-align:left; width:100%; }
#capitulos button.activo { border-color:var(--acento); box-shadow: inset 4px 0 0 var(--acento); }
main { padding:24px 28px 40px; max-width: 820px; width:100%; }
#titulo-capitulo { font-size:26px; margin:0 0 16px; }
#lectura { font-size:21px; line-height:1.75; }
#lectura p { padding:10px 14px; border-radius:10px; cursor:pointer; margin:6px 0; border-left:4px solid transparent; }
#lectura p:hover { background: rgba(127,127,127,.12); }
#lectura p.actual { background: var(--acento); color:#000; border-left-color:#000; font-weight:600; }
.vacio { color:var(--suave); font-size:20px; padding:30px 0; }
.tarjeta { background:var(--panel); border:1px solid var(--borde); border-radius:12px; padding:14px; margin-bottom:14px; }
textarea { width:100%; height:120px; font:inherit; font-size:18px; padding:12px; border-radius:10px; border:2px solid var(--borde); background:var(--fondo); color:var(--texto); }
.reproductor { position:sticky; bottom:0; background:var(--panel); border-top:1px solid var(--borde); padding:12px 20px; display:flex; flex-wrap:wrap; align-items:center; gap:10px 14px; z-index:2; }
.reproductor .ctrl { min-width:56px; min-height:56px; border-radius:50%; font-size:22px; padding:0; }
.reproductor .ctrl.grande { min-width:68px; min-height:68px; font-size:28px; background:var(--acento); color:#000; border-color:var(--acento); }
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
    </select>
    <div id="capitulos" role="list" aria-label="Capítulos"></div>
    <h2 style="margin-top:24px;">Texto suelto</h2>
    <textarea id="texto" aria-label="Pega un texto para escucharlo" placeholder="Pega aquí un texto..."></textarea>
    <button id="generar-texto" style="margin-top:8px; width:100%;">Generar audio del texto</button>
    <button id="bajar-texto" style="margin-top:8px; width:100%;" title="Descargar el audio del texto (.wav)" disabled>&#11015; Descargar audio del texto</button>
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
  <button id="bajar-parte" aria-label="Descargar esta parte" title="Descargar esta parte (.wav)" disabled>&#11015; Parte</button>
  <button id="bajar-capitulo" aria-label="Descargar el capítulo completo" title="Descargar el capítulo completo (.wav)" disabled>&#11015; Capítulo</button>
  <div id="estado" role="status" aria-live="polite"></div>
</div>
<audio id="reproductor" preload="auto"></audio>

<script>
let elegido = null, sesion = 0, urls = [], blobs = [], audioTexto = null, actual = -1, esperando = null, total = 0;
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
  $('bajar-capitulo').disabled = !hay || urls.filter(Boolean).length < total;
}

function guardar(url, nombre) {
  const a = document.createElement('a');
  a.href = url; a.download = nombre;
  document.body.appendChild(a); a.click(); a.remove();
}
const limpio = (s) => (s || 'audio').replace(/[\\/:*?"<>|]+/g, '').trim().slice(0, 80) || 'audio';

async function unirWavs(blobs) {
  const trozos = [];
  let cabecera = null;
  for (const b of blobs) {
    const buf = new Uint8Array(await b.arrayBuffer());
    const vista = new DataView(buf.buffer);
    let pos = 12;
    while (pos + 8 <= buf.length) {
      const id = String.fromCharCode(...buf.slice(pos, pos + 4));
      const largo = vista.getUint32(pos + 4, true);
      if (id === 'data') { trozos.push(buf.slice(pos + 8, pos + 8 + largo)); break; }
      if (id === 'fmt ' && !cabecera) cabecera = buf.slice(pos, pos + 8 + largo);
      pos += 8 + largo + (largo % 2);
    }
  }
  const datos = trozos.reduce((n, t) => n + t.length, 0);
  const out = new Uint8Array(12 + cabecera.length + 8 + datos);
  const v = new DataView(out.buffer);
  out.set([82, 73, 70, 70], 0); v.setUint32(4, out.length - 8, true); out.set([87, 65, 86, 69], 8);
  out.set(cabecera, 12);
  let p = 12 + cabecera.length;
  out.set([100, 97, 116, 97], p); v.setUint32(p + 4, datos, true); p += 8;
  trozos.forEach(t => { out.set(t, p); p += t.length; });
  return new Blob([out], { type: 'audio/wav' });
}

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
  else { actual = n; esperando = n; marcar(n); actualizarControles(); }
}

r.onended = () => {
  const s = actual + 1;
  if (s >= total) { estado('Capítulo terminado'); actualizarControles(); return; }
  if (urls[s]) reproducir(s); else { esperando = s; actual = s; marcar(s); actualizarControles(); }
};
r.onplay = r.onpause = actualizarControles;
r.ontimeupdate = () => {
  const d = r.duration || 0;
  $('progreso').value = d ? (r.currentTime / d) * 100 : 0;
  $('tiempo').textContent = formato(r.currentTime) + ' / ' + formato(d);
};
$('progreso').oninput = (e) => { if (r.duration) r.currentTime = (e.target.value / 100) * r.duration; };
$('velocidad').onchange = (e) => { r.playbackRate = parseFloat(e.target.value); };
$('reproducir').onclick = () => {
  if (actual < 0) { irA(0); return; }
  if (r.paused) { if (urls[actual]) r.play(); else irA(actual); } else r.pause();
};
$('anterior').onclick = () => irA(actual - 1);
$('siguiente').onclick = () => irA(actual + 1);

function mostrarTextos(lista) {
  const cont = $('lectura');
  cont.innerHTML = '';
  lista.forEach((t, i) => {
    const p = document.createElement('p');
    p.id = 'p' + i; p.textContent = t; p.tabIndex = 0;
    p.onclick = () => empezarDesde(i);
    p.onkeydown = (e) => { if (e.key === 'Enter') empezarDesde(i); };
    cont.appendChild(p);
  });
  $('vacio').hidden = true;
}

let peticion = null;
async function empezarDesde(desde, cap = elegido) {
  const mia = ++sesion;
  if (peticion) peticion.abort();
  r.pause();
  urls.forEach(u => u && URL.revokeObjectURL(u));
  urls = []; blobs = []; actual = -1; esperando = null;
  actualizarControles();
  const voz = $('voz').value;
  for (let n = desde; n < total; n++) {
    if (mia !== sesion) return;
    estado('Generando parte ' + (n + 1) + ' de ' + total + '…');
    peticion = new AbortController();
    let resp;
    try {
      resp = await fetch('/trozo', { method: 'POST', signal: peticion.signal, body: new URLSearchParams({ indice: cap, n: n, voz: voz }) });
    } catch (e) { return; }
    if (mia !== sesion) return;
    if (!resp.ok) { estado('Error en la parte ' + (n + 1) + '. Prueba de nuevo.'); return; }
    const blob = await resp.blob();
    blobs[n] = blob;
    urls[n] = URL.createObjectURL(blob);
    if (actual < 0 && n === desde) reproducir(n);
    else if (esperando === n) reproducir(n);
    else actualizarControles();
  }
  if (mia === sesion) estado('Listo: ' + total + ' partes');
}

$('subir').onclick = async () => {
  const f = $('archivo').files[0];
  if (!f) { $('estado-subida').textContent = 'Primero elige un archivo.'; return; }
  $('estado-subida').textContent = 'Leyendo…';
  const resp = await fetch('/subir', { method: 'POST', headers: { 'X-Nombre': encodeURIComponent(f.name) }, body: f });
  const datos = await resp.json();
  if (!resp.ok) { $('estado-subida').textContent = datos.error; return; }
  $('estado-subida').textContent = datos.capitulos.length + ' capítulos cargados';
  const cont = $('capitulos');
  cont.innerHTML = '';
  datos.capitulos.forEach((c, i) => {
    const b = document.createElement('button');
    b.textContent = c;
    b.setAttribute('role', 'listitem');
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
      mostrarTextos(info.textos);
      if (total) empezarDesde(0, i); else estado('El capítulo está vacío');
    };
    cont.appendChild(b);
  });
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
$('bajar-capitulo').onclick = async () => {
  estado('Uniendo audio…');
  const todo = await unirWavs(blobs.slice(0, total));
  const url = URL.createObjectURL(todo);
  guardar(url, limpio($('titulo-capitulo').textContent) + '.wav');
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  estado('Capítulo descargado');
};

document.addEventListener('keydown', (e) => {
  if (['TEXTAREA', 'INPUT', 'SELECT'].includes(document.activeElement.tagName)) return;
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


def partir(texto, max_palabras=60):
    oraciones = re.split(r"(?<=[.!?…])\s+", texto.strip())
    trozos, actual, cuenta = [], [], 0
    for oracion in oraciones:
        n = len(oracion.split())
        if actual and cuenta + n > max_palabras:
            trozos.append(" ".join(actual))
            actual, cuenta = [], 0
        actual.append(oracion)
        cuenta += n
    if actual:
        trozos.append(" ".join(actual))
    return [t for t in trozos if t.strip()]


cerrojo = threading.Lock()


def generar_wav(texto, voz):
    with cerrojo:
        audio = [c for _, _, c in pipeline(texto, voice=voz)]
    buf = io.BytesIO()
    sf.write(buf, np.concatenate(audio), 24000, format="WAV")
    return buf.getvalue()


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
                self._json(200, {"capitulos": [t for t, _ in documento["capitulos"]]})
            elif self.path == "/trozos":
                campos = self._campos()
                _, texto = documento["capitulos"][int(campos["indice"])]
                partes = partir(texto)
                self._json(200, {"total": len(partes), "textos": partes})
            elif self.path == "/trozo":
                campos = self._campos()
                _, texto = documento["capitulos"][int(campos["indice"])]
                trozo = partir(texto)[int(campos["n"])]
                self._enviar(200, "audio/wav", generar_wav(trozo, campos.get("voz", "ef_dora")))
            elif self.path == "/texto":
                campos = self._campos()
                self._enviar(200, "audio/wav", generar_wav(campos.get("texto", ""), campos.get("voz", "ef_dora")))
            else:
                self.send_error(404)
        except Exception as e:
            self._json(500, {"error": str(e)})


if __name__ == "__main__":
    print(f"Interfaz en http://localhost:{PORT}")
    import os
    host = "0.0.0.0" if os.environ.get("LECTOR_RED") == "1" else "127.0.0.1"
    ThreadingHTTPServer((host, PORT), Handler).serve_forever()
