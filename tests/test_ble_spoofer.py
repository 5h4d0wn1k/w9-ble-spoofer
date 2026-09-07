#!/usr/bin/env python3
"""Byte-exact unit tests for w9-ble-spoofer."""

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from firmware import ble_spoofer as bs


class Crc24Test(unittest.TestCase):
    def test_crc_deterministic(self):
        pdu = b"\x00\x06" + bytes.fromhex("00 11 22 aa bb 01")
        self.assertEqual(bs.ble_crc24(pdu), bs.ble_crc24(pdu))

    def test_crc_detects_change(self):
        pdu = b"\x00\x06" + bytes.fromhex("00 11 22 aa bb 01")
        changed = pdu[:-1] + bytes([pdu[-1] ^ 0x01])
        self.assertNotEqual(bs.ble_crc24(pdu), bs.ble_crc24(changed))


class PduTest(unittest.TestCase):
    def test_build_parse_roundtrip(self):
        pdu = bs.build_adv_pdu("00:11:22:aa:bb:01", "lab-ble-fake-1")
        p = bs.parse_adv_pdu(pdu)
        self.assertEqual(p["adva"], "00:11:22:aa:bb:01")
        self.assertEqual(p["name"], "lab-ble-fake-1")
        self.assertEqual(p["adv_type"], bs.ADV_IND)

    def test_crc_corruption_rejected(self):
        pdu = bytearray(bs.build_adv_pdu("00:11:22:aa:bb:01", "lab-x"))
        pdu[-1] ^= 0xFF
        with self.assertRaises(ValueError):
            bs.parse_adv_pdu(bytes(pdu))

    def test_legacy_pdu_le_37_payload(self):
        pdu = bs.build_adv_pdu("00:11:22:aa:bb:01", "lab-ble-fake-1", service_uuids=(0x1800,))
        self.assertLessEqual(pdu[1], 37)

    def test_name_from_ad(self):
        pdu = bs.build_adv_pdu("00:11:22:aa:bb:02", "lab-sensor")
        p = bs.parse_adv_pdu(pdu)
        self.assertEqual(p["name"], "lab-sensor")


class RegistryTest(unittest.TestCase):
    def test_add_enforces_lab_scope(self):
        r = bs.SpoofRegistry()
        with self.assertRaises(ValueError):
            r.add("real-hacker", "00:11:22:aa:bb:01")
        with self.assertRaises(ValueError):
            r.add("lab-ok", "aa:bb:cc:dd:ee:ff")
        idx = r.add("lab-ok-device", "00:11:22:aa:bb:03")
        self.assertEqual(idx, 0)
        self.assertFalse(r.devices[0]["active"])

    def test_activate_and_pdu(self):
        r = bs.SpoofRegistry()
        idx = r.add("lab-ok-device", "00:11:22:aa:bb:03")
        r.activate(idx)
        self.assertTrue(r.devices[idx]["active"])
        p = bs.parse_adv_pdu(r.pdu_for(idx))
        self.assertEqual(p["name"], "lab-ok-device")


class DuplicateDetectTest(unittest.TestCase):
    def test_same_name_two_macs_flagged(self):
        pdus = [bs.build_adv_pdu("00:11:22:aa:bb:01", "lab-lock"),
                bs.build_adv_pdu("00:11:22:aa:bb:02", "lab-lock")]
        det = bs.detect_duplicates(pdus)
        self.assertTrue(any(a["type"] == "identity_spoof" for a in det["alerts"]))
        self.assertEqual(det["pdus_valid"], 2)

    def test_unique_identities_clean(self):
        pdus = [bs.build_adv_pdu("00:11:22:aa:bb:01", "lab-a"),
                bs.build_adv_pdu("00:11:22:aa:bb:02", "lab-b")]
        det = bs.detect_duplicates(pdus)
        self.assertEqual(det["alerts"], [])


class FixtureTest(unittest.TestCase):
    def test_fixture_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "adv.pcap")
            pdus = [bs.build_adv_pdu("00:11:22:aa:bb:01", "lab-a")]
            n = bs.write_fixture(path, pdus)
            self.assertEqual(n, 1)
            back = bs.read_fixture(path)
            self.assertEqual(bs.parse_adv_pdu(back[0])["name"], "lab-a")


class CLITest(unittest.TestCase):
    def test_demo_exit_zero(self):
        self.assertEqual(bs.run_demo(), 0)

    def test_json_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "o.json")
            rc = bs.main(["--spoof", "lab-ble-fake-1", "00:11:22:aa:bb:01",
                          "--spoof", "lab-ble-fake-2", "00:11:22:aa:bb:02",
                          "--json", out])
            self.assertEqual(rc, 0)
            data = json.load(open(out))
            self.assertFalse(data["radio_emitted"])
            self.assertEqual(len(data["devices"]), 2)


if __name__ == "__main__":
    unittest.main()