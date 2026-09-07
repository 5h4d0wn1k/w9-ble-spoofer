# W9 — BLE Spoofer

Clone BLE device identities and broadcast fake advertisements.

## Overview

This project implements a BLE spoofing attack that:
- Clones any BLE device's MAC address
- Broadcasts fake BLE advertisements
- Spoofs device names and services
- Tracks nearby BLE devices

**WARNING: Educational use only. Test on your own devices.**

## Hardware

| Component | Connection | Role |
|-----------|------------|------|
| ESP32-C6 | Main board | BLE radio + spoofing |

## Serial Commands

```
spoof <name> <mac> - Add spoofed device
start <index>      - Start advertising as device
stop               - Stop advertising
list               - List spoofed devices
clear              - Clear all devices
help               - Show commands
```

## Example Session

```
=== W9 — BLE Spoofer ===
BLE initialized

spoof AirPods aa:bb:cc:dd:ee:ff
Added spoofed device: AirPods (aa:bb:cc:dd:ee:ff)

spoof iPhone 11:22:33:44:55:66
Added spoofed device: iPhone (11:22:33:44:55:66)

list
=== Spoofed Devices ===
[0] AirPods (AA:BB:CC:DD:EE:FF) INACTIVE
[1] iPhone (11:22:33:44:55:66) INACTIVE

start 0
Starting advertising as: AirPods
Advertising started!
```

## Build & Flash

```bash
arduino-cli compile --fqbn esp32:esp32:esp32c6 w9_ble_spoofer
arduino-cli upload --fqbn esp32:esp32:esp32c6 --port /dev/ttyACM0 w9_ble_spoofer
```

## Legal Disclaimer

**IMPORTANT: Read before use.**

This project is provided for **educational and authorized security testing purposes only**. 

### Authorization Requirements
- You MUST have explicit written permission from the device owner before using this tool
- Unauthorized impersonation of BLE devices is illegal in many jurisdictions
- This tool should ONLY be used on devices you own or have written authorization to test

### Legal Framework
- **Computer Fraud and Abuse Act (CFAA)**: Unauthorized access to computer systems is a federal crime
- **Wireless Communication Laws**: Impersonating wireless devices may violate FCC regulations
- **State Laws**: Many states have additional computer crime and impersonation statutes
- **GDPR/CCPA**: Data collection may be subject to privacy regulations

### Acceptable Use
- Testing security of your own devices
- Authorized penetration testing with written scope
- Academic research in controlled lab environments
- Security education and training

### Prohibited Use
- Impersonating devices you do not own
- Advertising a spoofed identity in the presence of third parties
- Attacking infrastructure without authorization
- Any activity that violates applicable laws or regulations — the Python engine emits no radio
- Commercial use without proper licensing

### Regulatory Framework
- **Federal Communications Act (47 U.S.C. § 333)**: Willful interference with authorized radio communications is prohibited.
- **47 CFR Part 15**: Unauthorized intentional radiators (a cloned/bluetooth identity transmitter) are regulated; this repo is byte-level simulation only.
- **CFAA (18 U.S.C. § 1030) / state computer-crime laws**: Impersonating another device and spoofing advertisements to trick users or owners is illegal without authorization.
- Sending real advertisements as a cloned identity requires written scope over the target device and frequency band, in an RF-shielded lab, using authorized test hardware.

## Live Lab Test Plan

Offline (this repo, no radio):
1. Register spoofed (lab-scoped) identities:
   `python3 firmware/ble_spoofer.py --spoof lab-ble-fake-1 00:11:22:aa:bb:01 --spoof lab-ble-fake-2 00:11:22:aa:bb:02 --json reports/w9.json`
   — two ADV PDUs built + CRC-24 verified, exit 0, `radio_emitted=false`.
2. Scope guards: `--spoof prod-fake 00:11:22:01` or `--spoof lab-x aa:bb:cc:dd:ee:ff`
   -> ValueError (no radio transmitted); registry refuses non-`lab-` names/non-lab OUIs.
3. Duplicate detector: generate two PDUs with the same name, different AdvA ->
   `identity_spoof` alert raised (the eye that would catch this threat).
4. `python3 -m unittest discover -s tests` — PDU roundtrip, CRC-24 corruption,
   fixture roundtrip, detector, registry scope (exit 0).

Authorized lab (simulation of YOUR OWN BLE sensor only):
5. Clone your own device's name + label in a shielded enclosure; verify ADV PDU bytes
   match a sniffer capture and that no third-party device sees a transmission.
6. `green = permitted`: byte-level PDU construction, registry, duplicate detection.

## Metrics

- BLE advertising PDU (byte-exact): ADV_IND, AdvA (6B) + AD structures (flags 0x1A,
  service UUID list, complete local name, appearance)
- BLE CRC-24: poly 0x00065B, init 0x555555, appended 3 bytes; corruption rejected
- Legacy payload constrained to the 37-byte rule; noncompliance raises ValueError
- Spoof registry: `lab-` names + `00:11:22` OUI enforced (10-slot, mirrors the sketch)
- Identity detection: same name across != AdvA or same AdvA across != names flagged
- Offline: no radio, no real MACs, no wall-clock-dependent frame data
- pcap linktype 105 (802.11) transport only for fixture replay; bytes are the realism

- Test suite: `python3 -m unittest discover -s tests`
- Reports: `reports/` (gitignored)
- Associated firmware: `firmware/w9_ble_spoofer/w9_ble_spoofer.ino` (ESP32-C6)

## License

MIT
