"""
pokemitas_mvp.py — Versión mínima funcional de Pokemitas Analyzer.

Implementa el pseudocódigo base (INICIO AnalizadorEquipoPokémon...):
  1. Lee un equipo de hasta 6 Pokémon desde un CSV (nombre, rol, IVs).
  2. Consulta tipos en PokéAPI, usando un cache local en /cache.
  3. Calcula debilidades de tipo por Pokémon.
  4. Evalúa la idoneidad de IVs contra el rol asignado.
  5. Calcula promedios de stats base del equipo.
  6. Analiza cobertura del equipo (tipos donde hay huecos de defensa).
  7. Muestra el resumen final.

Uso:
    pip install requests
    python pokemitas_mvp.py equipo_ejemplo.csv
"""

import csv
import json
import os
import sys

import requests

from logger_config import logger
from type_chart import TYPES, multiplicador_contra

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

ROLE_PRIORITY_STATS = {
    "Atacante": ["atk", "spatk", "spd"],
    "Defensor": ["hp", "def", "spdef"],
    "Soporte": ["hp", "spdef", "spd"],
    "Mixto": ["hp", "atk", "def", "spatk", "spdef", "spd"],
}
STAT_KEYS = ["hp", "atk", "def", "spatk", "spdef", "spd"]


# ---------------------------------------------------------------------
# 1. LEER EQUIPO (file management)
# ---------------------------------------------------------------------
def leer_equipo(path_csv: str) -> list[dict]:
    equipo = []
    try:
        with open(path_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=1):
                try:
                    ivs = {k: int(row[k]) for k in STAT_KEYS}
                except (ValueError, KeyError) as e:
                    logger.warning(f'Fila {i}: IV inválido o columna faltante ({e}) — se omite "{row.get("nombre", "?")}"')
                    continue

                for stat, val in ivs.items():
                    if not (0 <= val <= 31):
                        logger.warning(f'Fila {i} ("{row["nombre"]}"): IV de {stat}={val} fuera de rango 0-31')

                rol = row.get("rol", "Mixto").strip()
                if rol not in ROLE_PRIORITY_STATS:
                    logger.warning(f'Fila {i} ("{row["nombre"]}"): rol "{rol}" no reconocido — usando "Mixto"')
                    rol = "Mixto"

                equipo.append({"nombre": row["nombre"].strip(), "rol": rol, "ivs": ivs})
    except FileNotFoundError:
        logger.error(f'No se pudo encontrar el archivo "{path_csv}"')
        raise
    except PermissionError:
        logger.error(f'No se pudo leer "{path_csv}": permiso denegado')
        raise

    if not equipo:
        logger.warning(f'"{path_csv}" se leyó pero no contiene Pokémon válidos')
    else:
        logger.info(f'Archivo "{os.path.basename(path_csv)}" cargado correctamente ({len(equipo)} Pokémon)')

    return equipo


# ---------------------------------------------------------------------
# 2. CONSULTAR TABLA / POKEAPI + CACHE (file management + error handling)
# ---------------------------------------------------------------------
def consultar_pokemon(nombre: str) -> dict | None:
    cache_path = os.path.join(CACHE_DIR, f"{nombre.lower()}.json")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f'Cache hit: datos de "{nombre}" cargados desde cache local')
            return data
        except json.JSONDecodeError:
            logger.warning(f'Cache corrupto para "{nombre}" — se volverá a consultar PokéAPI')

    logger.info(f'Cache miss: consultando PokéAPI para "{nombre}"')
    url = f"https://pokeapi.co/api/v2/pokemon/{nombre.lower()}"
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f'No se pudo conectar a PokéAPI para "{nombre}": {e}')
        return None

    raw = resp.json()
    data = {
        "tipos": [t["type"]["name"] for t in raw["types"]],
        "stats": {s["stat"]["name"].replace("special-attack", "spatk")
                                    .replace("special-defense", "spdef")
                                    .replace("speed", "spd")
                                    .replace("attack", "atk")
                                    .replace("defense", "def")
                                    .replace("hp", "hp"): s["base_stat"]
                  for s in raw["stats"]},
    }

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        logger.info(f'"{nombre}" guardado en cache local')
    except PermissionError:
        logger.error(f'No se pudo escribir cache para "{nombre}": permiso denegado')

    return data


