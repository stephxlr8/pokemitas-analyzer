# Pokemitas Analyzer

<img width="728" height="410" alt="image" src="https://github.com/user-attachments/assets/32835c64-0b4f-489c-aed1-ed437b822c7b" />



'Versión mínima funcional'

## Archivos
- `logger_config.py` — configura el logger, crea `/logs/app.log` automáticamente.
- `type_chart.py` — tabla de efectividad de tipos (18x18).
- `pokemitas_mvp.py` — lógica principal: lee equipo, consulta PokéAPI + cache, calcula debilidades, evalúa IVs, promedios y cobertura.
- `equipo_ejemplo.csv` — equipo de prueba (incluye a propósito un rol inválido y un IV fuera de rango, para que veas los WARNING en acción).
- `cache/` — se llena solo con las respuestas de PokéAPI (JSON por Pokémon).
- `logs/app.log` — ya incluye una corrida de ejemplo con INFO, WARNING y ERROR reales.

## Cómo correrlo
```bash
pip install requests
python pokemitas_mvp.py equipo_ejemplo.csv
```

Cada corrida agrega líneas nuevas a `logs/app.log` (no lo borra).

## Note for logs
Mis logs registran cargas de equipo, hits/misses del cache local de PokéAPI y errores de conexión o de IVs fuera de rango, para poder diagnosticar rápido si el análisis de un equipo falla o da resultados inconsistentes.


## Siguiente paso
Esto es la lógica "cerebro" del proyecto — todavía falta la GUI. Cuando la
tengas, solo importa `from logger_config import logger` en ese archivo también
y loggea las acciones del usuario (botones, exportar, etc.).

