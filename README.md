> **⚠️ EDUCATIONAL USE ONLY — AUTHORIZED TESTING ONLY.**
> This project exists for education, research, and **defense of systems you own
> or hold explicit written authorization to assess**. Unauthorized use is
> prohibited and may be illegal. Read [ETHICS.md](ETHICS.md) and
> [SCOPE.md](SCOPE.md) before use. Use at your own risk; **AS IS**, no warranty.

# W9 — BLE Spoofer

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![GitHub Stars](https://img.shields.io/github/stars/5h4d0wn1k/w9-ble-spoofer)
![Last Commit](https://img.shields.io/github/last-commit/5h4d0wn1k/w9-ble-spoofer)
![GitHub Issues](https://img.shields.io/github/issues/5h4d0wn1k/w9-ble-spoofer)

> **BLE advertising spoofer in Python + ESP32-C6 firmware** — byte-exact BLE
> advertising-frame (ADV PDU) forging, CRC-24 validation, a spoofed-identity
> registry, and duplicate-identity detection for wireless security research in
> isolated labs.

## Why

Bluetooth Low Energy advertising is unauthenticated: anyone with a 2.4 GHz radio
can clone a device name and MAC, an attack used for impersonation and social
engineering. W9 lets defenders and students study that attack class safely.
The Python engine builds byte-exact `ADV_IND` PDUs (AdvA + AD structures),
computes and verifies the BLE CRC-24 (poly `0x00065B`), and maintains a
10-slot identity registry that refuses anything outside `lab-` names and the
`00:11:22` test OUI — so no real identity can be replicated. Nothing is ever
emitted over the air; the ESP32-C6 firmware is provided for authorized,
shielded-lab demonstrations of your own devices only.

## Features

- **Byte-exact ADV PDU construction** — flags, service UUIDs, complete local
  name, and appearance structures; 37-byte legacy payload rule enforced.
- **BLE CRC-24 engine** — appended and verified; corruption is rejected.
- **Identity spoof registry** — `--spoof NAME MAC` with hard `lab-`/OUI scope.
- **Duplicate detection** — same name on different AdvA (and vice versa)
  raises an `identity_spoof` alert; `--pcap` scans 802.11 captures.
- **Fixture generation** — `--gen-fixture` writes deterministic ADV fixtures.
- **JSON reporting** — `--json` writes reports to `reports/` (gitignored).

## Quickstart

```bash
# Offline: register lab-scoped identities and emit a PDU report
python3 firmware/ble_spoofer.py \
  --spoof lab-ble-fake-1 00:11:22:aa:bb:01 \
  --spoof lab-ble-fake-2 00:11:22:aa:bb:02 \
  --json reports/w9.json

# Scope guards: refuses non-lab names / non-lab OUIs
python3 firmware/ble_spoofer.py --spoof prod-fake 00:11:22:01   # ValueError

# Detect duplicate identities in an ADV pcap
python3 firmware/ble_spoofer.py --pcap lab-capture.pcap

python3 -m unittest discover -s tests
```

## ESP32-C6 firmware

```bash
arduino-cli compile --fqbn esp32:esp32:esp32c6 firmware/w9_ble_spoofer
arduino-cli upload --fqbn esp32:esp32:esp32c6 --port /dev/ttyACM0 firmware/w9_ble_spoofer
```

Serial commands: `spoof <name> <mac>`, `start <index>`, `stop`, `list`,
`clear`, `help`. The firmware mirrors the Python registry (10-slot, lab-scoped).

## Project structure

```
firmware/ble_spoofer.py   # Python engine (PDU + CRC-24 + registry + pcap)
firmware/frame_core.py    # frame-building core
firmware/w9_ble_spoofer/  # ESP32-C6 Arduino firmware
tests/                    # offline unit tests
```

## Documentation

- [ETHICS.md](ETHICS.md) — ethical-use policy, read first
- [SCOPE.md](SCOPE.md) — authorized-scope definition
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute
- [SECURITY.md](SECURITY.md) — vulnerability reporting

## Contributing

New AD structures, CRC-24 test vectors, and lab-fixture generators are welcome.
See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).