#!/usr/bin/env python3
"""W9 — BLE Spoofer (offscreen identity clone + duplicate detector).

Byte-exact BLE advertising-PDU builder mirroring the ESP32-C6 sketch flow:

  * spoof <name> <mac> — register a fake identity (lab OUI + `lab-` name only)
  * start <idx>        — build the ADV_IND PDU bytes for that identity
  * byte model: PDU header (adv-type + len) | AdvA (6B) | AD structures
    (flags, 16-bit service UUIDs, complete local name, tx power, appearance)
    | BLE CRC-24 (poly 0x00065B, init 0x555555)
  * duplicate-identity detector: same name across != AdvA (or same AdvA across
    != names) is flagged as spoof/collision

Pure-stdlib bytes; nothing is broadcast. Defensive pairing: the detector is
the eye that would catch the spoofed advertisements.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys

try:
    from firmware import frame_core as fc
except ImportError:
    try:
        import frame_core as fc
    except ImportError:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "firmware"))
        import frame_core as fc

# cached access-address / preamble omitted: we model the PDU + CRC24, which is
# the identity-relevant content; on-air framing (preamble/access-address) is
# the radio layer's job and is not needed for detection.
ADV_IND = 0x00          # connectable, scannable advertising
ADV_NONCONN_IND = 0x03  # non-connectable advertising
START_TS = 1700000000.0


def ble_crc24(pdu: bytes, poly: int = 0x00065B, init: int = 0x555555) -> int:
    """BLE CRC-24 (MSB-first, poly 0x00065B, init 0x555555)."""
    crc = init
    for byte in pdu:
        crc ^= byte << 16
        for _ in range(8):
            crc = ((crc << 1) ^ poly) & 0xFFFFFF if crc & 0x800000 else (crc << 1) & 0xFFFFFF
    return crc


def ad(type_, data: bytes) -> bytes:
    return bytes([len(data) + 1, type_]) + data


def mac_bytes_valid(mac: str) -> bool:
    if len(mac) != 17:
        return False
    try:
        parts = mac.split(":")
        return len(parts) == 6 and all(len(p) == 2 and 0 <= int(p, 16) <= 255 for p in parts)
    except ValueError:
        return False


def is_lab_mac(mac: str) -> bool:
    return mac.startswith("00:11:22")


# ----------------------------------------------------------------------
# Advertising PDU builder / parser (byte-exact)
# ----------------------------------------------------------------------

def build_adv_pdu(addr: str, name: str, service_uuids: tuple = (0x1800, 0x180F),
                  appearance: int = 0x0041, flags: int = 0x1A,
                  adv_type: int = ADV_IND) -> bytes:
    """Full ADV PDU + CRC24. addr is the advertised (spoofed) AdvA."""
    adva = bytes.fromhex(addr.replace(":", ""))
    pld = adva
    pld += ad(0x01, bytes([flags]))
    uuid_bytes = b"".join(struct.pack("<H", u) for u in service_uuids)
    pld += ad(0x03, uuid_bytes)
    pld += ad(0x09, name.encode())
    pld += ad(0x19, struct.pack("<H", appearance))
    if len(pld) > 37:
        raise ValueError("legacy advertising PDU payload exceeds 37 bytes")
    hdr = bytes([adv_type, len(pld)])
    pdu = hdr + pld
    return pdu + ble_crc24(pdu).to_bytes(3, "big")


def parse_adv_pdu(pdu: bytes) -> dict:
    if len(pdu) < 2 + 6 + 3:
        raise ValueError("truncated PDU")
    if ble_crc24(pdu[:-3]) != int.from_bytes(pdu[-3:], "big"):
        raise ValueError("bad BLE CRC-24")
    adv_type = pdu[0] & 0x0F
    length = pdu[1]
    if length != len(pdu) - 2 - 3:
        raise ValueError("length mismatch")
    adva = ":".join(f"{b:02x}" for b in pdu[2:8])
    ads = []
    i = 8
    end = 2 + length
    while i + 1 < end:
        alen = pdu[i]              # BLE AD len field covers type + data
        atype = pdu[i + 1]
        data = pdu[i + 2:i + 1 + alen]
        ads.append({"type": atype, "data": data.hex()})
        i += 1 + alen
    name = ""
    for a in ads:
        if a["type"] == 0x09:
            name = bytes.fromhex(a["data"]).decode(errors="replace")
    return {"adv_type": adv_type, "adva": adva, "name": name, "ads": ads}


# ----------------------------------------------------------------------
# Spoof registry (mirrors the sketch commands) + detection
# ----------------------------------------------------------------------

class SpoofRegistry:
    MAX = 10

    def __init__(self):
        self.devices: list[dict] = []

    def add(self, name: str, mac: str) -> int:
        if len(self.devices) >= self.MAX:
            raise ValueError("registry full")
        if not name.startswith("lab-"):
            raise ValueError("spoof names must start with lab- (lab simulation only)")
        if not mac_bytes_valid(mac) or not is_lab_mac(mac):
            raise ValueError("spoof MAC must be a valid 00:11:22 lab OUI")
        self.devices.append({"name": name, "mac": mac, "active": False})
        return len(self.devices) - 1

    def activate(self, idx: int) -> dict:
        dev = self.devices[idx]
        dev["active"] = True
        return dev

    def pdu_for(self, idx: int) -> bytes:
        dev = self.devices[idx]
        return build_adv_pdu(dev["mac"], dev["name"])


def detect_duplicates(pdus: list[bytes]) -> dict:
    by_name = {}
    by_adva = {}
    for pdu in pdus:
        try:
            p = parse_adv_pdu(pdu)
        except ValueError:
            continue
        if p["name"]:
            by_name.setdefault(p["name"], set()).add(p["adva"])
        by_adva.setdefault(p["adva"], set()).add(p["name"])
    alerts = []
    for name, addrset in by_name.items():
        if len(addrset) > 1:
            alerts.append({"type": "identity_spoof", "detail": "name across multiple AdvA",
                           "name": name, "advas": sorted(addrset), "severity": "high"})
    for adva, names in by_adva.items():
        if len(names) > 1:
            alerts.append({"type": "identity_spoof", "detail": "AdvA across multiple names",
                           "adva": adva, "names": sorted(names), "severity": "high"})
    return {"pdus_valid": sum(1 for p in pdus if _valid(p)), "alerts": alerts}


def _valid(pdu: bytes) -> bool:
    try:
        parse_adv_pdu(pdu)
        return True
    except ValueError:
        return False


def write_fixture(path: str, identity_pdus: list[bytes]) -> int:
    fc.write_pcap(path, identity_pdus, ts=START_TS)
    return len(identity_pdus)


def read_fixture(path: str) -> list[bytes]:
    return [r["data"] for r in fc.read_pcap(path)]


# ----------------------------------------------------------------------
# CLI / demo
# ----------------------------------------------------------------------

def build_args_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="w9-ble-spoofer",
        description="BLE spoofer lab engine: byte-exact ADV PDU builder (spoofed lab-OUI "
                    "identities), spoof registry + duplicate-identity detector. "
                    "Pure-stdlib bytes; nothing is broadcast.")
    p.add_argument("--spoof", nargs=2, metavar=("NAME", "MAC"), action="append",
                   help="register lab identity (name lab-*, MAC 00:11:22:*)")
    p.add_argument("--start", type=int, metavar="IDX", help="build ADV PDU for registry index")
    p.add_argument("--pcap", metavar="PATH", help="detect duplicates in an ADV pcap")
    p.add_argument("--gen-fixture", metavar="PATH", help="write ADV fixture for registered ids")
    p.add_argument("--json", metavar="PATH", help="write JSON report")
    return p


def print_report(registry: SpoofRegistry, pdus: list[bytes], det: dict) -> None:
    print("=" * 62)
    print(" W9 — BLE Spoofer (offscreen identity clone + detector)")
    print("=" * 62)
    print("\n--- spoof registry ---")
    for i, d in enumerate(registry.devices):
        print(f"  [{i}] {d['name']} ({d['mac']}) {'ACTIVE' if d['active'] else 'inactive'}")
    print(f"\n[+] ADV PDUs built: {len(pdus)}  crc-valid: {det['pdus_valid']}  "
          f"radio_emitted=False")
    for a in det["alerts"]:
        print(f"  [{a['severity'].upper()}] {a['type']}  {a['detail']}  "
              f"name={a.get('name', a.get('adva', ''))}")
    if not det["alerts"]:
        print("  (no duplicate identities)")
    print("[+] identity bytes only — no advertisement was broadcast.")
    print("=" * 62)


def main(argv=None) -> int:
    args = build_args_parser().parse_args(argv)
    registry = SpoofRegistry()
    for name, mac in args.spoof or []:
        idx = registry.add(name, mac)
        registry.activate(idx)
        print(f"[+] spoofed identity {idx}: {name} ({mac})")
    if args.start is not None and (args.spoof or args.start < len(registry.devices)):
        if not registry.devices:
            raise SystemExit("no spoofed identities registered; pass --spoof first")
        idx = args.start if args.start < len(registry.devices) else 0
        registry.activate(idx)
        print(f"[+] ADV PDU built for [{idx}] {registry.devices[idx]['name']} "
              f"(crc-24 appended)")
    if args.gen_fixture:
        if not registry.devices:
            raise SystemExit("no spoofed identities registered; pass --spoof first")
        pdus = [registry.pdu_for(i) for i in range(len(registry.devices))]
        write_fixture(args.gen_fixture, pdus)
        print(f"\n[+] fixture -> {args.gen_fixture} ({len(pdus)} ADV PDUs)")
    if args.pcap:
        det = detect_duplicates(read_fixture(args.pcap))
    else:
        pdus = [registry.pdu_for(i) for i in range(len(registry.devices))]
        det = detect_duplicates(pdus)
    print_report(registry, pdus if not args.pcap else [], det)
    if args.json:
        d = os.path.dirname(args.json)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump({"name": "w9-ble-spoofer", "radio_emitted": False,
                       "devices": registry.devices,
                       "pdus": [{"name": d["name"], "adva": d["adva"],
                                 "crc24_ok": True}
                                for d in (parse_adv_pdu(registry.pdu_for(i))
                                          for i in range(len(registry.devices)))]
                       if not args.pcap else [],
                       "detection": det}, f, indent=2, default=str)
    return 0


def run_demo() -> int:
    return main(["--spoof", "lab-ble-fake-1", "00:11:22:aa:bb:01",
                 "--spoof", "lab-ble-fake-2", "00:11:22:aa:bb:02"])


if __name__ == "__main__":
    raise SystemExit(main())