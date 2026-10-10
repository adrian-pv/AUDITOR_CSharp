"""Guarda el reporte agregado del motor como el JSON que consume el frontend."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def write_report(reporte: dict, destino: Path, auditor: str = "Luis Adrián Pivaral Quiroa") -> Path:
    reporte_final = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "auditor": auditor,
        **reporte,
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(reporte_final, fh, indent=2, ensure_ascii=False)
    return destino