# ---------------------------------------------------------------------
# 3. DEBILIDADES DE TIPO
# ---------------------------------------------------------------------
def calcular_debilidades(tipos_defensor: list[str]) -> dict:
    return {t: multiplicador_contra(tipos_defensor, t) for t in TYPES
            if multiplicador_contra(tipos_defensor, t) > 1}


# ---------------------------------------------------------------------
# 4. EVALUAR IVs VS ROL
# ---------------------------------------------------------------------
def evaluar_ivs(ivs: dict, rol: str) -> str:
    prioridad = ROLE_PRIORITY_STATS[rol]
    promedio = sum(ivs[s] for s in prioridad) / len(prioridad)
    if promedio >= 26:
        return "Excelente"
    elif promedio >= 20:
        return "Buena"
    elif promedio >= 12:
        return "Regular"
    else:
        return "Pobre"


# ---------------------------------------------------------------------
# 5 y 6. PROMEDIOS Y COBERTURA DEL EQUIPO
# ---------------------------------------------------------------------
def calcular_promedios(stats_equipo: list[dict]) -> dict:
    n = len(stats_equipo)
    if n == 0:
        return {}
    return {s: round(sum(p[s] for p in stats_equipo) / n, 1) for s in STAT_KEYS}


def analizar_cobertura(debilidades_equipo: list[dict]) -> dict:
    conteo = {t: 0 for t in TYPES}
    for deb in debilidades_equipo:
        for t in deb:
            conteo[t] += 1
    huecos = {t: c for t, c in conteo.items() if c >= 3}
    return {"conteo_por_tipo": conteo, "huecos_del_equipo": huecos}


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main(path_csv: str):
    logger.info("=== Inicio de análisis de equipo ===")
    equipo = leer_equipo(path_csv)

    resultados = []
    stats_equipo = []
    debilidades_equipo = []

    for pkmn in equipo:
        data = consultar_pokemon(pkmn["nombre"])
        if data is None:
            logger.warning(f'Se omite "{pkmn["nombre"]}" del análisis por falta de datos de PokéAPI')
            continue

        debilidades = calcular_debilidades(data["tipos"])
        calificacion = evaluar_ivs(pkmn["ivs"], pkmn["rol"])

        resultados.append({
            "nombre": pkmn["nombre"],
            "tipos": data["tipos"],
            "rol": pkmn["rol"],
            "debilidades": debilidades,
            "calificacion_ivs": calificacion,
        })
        stats_equipo.append(data["stats"])
        debilidades_equipo.append(debilidades)

        logger.info(f'"{pkmn["nombre"]}" analizado — rol: {pkmn["rol"]}, calificación IVs: {calificacion}')

    promedios = calcular_promedios(stats_equipo)
    cobertura = analizar_cobertura(debilidades_equipo)

    print("\n=== RESUMEN DEL EQUIPO ===")
    for r in resultados:
        print(f'\n{r["nombre"]} ({"/".join(r["tipos"])}) — rol: {r["rol"]}')
        print(f'  Calificación de IVs: {r["calificacion_ivs"]}')
        print(f'  Debilidades: {r["debilidades"] or "ninguna"}')

    print(f"\nPromedios de stats del equipo: {promedios}")
    print(f'Huecos de cobertura (3+ miembros débiles): {cobertura["huecos_del_equipo"] or "ninguno"}')

    logger.info("=== Fin de análisis de equipo ===")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pokemitas_mvp.py <archivo_equipo.csv>")
        sys.exit(1)
    main(sys.argv[1])
