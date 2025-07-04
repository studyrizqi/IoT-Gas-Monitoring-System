// Gas Monitoring System with Dual Control
// MQ Sensor + LED + Buzzer + Serial Communication
// Features: Auto trigger, Manual override, Acknowledgment system

const int MQ_PIN = A0;          // MQ sensor analog pin
const int LED_PIN = 13;         // LED pin
const int BUZZER_PIN = 12;      // Buzzer pin

// Threshold dan state variables
int gasThreshold = 400;         // Default threshold, adjustable via serial
bool manualLedState = false;    // Manual LED override
bool manualBuzzerState = false; // Manual buzzer override
bool autoMode = true;           // Auto trigger mode
bool alarmAcknowledged = false; // Alarm acknowledgment state

// Timing variables
unsigned long lastReading = 0;
const unsigned long readingInterval = 1000; // Read sensor every 1 second

void setup() {
  Serial.begin(9600);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  
  // Initialize pins
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  
  Serial.println("Gas Monitor System Ready");
  Serial.println("Commands: LED_ON, LED_OFF, BUZZ_ON, BUZZ_OFF, BOTH_ON, BOTH_OFF");
  Serial.println("Settings: THRESHOLD_xxx, AUTO_ON, AUTO_OFF, GET_STATUS");
}

void loop() {
  // Read sensor setiap interval
  if (millis() - lastReading >= readingInterval) {
    int gasValue = analogRead(MQ_PIN);
    
    // Auto trigger logic dengan acknowledgment system
    bool autoTrigger = false;
    if (autoMode && gasValue > gasThreshold && !alarmAcknowledged) {
      autoTrigger = true;
    }
    
    // Reset acknowledgment jika gas kembali normal
    if (gasValue <= gasThreshold) {
      alarmAcknowledged = false;
    }
    
    // Final actuator states (auto trigger OR manual override)
    bool finalLedState = autoTrigger || manualLedState;
    bool finalBuzzerState = autoTrigger || manualBuzzerState;
    
    // Control actuators
    digitalWrite(LED_PIN, finalLedState ? HIGH : LOW);
    digitalWrite(BUZZER_PIN, finalBuzzerState ? HIGH : LOW);
    
    // Send data to Python
    Serial.print("GAS:");
    Serial.print(gasValue);
    Serial.print(",LED:");
    Serial.print(finalLedState ? "ON" : "OFF");
    Serial.print(",BUZZER:");
    Serial.print(finalBuzzerState ? "ON" : "OFF");
    Serial.print(",AUTO:");
    Serial.print(autoMode ? "ON" : "OFF");
    Serial.print(",THRESHOLD:");
    Serial.println(gasThreshold);
    
    lastReading = millis();
  }
  
  // Check for serial commands
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    processCommand(command);
  }
}

void processCommand(String command) {
  if (command == "LED_ON") {
    manualLedState = true;
    Serial.println("LED Manual ON");
  }
  else if (command == "LED_OFF") {
    manualLedState = false;
    // Acknowledge alarm jika sedang auto trigger  
    if (autoMode) {
      alarmAcknowledged = true;
    }
    Serial.println("LED Manual OFF");
  }
  // Di processCommand(), ganti ini:
  else if (command == "BUZZER_ON") {
    manualBuzzerState = true;
    Serial.println("Buzzer Manual ON");
}
  else if (command == "BUZZER_OFF") {
    manualBuzzerState = false;
    // Acknowledge alarm jika sedang auto trigger
    if (autoMode) {
        alarmAcknowledged = true;
    }
    Serial.println("Buzzer Manual OFF");
}
  else if (command == "BOTH_ON") {
    manualLedState = true;
    manualBuzzerState = true;
    Serial.println("LED + Buzzer Manual ON");
  }
  else if (command == "BOTH_OFF") {
    manualLedState = false;
    manualBuzzerState = false;
    // Acknowledge alarm jika sedang auto trigger
    if (autoMode) {
      alarmAcknowledged = true;
    }
    Serial.println("LED + Buzzer Manual OFF");
  }
  else if (command == "AUTO_ON") {
    autoMode = true;
    alarmAcknowledged = false; // Reset acknowledgment
    Serial.println("Auto Mode ON");
  }
  else if (command == "AUTO_OFF") {
    autoMode = false;
    alarmAcknowledged = false;
    // Reset manual states ketika auto off
    manualLedState = false;
    manualBuzzerState = false;
    Serial.println("Auto Mode OFF");
  }
  else if (command.startsWith("THRESHOLD_")) {
    String thresholdStr = command.substring(10);
    int newThreshold = thresholdStr.toInt();
    if (newThreshold > 0 && newThreshold < 1024) {
      gasThreshold = newThreshold;
      alarmAcknowledged = false; // Reset acknowledgment with new threshold
      Serial.print("Threshold set to: ");
      Serial.println(gasThreshold);
    } else {
      Serial.println("Invalid threshold. Use 1-1023");
    }
  }
  else if (command == "GET_STATUS") {
    int gasValue = analogRead(MQ_PIN);
    Serial.print("STATUS - GAS:");
    Serial.print(gasValue);
    Serial.print(", THRESHOLD:");
    Serial.print(gasThreshold);
    Serial.print(", AUTO:");
    Serial.print(autoMode ? "ON" : "OFF");
    Serial.print(", MANUAL_LED:");
    Serial.print(manualLedState ? "ON" : "OFF");
    Serial.print(", MANUAL_BUZZ:");
    Serial.println(manualBuzzerState ? "ON" : "OFF");
  }
  else {
    Serial.println("Unknown command");
  }
}