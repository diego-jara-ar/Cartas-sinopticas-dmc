
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = (
    "https://archivos.meteochile.gob.cl/"
    "portaldmc/cartaSinoptica/"
)

SALIDA = Path("carta_actual.jpg")
FECHA_SALIDA = Path("ultima_actualizacion.txt")

def descargar_carta():
    ahora = datetime.now(timezone.utc)

    # Revisar cartas de los últimos 5 días,
    # comenzando por las emisiones más recientes.
    for dias in range(6):
        fecha = (ahora - timedelta(days=dias)).strftime("%Y%m%d")

        for hora in ("12", "00"):
            nombre = f"carta_sinoptica_{fecha}-{hora}UTC.jpg"
            url = BASE + nombre

            try:
                solicitud = Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"}
                )

                with urlopen(solicitud, timeout=20) as respuesta:
                    datos = respuesta.read()
                    tipo = respuesta.headers.get(
                        "Content-Type", ""
                    ).lower()

                # Comprobar que sea una imagen JPEG válida.
                if (
                    "image/jpeg" not in tipo
                    or not datos.startswith(b"\xff\xd8\xff")
                    or len(datos) < 10000
                ):
                    continue

                # Evitar sobrescribir si no hay cambios.
                if not SALIDA.exists() or SALIDA.read_bytes() != datos:
                    SALIDA.write_bytes(datos)

                FECHA_SALIDA.write_text(
                    f"{fecha} {hora}:00 UTC\n"
                    f"Fuente: {url}\n",
                    encoding="utf-8"
                )

                print(f"Carta encontrada: {url}")
                return

            except (HTTPError, URLError, TimeoutError) as error:
                print(f"No disponible: {nombre} ({error})")

    raise RuntimeError(
        "No se encontró una carta válida en los últimos 6 días."
    )

if __name__ == "__main__":
    descargar_carta()
