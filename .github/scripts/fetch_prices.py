#!/usr/bin/env python3
"""
Descarga precios oficiales de carburantes (MITECO / Ministerio de
Transición Ecológica) y genera prices.json con la media nacional de
Gasóleo A.

API: https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/
     PreciosCarburantes/EstacionesTerrestres/

Output: prices.json en la raíz del repo, con esquema:
{
  "gasoleo_a":             1.823,     # media nacional surtidor (€/l)
  "gasoleo_a_profesional": 1.390,     # surtidor − devolución − descuento flota
  "estaciones":            11542,     # nº estaciones consideradas
  "fecha":                 "11/05/2026 09:30:00",
  "iso_date":              "2026-05-11T09:30:00",
  "fuente":                "MITECO",
  "stale":                 false,     # true si se mantuvo dato viejo
  "last_check":            "...+00:00",  # ISO 8601 UTC del último intento
  "last_successful_fetch": "...+00:00",  # ISO 8601 UTC del último fetch con éxito (null si nunca)
  "descuentos_profesional": { ... }
}

Si el fetch falla, reintenta con backoff (ver MAX_ATTEMPTS); si tras los
reintentos sigue fallando, mantiene el prices.json existente con stale=true.
El script termina en rojo (exit 1) si last_successful_fetch supera
STALE_THRESHOLD_DAYS días de antigüedad.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = (
    "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
    "PreciosCarburantes/EstacionesTerrestres/"
)

# Descuentos profesionales (€/l) para flotas medianas-grandes en España.
# Suma de dos conceptos independientes:
#   1. Devolución parcial del Impuesto sobre Hidrocarburos por gasóleo
#      profesional: 0,049 €/l. Valor estructural fijado por la Orden
#      HFP/941/2022, vigente desde el 1 de enero de 2019, uniforme en
#      todo el territorio nacional. Tope 50.000 l/vehículo/año.
#      Gestionado a posteriori por la AEAT, no es un descuento en surtidor.
#   2. Descuento típico de tarjeta profesional de flota: 0,100 €/l.
#      Extremo alto del rango habitual sin promociones extraordinarias:
#      Galp Flota Business (~6-8 cts/l), Repsol Solred Precio Profesional
#      (13-15 cts/l con >8.000 l/mes), AS-24 (~11-15 cts/l).
# NOTA: cifras estables que NO reflejan el régimen extraordinario del
# RD-ley 7/2026 (ayuda directa de 20 cts/l + IVA al 10%, vigente del
# 22 de marzo al 30 de junio de 2026). Decisión deliberada para que la
# herramienta sirva para comparar escenarios entre sí a largo plazo.
DEVOLUCION_PROFESIONAL = 0.049
DESCUENTO_FLOTA       = 0.100  # ≈ extremo alto del rango habitual 0,06–0,10

REPO_ROOT  = Path(__file__).resolve().parents[2]
OUT_PATH   = REPO_ROOT / "prices.json"

TIMEOUT_S  = 30
USER_AGENT = "calculadora-camion-electrico/1.0 (+github actions)"

# Reintentos ante fallos de red transitorios.
MAX_ATTEMPTS   = 4
BACKOFF_DELAYS = (30, 60, 120)  # segundos de espera tras el intento n (1-indexado)

# Umbral por defecto si STALE_THRESHOLD_DAYS no está en el entorno.
DEFAULT_STALE_THRESHOLD_DAYS = 3


def fetch_miteco() -> dict:
    req = urllib.request.Request(API_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        raw = resp.read().decode("utf-8-sig")
    return json.loads(raw)


def _is_transient(exc: Exception) -> bool:
    """True si el error merece reintento (red transitoria, HTTP 5xx o 429).

    NO transitorio: HTTP 4xx salvo 429 (Forbidden, Not Found...): reintentar
    no cambia el resultado.
    """
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code >= 500 or exc.code == 429
    if isinstance(exc, urllib.error.URLError):
        # .reason suele ser un OSError: timeout, conexión reseteada,
        # rehusada, fallo de DNS... todos transitorios.
        return isinstance(exc.reason, OSError)
    return isinstance(exc, OSError)


def fetch_with_retries() -> dict:
    """fetch_miteco con hasta MAX_ATTEMPTS intentos y backoff exponencial.

    Solo reintenta ante errores transitorios (ver _is_transient). Los errores
    permanentes (HTTP 4xx salvo 429) se propagan de inmediato.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fetch_miteco()
        except Exception as exc:
            if not _is_transient(exc):
                print(f"Intento {attempt}/{MAX_ATTEMPTS} fallido: {exc}. "
                      f"Error no transitorio — no se reintenta.", file=sys.stderr)
                raise
            if attempt == MAX_ATTEMPTS:
                print(f"Intento {attempt}/{MAX_ATTEMPTS} fallido: {exc}. "
                      f"Agotados los reintentos.", file=sys.stderr)
                raise
            delay = BACKOFF_DELAYS[attempt - 1]
            print(f"Intento {attempt}/{MAX_ATTEMPTS} fallido: {exc}. "
                  f"Reintentando en {delay}s...", file=sys.stderr)
            time.sleep(delay)
    raise RuntimeError("fetch_with_retries: estado inalcanzable")


