#!/usr/bin/env python3
"""
Descarga precios oficiales de carburantes (MITECO / Ministerio de
Transición Ecológica) y genera prices.json con la media nacional de
Gasóleo A.

API: https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/
     PreciosCarburantes/EstacionesTerrestres/

Output: prices.json en la raíz del repo, con esquema:
{
  "gasoleo_a":            1.823,      # media nacional surtidor (€/l)
  "gasoleo_a_profesional": 1.390,     # surtidor − devolución − descuento flota
  "estaciones":           11542,      # nº estaciones consideradas
  "fecha":                "11/05/2026 09:30:00",
  "iso_date":             "2026-05-11T09:30:00",
  "fuente":               "MITECO",
  "stale":                false
}

Si el fetch falla, mantiene el prices.json existente y marca stale=true.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = (
    "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
    "PreciosCarburantes/EstacionesTerrestres/"
)

# Descuentos profesionales (€/l) — alineados con la nota del propio index.html:
#   "devolución gasóleo profesional (~0,067 €/l) + descuento tarjeta flota
#    (~0,25–0,35 €/l). Típico en flotas medianas-grandes España."
# Usamos el extremo alto del descuento de flota para flotas medianas-grandes,
# lo que reproduce el valor histórico hardcoded (surtidor 1,863 → profesional 1,43).
DEVOLUCION_PROFESIONAL = 0.067
DESCUENTO_FLOTA       = 0.366  # ≈ extremo alto del rango 0,25–0,35

REPO_ROOT  = Path(__file__).resolve().parents[2]
OUT_PATH   = REPO_ROOT / "prices.json"

TIMEOUT_S  = 30
USER_AGENT = "calculadora-camion-electrico/1.0 (+github actions)"


def fetch_miteco() -> dict:
    req = urllib.request.Request(API_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        raw = resp.read().decode("utf-8-sig")
    return json.loads(raw)


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


def write_stale_fallback(reason: str) -> int:
    existing = load_existing()
    if existing is None:
        print(f"::error::Fetch falló y no hay prices.json previo: {reason}", file=sys.stderr)
        return 1
    existing["stale"] = True
    existing["last_error"] = reason
    existing["last_check"] = datetime.now(timezone.utc).isoformat()
    OUT_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"::warning::MITECO inaccesible — manteniendo datos previos (stale): {reason}")
    return 0


def main() -> int:
    try:
        data = fetch_miteco()
    except Exception as e:
        return write_stale_fallback(f"fetch error: {e}")

    if data.get("ResultadoConsulta") != "OK":
        return write_stale_fallback(f"API status: {data.get('ResultadoConsulta')}")

    stations = data.get("ListaEESSPrecio", [])
    try:
        media, n = compute_average(stations)
    except Exception as e:
        return write_stale_fallback(f"average error: {e}")

    fecha = data.get("Fecha", "")
    surtidor = round(media, 3)
    profesional = round(surtidor - DEVOLUCION_PROFESIONAL - DESCUENTO_FLOTA, 3)

    output = {
        "gasoleo_a":             surtidor,
        "gasoleo_a_profesional": profesional,
        "estaciones":            n,
        "fecha":                 fecha,
        "iso_date":              parse_iso(fecha),
        "fuente":                "MITECO",
        "stale":                 False,
        "last_check":            datetime.now(timezone.utc).isoformat(),
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
