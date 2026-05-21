import unittest

from csi_capture.core.environment import (
    DEFAULT_ENVIRONMENT_PROFILE_ID,
    EnvironmentProfileError,
    list_environment_profiles,
    resolve_environment_profile,
)


class EnvironmentProfileTests(unittest.TestCase):
    def test_default_profile_resolves(self):
        profile = resolve_environment_profile(None)
        self.assertEqual(profile.profile_id, DEFAULT_ENVIRONMENT_PROFILE_ID)
        self.assertTrue(profile.default_serial_device.startswith("/dev/"))

    def test_unknown_profile_raises(self):
        with self.assertRaises(EnvironmentProfileError):
            resolve_environment_profile("unknown_profile")

    def test_registry_contains_default_profile(self):
        profile_ids = [item.profile_id for item in list_environment_profiles()]
        self.assertIn(DEFAULT_ENVIRONMENT_PROFILE_ID, profile_ids)


if __name__ == "__main__":
    unittest.main()
