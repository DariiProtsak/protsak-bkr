from __future__ import annotations

from dataclasses import dataclass


class EnvironmentProfileError(ValueError):
    """Raised when an environment profile is invalid or unknown."""


@dataclass(frozen=True)
class EnvironmentProfile:
    profile_id: str
    display_name: str
    board: str
    chip: str
    esp_idf_version: str
    esp_csi_branch: str
    tx_firmware: str
    rx_firmware: str
    default_serial_device: str
    default_baud: int
    wifi_band: str
    notes: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "board": self.board,
            "chip": self.chip,
            "esp_idf_version": self.esp_idf_version,
            "esp_csi_branch": self.esp_csi_branch,
            "tx_firmware": self.tx_firmware,
            "rx_firmware": self.rx_firmware,
            "default_serial_device": self.default_serial_device,
            "default_baud": self.default_baud,
            "wifi_band": self.wifi_band,
            "notes": self.notes,
        }


DEFAULT_ENVIRONMENT_PROFILE_ID = "esp32s3_csi_v1"


_ENVIRONMENT_PROFILES: dict[str, EnvironmentProfile] = {
    DEFAULT_ENVIRONMENT_PROFILE_ID: EnvironmentProfile(
        profile_id=DEFAULT_ENVIRONMENT_PROFILE_ID,
        display_name="ESP32-S3 CSI Baseline v1",
        board="esp32-s3-devkitc-1",
        chip="esp32s3",
        esp_idf_version="v5.5.3",
        esp_csi_branch="main",
        tx_firmware="esp-csi/examples/get-started/csi_send",
        rx_firmware="esp-csi/examples/get-started/csi_recv",
        default_serial_device="/dev/esp32_csi",
        default_baud=921600,
        wifi_band="2.4GHz",
        notes="Primary target for current RSSI/CSI capture workflows.",
    ),
}


def list_environment_profiles() -> list[EnvironmentProfile]:
    return [_ENVIRONMENT_PROFILES[key] for key in sorted(_ENVIRONMENT_PROFILES)]


def resolve_environment_profile(profile_id: str | None) -> EnvironmentProfile:
    requested = (profile_id or DEFAULT_ENVIRONMENT_PROFILE_ID).strip()
    if not requested:
        requested = DEFAULT_ENVIRONMENT_PROFILE_ID
    profile = _ENVIRONMENT_PROFILES.get(requested)
    if profile is None:
        raise EnvironmentProfileError(
            f"unknown target profile '{requested}'. Available: {', '.join(sorted(_ENVIRONMENT_PROFILES))}"
        )
    return profile


def format_environment_banner(profile: EnvironmentProfile) -> str:
    return (
        f"Target profile: {profile.profile_id} ({profile.display_name})\n"
        f"Board/chip: {profile.board} / {profile.chip}\n"
        f"ESP-IDF: {profile.esp_idf_version} | esp-csi: {profile.esp_csi_branch}\n"
        f"Firmware: TX={profile.tx_firmware}, RX={profile.rx_firmware}\n"
        f"Serial default: {profile.default_serial_device} @ {profile.default_baud}"
    )
