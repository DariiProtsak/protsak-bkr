import unittest

from csi_capture.parser import parse_csi_line


class ParseCSILineTests(unittest.TestCase):
    def test_parses_valid_line(self):
        line = 'CSI_DATA,119050,1a:00:00:00:00:00,-15,11,1,0,1,1,1,0,0,0,0,-97,0,11,2,131691810,0,47,0,384,0,"[1,-2,3,-4]"'
        record = parse_csi_line(line, timestamp=1700000000000)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.timestamp, 1700000000000)
        self.assertEqual(record.rssi, -15)
        self.assertEqual(record.csi, [1, -2, 3, -4])
        self.assertEqual(record.esp_timestamp, 119050)
        self.assertEqual(record.mac, "1a:00:00:00:00:00")

    def test_ignores_non_csi_line(self):
        self.assertIsNone(parse_csi_line("I (10) csi_recv: hello", timestamp=1))

    def test_parses_csi_with_prefix_garbage(self):
        line = 'garbage-prefix CSI_DATA,119050,1a:00:00:00:00:00,-15,11,1,0,1,1,1,0,0,0,0,-97,0,11,2,131691810,0,47,0,384,0,"[1,-2,3,-4]"'
        record = parse_csi_line(line, timestamp=1)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.rssi, -15)
        self.assertEqual(record.csi, [1, -2, 3, -4])

    def test_rejects_bad_csi_payload(self):
        bad = 'CSI_DATA,1,aa:bb:cc:dd:ee:ff,-20,11,"not-a-list"'
        self.assertIsNone(parse_csi_line(bad, timestamp=1))


if __name__ == "__main__":
    unittest.main()
