import unittest

from csi_capture.experiments import get_experiment, iter_experiments


class ExperimentRegistryTests(unittest.TestCase):
    def test_registry_exposes_expected_plugins(self):
        experiment_ids = [plugin.definition.experiment_id for plugin in iter_experiments()]
        self.assertIn("distance", experiment_ids)
        self.assertIn("angle", experiment_ids)
        self.assertIn("static_sign_v1", experiment_ids)
        self.assertIn("presence_v1", experiment_ids)

    def test_static_sign_plugin_capabilities(self):
        plugin = get_experiment("static_sign_v1")
        self.assertTrue(plugin.supports("capture"))
        self.assertTrue(plugin.supports("train"))
        self.assertTrue(plugin.supports("eval"))
        self.assertTrue(plugin.supports("validate-config"))
        self.assertFalse(plugin.supports("report"))

    def test_presence_plugin_is_future_ready_validate_only_shape(self):
        plugin = get_experiment("presence_v1")
        self.assertFalse(plugin.supports("capture"))
        self.assertTrue(plugin.supports("validate-config"))
        self.assertEqual(plugin.definition.task_type, "detection")


if __name__ == "__main__":
    unittest.main()
