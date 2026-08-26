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
- Attacking infrastructure without authorization
- Any activity that violates applicable laws or regulations
- Commercial use without proper licensing

### No Warranty
This software is provided "AS IS" without warranty of any kind. The author is not responsible for any misuse or damage caused by this software.

### Responsible Disclosure
If you discover vulnerabilities using this tool, follow responsible disclosure practices:
1. Report to the vendor/owner privately
2. Allow reasonable time for remediation
3. Do not exploit beyond proof of concept

## License

MIT
