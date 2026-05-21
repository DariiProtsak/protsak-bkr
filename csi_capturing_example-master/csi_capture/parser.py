from __future__ import annotations

import ast
import csv
from dataclasses import dataclass
from typing import Optional


@dataclass
class CSIRecord:
    timestamp: int
    rssi: int
    csi: list[int]
    esp_timestamp: int
    mac: str


def parse_csi_line(line: str, timestamp: int) -> Optional[CSIRecord]:
    """Parse one ESP CSI_DATA line into a normalized record.

    `timestamp` is the host timestamp in milliseconds.
    """
    line = line.strip()
    marker = "CSI_DATA,"
    marker_idx = line.find(marker)
    if marker_idx < 0:
        return None
    line = line[marker_idx:]

    fields = next(csv.reader([line]))
    if len(fields) < 5:
        return None
    if fields[0] != "CSI_DATA":
        return None

    try:
        esp_timestamp = int(fields[1])
        mac = fields[2]
        rssi = int(fields[3])
        csi_raw = fields[-1]
        csi = ast.literal_eval(csi_raw)
    except (ValueError, SyntaxError):
        return None

    if not isinstance(csi, list) or not all(isinstance(x, int) for x in csi):
        return None

    return CSIRecord(
        timestamp=timestamp,
        rssi=rssi,
        csi=csi,
        esp_timestamp=esp_timestamp,
        mac=mac,
    )
