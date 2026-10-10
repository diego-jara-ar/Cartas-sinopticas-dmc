
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CARPETA = Path(__file__).resolve().parent

with open(CARPETA / "puntos.json", encoding="utf-8") as archivo:
    configuracion = json.load(archivo)

puntos = configuracion["puntos"]

variables = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "precipitation"
]

parametros = {
    "latitude": ",".join(str(p["latitud"]) for p in puntos),
    "longitude": ",".join(str(p["longitud"]) for p in puntos),
    "hourly": ",".join(variables),
    "models": "ecmwf_ifs",
    "timezone": "America/Santiago",
    "forecast_days": 4,
    "wind_speed_unit": "kmh"
}

url = (
    "https://api.open-meteo.com/v1/forecast?"
    + urllib.parse.urlencode(parametros)
)

solicitud = urllib.request.Request(
    url,
    headers={"User-Agent": "PanelMeteorologicoRM/1.0"}
)

with urllib.request.urlopen(solicitud, timeout=45) as respuesta:
    datos_api = json.load(respuesta)

if not isinstance(datos_api, list):
    datos_api = [datos_api]

if len(datos_api) != len(puntos):
    raise ValueError("Cantidad de pronosticos diferente a los puntos")

resultados = []

for punto, pronostico in zip(puntos, datos_api):
    horarios = pronostico["hourly"]

    for variable in variables:
        if variable not in horarios:
            raise ValueError(
                f"Falta {variable} para {punto['provincia']}"
            )

    resultados.append({
        "provincia": punto["provincia"],
        "latitud_solicitada": punto["latitud"],
        "longitud_solicitada": punto["longitud"],
        "latitud_modelo": pronostico.get("latitude"),
        "longitud_modelo": pronostico.get("longitude"),
        "elevacion_modelo": pronostico.get("elevation"),
        "horarios": horarios
    })

salida = {
    "fuente": "Open-Meteo",
    "modelo_solicitado": "ECMWF IFS",
    "zona_horaria": "America/Santiago",
    "actualizado_utc": datetime.now(timezone.utc).isoformat(),
    "puntos": resultados
}

destino = CARPETA / "datos.json"

with open(destino, "w", encoding="utf-8") as archivo:
    json.dump(salida, archivo, ensure_ascii=False, indent=2)

print("Pronosticos descargados correctamente")
print(f"Puntos procesados: {len(resultados)}")
print(f"Archivo generado: {destino}")
