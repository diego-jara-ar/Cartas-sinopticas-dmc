
from urllib.request import Request, urlopen
from html.parser import HTMLParser

URL = (
    "https://archivos.meteochile.gob.cl/"
    "portaldmc/cartaSinoptica/vercarta.php"
)

class ExtractorTexto(HTMLParser):
    def __init__(self):
        super().__init__()
        self.partes = []

    def handle_data(self, data):
        texto = " ".join(data.split())
        if texto:
            self.partes.append(texto)

solicitud = Request(
    URL,
    headers={"User-Agent": "Mozilla/5.0"}
)

with urlopen(solicitud, timeout=30) as respuesta:
    contenido = respuesta.read()
    codificacion = respuesta.headers.get_content_charset() or "utf-8"

html = contenido.decode(codificacion, errors="replace")

extractor = ExtractorTexto()
extractor.feed(html)

texto = "\n".join(extractor.partes)

print("¿Se encontró el título de condiciones sinópticas?")
print("Condiciones sinópticas" in texto)

print("\n¿Se encontró ZONA CENTRO?")
print("ZONA CENTRO" in texto)

print("\nFragmento de las condiciones:")
posicion = texto.find("ZONA CENTRO")
if posicion >= 0:
    print(texto[max(0, posicion - 200):posicion + 1500])
else:
    print("No se encontró el texto esperado.")
