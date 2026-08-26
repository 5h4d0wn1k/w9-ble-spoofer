/*
 * W9 — BLE Spoofer
 * Clone BLE device identities and broadcast fake advertisements
 * 
 * Hardware: ESP32-C6
 * 
 * Features:
 *   - Clone any BLE device's MAC address
 *   - Broadcast fake BLE advertisements
 *   - Spoof device names and services
 *   - Track nearby BLE devices
 * 
 * WARNING: Educational use only. Test on your own devices.
 * 
 * Author: 5h4d0wn1k
 * License: MIT
 * Date: 2026-08-26
 */

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Configuration
#define DEVICE_NAME "H9-BLE-Spoofer"
#define ADV_INTERVAL 100  // ms

// Spoofed device structure
struct SpoofedDevice {
    char name[32];
    uint8_t mac[6];
    uint32_t appearance;
    bool active;
};

// Global state
BLEServer* pServer = nullptr;
BLEService* pService = nullptr;
bool deviceConnected = false;
SpoofedDevice spoofed_devices[10];
int spoof_count = 0;
bool advertising = false;

// Callback for server events
class ServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
        Serial.println("Client connected!");
    }
    
    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
        Serial.println("Client disconnected.");
    }
};

// Function prototypes
void startAdvertising(const char* name, uint8_t* mac);
void stopAdvertising();
void listSpoofed();
void showHelp();
void processSerialCommand();

void setup() {
    Serial.begin(115200);
    Serial.println("\n=== W9 — BLE Spoofer ===");
    Serial.println("Clone BLE device identities");
    Serial.println("WARNING: Educational use only!");
    Serial.println();
    
    // Initialize BLE
    BLEDevice::init(DEVICE_NAME);
    
    // Create server
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new ServerCallbacks());
    
    // Create service
    pService = pServer->createService("1800");  // Generic Access
    
    // Add device name characteristic
    BLECharacteristic* nameChar = pService->createCharacteristic(
        "2A00",  // Device Name
        BLECharacteristic::PROPERTY_READ
    );
    nameChar->setValue(DEVICE_NAME);
    
    // Add appearance characteristic
    BLECharacteristic* appearChar = pService->createCharacteristic(
        "2A01",  // Appearance
        BLECharacteristic::PROPERTY_READ
    );
    appearChar->setValue((uint8_t*)"\x00\x00", 2);
    
    // Start service
    pService->start();
    
    Serial.println("BLE initialized");
    Serial.println();
    showHelp();
}

void loop() {
    // Handle serial commands
    if (Serial.available()) {
        processSerialCommand();
    }
    
    delay(100);
}

void processSerialCommand() {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd == "help") {
        showHelp();
    } else if (cmd.startsWith("spoof ")) {
        // spoof <name> <mac:mac:mac:mac:mac:mac>
        int space = cmd.indexOf(' ', 6);
        if (space > 0) {
            String name = cmd.substring(6, space);
            String macStr = cmd.substring(space + 1);
            
            // Parse MAC
            uint8_t mac[6];
            sscanf(macStr.c_str(), "%02x:%02x:%02x:%02x:%02x:%02x",
                   &mac[0], &mac[1], &mac[2], &mac[3], &mac[4], &mac[5]);
            
            // Store spoofed device
            if (spoof_count < 10) {
                strncpy(spoofed_devices[spoof_count].name, name.c_str(), 31);
                memcpy(spoofed_devices[spoof_count].mac, mac, 6);
                spoofed_devices[spoof_count].active = false;
                spoof_count++;
                
                Serial.printf("Added spoofed device: %s (%s)\n", 
                             name.c_str(), macStr.c_str());
            }
        } else {
            Serial.println("Usage: spoof <name> <mac:mac:mac:mac:mac:mac>");
        }
    } else if (cmd.startsWith("start ")) {
        // start <index>
        int idx = cmd.substring(6).toInt();
        if (idx >= 0 && idx < spoof_count) {
            startAdvertising(spoofed_devices[idx].name, spoofed_devices[idx].mac);
            spoofed_devices[idx].active = true;
        } else {
            Serial.println("Invalid index!");
        }
    } else if (cmd == "stop") {
        stopAdvertising();
    } else if (cmd == "list") {
        listSpoofed();
    } else if (cmd == "clear") {
        spoof_count = 0;
        Serial.println("Cleared all spoofed devices.");
    } else {
        Serial.println("Unknown command. Type 'help' for commands.");
    }
}

void showHelp() {
    Serial.println("\n=== Commands ===");
    Serial.println("spoof <name> <mac> - Add spoofed device");
    Serial.println("start <index>      - Start advertising as device");
    Serial.println("stop               - Stop advertising");
    Serial.println("list               - List spoofed devices");
    Serial.println("clear              - Clear all devices");
    Serial.println("help               - Show this help");
    Serial.println("================\n");
}

void startAdvertising(const char* name, uint8_t* mac) {
    Serial.printf("\nStarting advertising as: %s\n", name);
    
    // Stop current advertising
    BLEDevice::getAdvertising()->stop();
    
    // Set custom MAC
    esp_base_mac_addr_set(mac);
    
    // Update device name
    BLEDevice::setName(name);
    
    // Start advertising
    BLEAdvertising* pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID("1800");
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);
    pAdvertising->setMinPreferred(0x12);
    pAdvertising->start();
    
    advertising = true;
    
    Serial.println("Advertising started!");
    Serial.printf("MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                 mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

void stopAdvertising() {
    BLEDevice::getAdvertising()->stop();
    advertising = false;
    Serial.println("Advertising stopped.");
}

void listSpoofed() {
    if (spoof_count == 0) {
        Serial.println("No spoofed devices configured.");
        return;
    }
    
    Serial.println("\n=== Spoofed Devices ===");
    for (int i = 0; i < spoof_count; i++) {
        Serial.printf("[%d] %s (%02X:%02X:%02X:%02X:%02X:%02X) %s\n",
                     i, spoofed_devices[i].name,
                     spoofed_devices[i].mac[0], spoofed_devices[i].mac[1],
                     spoofed_devices[i].mac[2], spoofed_devices[i].mac[3],
                     spoofed_devices[i].mac[4], spoofed_devices[i].mac[5],
                     spoofed_devices[i].active ? "ACTIVE" : "INACTIVE");
    }
    Serial.println("======================\n");
}