def parse_price(value: str) -> float | None:
    """MITECO devuelve precios como '1,823' (coma decimal). Vacío = sin servicio."""
    if not value:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def parse_iso(fecha: str) -> str:
    # MITECO: "DD/MM/YYYY HH:MM:SS"
    try:
        return datetime.strptime(fecha, "%d/%m/%Y %H:%M:%S").isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def compute_average(stations: list[dict]) -> tuple[float, int]:
    prices = []
    for s in stations:
        p = parse_price(s.get("Precio Gasoleo A", ""))
        # Filtramos outliers obvios (precio claramente inválido).
        if p is not None and 0.5 < p < 3.5:
            prices.append(p)
    if not prices:
        raise RuntimeError("No se pudo extraer ningún precio válido de Gasóleo A")
    return statistics.mean(prices), len(prices)


def load_existing() -> dict | None:
    if not OUT_PATH.exists():
        return None
    try:
        return json.loads(OUT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_stale_fallback(reason: str) -> dict | None:
    """Mantiene el prices.json previo marcándolo como stale.

    Devuelve el dict escrito (para el gate de frescura) o None si no existía
    un prices.json previo del que tirar.
    """
    existing = load_existing()
    if existing is None:
        print(f"::error::Fetch falló y no hay prices.json previo: {reason}", file=sys.stderr)
        return None
    existing["stale"] = True
    existing["last_error"] = reason
    existing["last_check"] = datetime.now(timezone.utc).isoformat()
    # last_successful_fetch conserva su valor previo; None si nunca hubo éxito
    # (caso borde del primer run tras introducir el campo).
    existing.setdefault("last_successful_fetch", None)
    OUT_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"::warning::MITECO inaccesible — manteniendo datos previos (stale): {reason}")
    return existing


def stale_threshold_days() -> int:
    """Lee STALE_THRESHOLD_DAYS del entorno; usa el default si falta o es inválido."""
    raw = os.environ.get("STALE_THRESHOLD_DAYS")
    if raw is None:
        return DEFAULT_STALE_THRESHOLD_DAYS
    try:
        value = int(raw)
    except ValueError:
        print(f"::warning::STALE_THRESHOLD_DAYS inválido ({raw!r}); "
              f"usando {DEFAULT_STALE_THRESHOLD_DAYS}.", file=sys.stderr)
        return DEFAULT_STALE_THRESHOLD_DAYS
    if value < 0:
        print(f"::warning::STALE_THRESHOLD_DAYS negativo ({value}); "
              f"usando {DEFAULT_STALE_THRESHOLD_DAYS}.", file=sys.stderr)
        return DEFAULT_STALE_THRESHOLD_DAYS
    return value


def staleness_gate(data: dict, threshold_days: int) -> int:
    """Falla en rojo (1) si el último fetch con éxito supera el umbral.

    Compara contra last_successful_fetch en días naturales (UTC). Si el campo
    es None (nunca hubo éxito), se considera el umbral excedido.
    """
    lsf = data.get("last_successful_fetch")
    if not lsf:
        print(f"::error::Nunca se ha obtenido dato fresco de MITECO "
              f"(last_successful_fetch vacío). Umbral de {threshold_days} "
              f"día(s) considerado excedido.", file=sys.stderr)
        return 1
    last_success = datetime.fromisoformat(lsf)
    age_days = (datetime.now(timezone.utc).date() - last_success.date()).days
    if age_days > threshold_days:
        print(f"::error::Dato obsoleto: {age_days} día(s) desde el último fetch "
              f"con éxito ({lsf}); umbral = {threshold_days}. Fallo en rojo.",
              file=sys.stderr)
        return 1
    print(f"Frescura OK: {age_days} día(s) desde el último fetch con éxito "
          f"(umbral {threshold_days}).")
    return 0


def main() -> int:
    threshold = stale_threshold_days()

    def fallback(reason: str) -> int:
        out = write_stale_fallback(reason)
        if out is None:
            return 1
        return staleness_gate(out, threshold)

    try:
        data = fetch_with_retries()
    except Exception as e:
        return fallback(f"fetch error: {e}")

    if data.get("ResultadoConsulta") != "OK":
        return fallback(f"API status: {data.get('ResultadoConsulta')}")

    stations = data.get("ListaEESSPrecio", [])
    try:
        media, n = compute_average(stations)
    except Exception as e:
        return fallback(f"average error: {e}")

    fecha = data.get("Fecha", "")
    surtidor = round(media, 3)
    profesional = round(surtidor - DEVOLUCION_PROFESIONAL - DESCUENTO_FLOTA, 3)

    now_iso = datetime.now(timezone.utc).isoformat()
    output = {
        "gasoleo_a":             surtidor,
        "gasoleo_a_profesional": profesional,
        "estaciones":            n,
        "fecha":                 fecha,
        "iso_date":              parse_iso(fecha),
        "fuente":                "MITECO",
        "stale":                 False,
        "last_check":            now_iso,
        "last_successful_fetch": now_iso,
        "descuentos_profesional": {
            "devolucion_profesional_eur_l": DEVOLUCION_PROFESIONAL,
            "descuento_flota_eur_l":        DESCUENTO_FLOTA,
        },
    }

    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK · Surtidor {surtidor:.3f} €/l · Profesional {profesional:.3f} €/l · {n} estaciones · {fecha}")

    # GitHub Actions outputs (para usar en pasos siguientes si se desea)
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"surtidor={surtidor}\n")
            fh.write(f"profesional={profesional}\n")
            fh.write(f"estaciones={n}\n")

    return staleness_gate(output, threshold)


if __name__ == "__main__":
    sys.exit(main())
