from PIL import Image, ImageDraw

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Fondo redondeado oscuro
d.rounded_rectangle((40, 40, S - 40, S - 40), radius=200, fill=(26, 26, 29, 255))

amarillo = (255, 212, 0, 255)
blanco = (245, 245, 245, 255)

# Bocina
d.polygon([(260, 430), (380, 430), (540, 300), (540, 724), (380, 594), (260, 594)], fill=amarillo)

# Ondas de sonido
for radio, grosor in [(190, 46), (300, 46), (410, 46)]:
    caja = (540 - radio + 60, 512 - radio, 540 + radio + 60, 512 + radio)
    d.arc(caja, start=-40, end=40, fill=blanco, width=grosor)

# Redondear bordes de la bocina con un trazo
img.save("icono_1024.png")
print("icono creado")
