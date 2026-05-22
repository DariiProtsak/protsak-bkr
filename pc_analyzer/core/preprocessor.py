import math

def extract_amplitudes(packet: dict) -> list[float] | None:
    csi = packet.get("csi")
    if not csi or len(csi) < 2:
        return None
    return [math.sqrt(r ** 2 + i ** 2) for r, i in csi]
