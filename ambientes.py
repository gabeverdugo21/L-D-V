import numpy as np

SR = 24000
AMBIENTES = ("lluvia", "viento", "pasos", "fuego")


def paso_bajo(x, corte, sr=SR):
    # Filtro paso bajo en el dominio de la frecuencia: simple y rápido con numpy.
    espectro = np.fft.rfft(x)
    frecuencias = np.fft.rfftfreq(len(x), 1 / sr)
    espectro[frecuencias > corte] = 0
    return np.fft.irfft(espectro, len(x))


def _gotas(n, densidad, sr=SR):
    # Impulsos cortos y aleatorios, usados para gotas de lluvia y chasquidos de fuego.
    x = np.zeros(n)
    cantidad = int(n / sr * densidad)
    posiciones = np.random.randint(0, n, cantidad)
    x[posiciones] = np.random.uniform(0.4, 1.0, cantidad)
    return x


def ambiente(nombre, segundos, sr=SR):
    n = int(segundos * sr)
    if nombre == "lluvia":
        base = paso_bajo(np.random.randn(n), 3000, sr) * 0.5
        return base + paso_bajo(_gotas(n, 25, sr), 6000, sr) * 0.3
    if nombre == "viento":
        ruido = np.cumsum(np.random.randn(n))
        ruido -= np.linspace(ruido[0], ruido[-1], n)
        ruido = ruido / (np.max(np.abs(ruido)) + 1e-9)
        modulacion = 0.6 + 0.4 * np.sin(2 * np.pi * 0.2 * np.arange(n) / sr)
        return ruido * modulacion * 0.6
    if nombre == "pasos":
        x = np.zeros(n)
        intervalo = int(sr * 0.55)
        duracion = int(sr * 0.08)
        golpe = paso_bajo(np.random.randn(duracion), 800, sr) * np.exp(-np.linspace(0, 6, duracion))
        for inicio in range(0, n - duracion, intervalo):
            x[inicio:inicio + duracion] += golpe * np.random.uniform(0.7, 1.0)
        return x * 0.5
    if nombre == "fuego":
        base = paso_bajo(np.random.randn(n), 400, sr) * 0.15
        return base + paso_bajo(_gotas(n, 40, sr), 4000, sr) * 0.4
    raise ValueError(f"Ambiente no soportado: {nombre}")


def mezclar(voz, nombre, nivel=0.25, sr=SR):
    # Repite el ambiente hasta cubrir la voz y lo baja de volumen para que no tape el habla.
    segundos = len(voz) / sr
    fondo = ambiente(nombre, segundos, sr)[: len(voz)]
    fundido = min(int(0.3 * sr), len(voz) // 2)
    rampa = np.ones(len(voz))
    rampa[:fundido] = np.linspace(0, 1, fundido)
    rampa[-fundido:] = np.linspace(1, 0, fundido)
    return np.clip(voz + fondo * rampa * nivel, -1, 1)
