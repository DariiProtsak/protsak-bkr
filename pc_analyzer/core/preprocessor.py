import math

NUM_SUBCARRIERS = 114

def extract_amplitudes(packet: dict) -> list[float] | None:
    csi = packet.get("csi")
    if not csi or len(csi) != NUM_SUBCARRIERS:
        return None
    return [math.sqrt(r ** 2 + i ** 2) for r, i in csi]
