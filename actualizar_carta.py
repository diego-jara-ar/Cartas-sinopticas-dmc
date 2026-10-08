
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from html import unescape
from html.parser import HTMLParser
import json
import re

BASE = (
    "https://archivos.meteochile.gob.cl/"
    "portaldmc/cartaSinoptica/"
)

SALIDA = Path("carta_actual.jpg")
FECHA_SALIDA = Path("ultima_actualizacion.txt")
CONDICIONES_SALIDA = Path("condiciones_actuales.json")

ZONAS = [
    ("ZONA NORTE", "Zona norte"),
    ("ZONA CENTRO", "Zona centro"),
    ("ZONA SUR", "Zona sur"),
    ("ZONA AUSTRAL", "Zona austral"),
    ("ARCHIPIÉLAGO JUAN FERNÁNDEZ", "Archipiélago Juan Fernández"),
    ("ISLA DE PASCUA", "Isla de Pascua"),
]


def obtener_url(url, timeout=30):
    solicitud = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Cache-Control": "no-cache",
        },
    )
    with urlopen(solicitud, timeout=timeout) as respuesta:
        datos = respuesta.read()
        tipo = respuesta.headers.get("Content-Type", "").lower()
        charset = respuesta.headers.get_content_charset()
    return datos, tipo, charset


def buscar_carta():
    ahora = datetime.now(timezone.utc)

    for dias in range(6):
        fecha = (ahora - timedelta(days=dias)).strftime("%Y%m%d")

        for hora in ("12", "00"):
            nombre = f"carta_sinoptica_{fecha}-{hora}UTC.jpg"
            url = BASE + nombre

            try:
                datos, tipo, _ = obtener_url(url, timeout=20)

                if (
                    "image/jpeg" not in tipo
                    or not datos.startswith(b"\xff\xd8\xff")
                    or len(datos) < 10000
                ):
                    continue

                return {
                    "fecha": fecha,
                    "hora": hora,
                    "nombre": nombre,
                    "url": url,
                    "datos": datos,
                }

            except (HTTPError, URLError, TimeoutError) as error:
                print(f"No disponible: {nombre} ({error})")

    raise RuntimeError(
        "No se encontró una carta válida en los últimos 6 días."
    )


class ExtractorHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.partes = []

    def handle_data(self, data):
        self.partes.append(data)

    def handle_entityref(self, name):
        self.partes.append(unescape(f"&{name};"))

    def handle_charref(self, name):
        self.partes.append(unescape(f"&#{name};"))


def limpiar_html(fragmento):
    extractor = ExtractorHTML()
    extractor.feed(unescape(fragmento))
    texto = unescape(" ".join(extractor.partes))
    return " ".join(texto.split())


def extraer_zonas(fragmento):
    # Las descripciones vienen separadas por etiquetas <br>
    # y los nombres de las zonas están en etiquetas <span>.
    fragmento = unescape(fragmento)

    resultado = {}

    for i, (nombre, etiqueta) in enumerate(ZONAS):
        patron = (
            r"<span\b[^>]*>\s*"
            + re.escape(nombre)
            + r"\s*</span>\s*:?\s*"
            + r"(.*?)(?=<br\s*/?>|$)"
        )

        coincidencia = re.search(
            patron,
            fragmento,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if coincidencia:
            descripcion = limpiar_html(coincidencia.group(1))
            if descripcion:
                resultado[etiqueta] = descripcion

    return resultado


def descargar_condiciones(carta):
    url = BASE + "vercarta.php"

    datos, _, charset = obtener_url(url)
    html = datos.decode(charset or "utf-8", errors="replace")

    # El documento de DMC puede contener varias emisiones.
    # Buscar el nombre exacto de la carta seleccionada.
    nombre = carta["nombre"]
    posiciones = list(re.finditer(re.escape(nombre), html))

    if not posiciones:
        raise ValueError(
            f"La página DMC no contiene la emisión {nombre}"
        )

    mejor = {}

    for coincidencia in posiciones:
        # Extraer únicamente el bloque cercano a la referencia
        # de esta emisión, sin pasar a la siguiente carta.
        inicio = coincidencia.end()
        resto = html[inicio:]

        siguiente = re.search(
            r"carta_sinoptica_\d{8}-(?:00|12)UTC\.jpg",
            resto,
        )

        fin = (
            inicio + siguiente.start()
            if siguiente
            else min(len(html), inicio + 12000)
        )

        fragmento = html[inicio:min(fin, inicio + 12000)]
        zonas = extraer_zonas(fragmento)

        if len(zonas) > len(mejor):
            mejor = zonas

    if len(mejor) < 4:
        raise ValueError(
            f"No se pudieron asociar suficientes zonas a {nombre}. "
            f"Zonas encontradas: {list(mejor)}"
        )

    return {
        "emision": f'{carta["fecha"]} {carta["hora"]}:00 UTC',
        "archivo_carta": nombre,
        "fuente": url,
        "zonas": mejor,
    }


def guardar_si_cambia(ruta, datos):
    if not ruta.exists() or ruta.read_bytes() != datos:
        ruta.write_bytes(datos)


def main():
    carta = buscar_carta()
    print(f'Carta encontrada: {carta["url"]}')

    # Intentar obtener las descripciones antes de
    # reemplazar los archivos publicados.
    condiciones = None

    try:
        condiciones = descargar_condiciones(carta)
        print("Condiciones recuperadas:")
        for zona, descripcion in condiciones["zonas"].items():
            print(f"  {zona}: {descripcion}")
    except Exception as error:
        print(f"No fue posible recuperar condiciones: {error}")

    guardar_si_cambia(SALIDA, carta["datos"])

    fecha_texto = (
        f'{carta["fecha"]} {carta["hora"]}:00 UTC\n'
        f'Fuente: {carta["url"]}\n'
    )
    guardar_si_cambia(
        FECHA_SALIDA,
        fecha_texto.encode("utf-8"),
    )

    if condiciones is not None:
        contenido = json.dumps(
            condiciones,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        guardar_si_cambia(CONDICIONES_SALIDA, contenido)
        print("Archivo condiciones_actuales.json preparado.")
    else:
        # No conservar textos de otra emisión como si fueran actuales.
        if CONDICIONES_SALIDA.exists():
            CONDICIONES_SALIDA.unlink()
        print("Condiciones no disponibles para esta emisión.")

    print("Actualización finalizada.")


if __name__ == "__main__":
    main()
