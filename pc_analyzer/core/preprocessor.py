import math
import base64

N_SUBCARRIERS = 114  # nominal (HT40 40 MHz); iPhone HT20 yields 57 — accepted automatically


def extract_amplitudes(packet: dict) -> list[float] | None:
    """Return per-subcarrier amplitude list.

    Supports three CSI formats:
      1. Flat int array  [im0,re0,im1,re1,...] — current firmware & supervisor format
      2. Base64 string   — legacy firmware (v2.3)
      3. List of pairs   [[re0,im0],[re1,im1],...] — oldest legacy format
    """
    csi = packet.get("csi")
    if csi is None:
        return None

    # ── Format 1: flat JSON int array [im0, re0, im1, re1, ...] ─────────────────
    if isinstance(csi, list):
        if len(csi) < 4:
            return None
        if isinstance(csi[0], (int, float)):
            n = (len(csi) // 2) * 2   # round down to even
            if n < 4:
                return None
            try:
                return [math.sqrt(float(csi[i]) ** 2 + float(csi[i + 1]) ** 2)
                        for i in range(0, n, 2)]
            except Exception:
                return None
        else:
            # List of [re, im] pairs
            try:
                return [math.sqrt(float(r) ** 2 + float(im) ** 2) for r, im in csi]
            except Exception:
                return None

    # ── Format 2: base64-encoded raw bytes (im, re interleaved int8) ─────────────
    if isinstance(csi, str):
        try:
            data = base64.b64decode(csi)
        except Exception:
            return None
        n = len(data) // 2
        if n < 4 or len(data) % 2 != 0:
            return None
        amps = []
        for k in range(n):
            im_u = data[2 * k];     im = im_u - 256 if im_u > 127 else im_u
            re_u = data[2 * k + 1]; re = re_u - 256 if re_u > 127 else re_u
            amps.append(math.sqrt(re * re + im * im))
        return amps

    return None
