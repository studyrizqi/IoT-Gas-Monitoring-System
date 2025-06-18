# IoT-Gas-Monitoring-System

# IoT Gas Monitoring System

An intelligent gas detection system using Arduino and Python for real-time monitoring, logging, and alerting. Features automated threshold detection with manual override capabilities and comprehensive data logging.

## 🚀 Features

- **Real-time Gas Detection**: Continuous monitoring using MQ-2 sensor
- **Dual Alert System**: Visual (LED) and audio (buzzer) warnings
- **Smart Logging**: Delta-based logging (saves only significant changes ≥10 points)
- **Manual Override**: Acknowledge alarms to prevent spam notifications
- **Automatic Threshold**: Triggers alarm when gas levels exceed 400 ppm
- **Serial Communication**: Real-time data exchange between Arduino and Python
- **Background Monitoring**: Non-blocking threaded monitoring system
- **Error Handling**: Comprehensive error management and recovery

## 📋 Hardware Requirements

| Component | Quantity | Description |
|-----------|----------|-------------|
| Arduino Uno | 1x | Main microcontroller |
| Breadboard | 1x | For prototyping connections |
| MQ-2 Gas Sensor | 1x | Detects LPG, smoke, alcohol, propane, hydrogen, methane |
| Buzzer | 1x | Audio alert system |
| LED (Red) | 1x | Visual alert indicator |
| Resistor 220Ω | 1x | Current limiting for LED |
| Jumper Wires | Multiple | For connections |

## 🔌 Wiring Diagram

```
Arduino Uno Connections:
├── MQ-2 Sensor
│   ├── VCC → 5V
│   ├── GND → GND
│   └── AOUT → A0
├── LED (Red)
│   ├── Anode → Pin 13 
│   └── Cathode → GND (through 220Ω resistor)
└── Buzzer
    ├── Positive → Pin 12
    └── Negative → GND
```

![image](https://github.com/user-attachments/assets/1eda3106-ef51-43a5-9fa5-719c129bdcf0)


## 💻 Software Requirements

### Arduino IDE
- Arduino IDE 1.8.x or later
- No additional libraries required (uses built-in functions)

### Python Environment
- Python 3.7 or later (tested with Python 3.13)
- Required packages:
  ```bash
  pip install pyserial
  ```

### Development Tools (Optional)
- Visual Studio Code
- Arduino IDE
- Serial Monitor for debugging

## 🛠️ Installation & Setup

### 1. Hardware Assembly
1. Connect components according to the wiring diagram
2. Ensure proper power connections (5V and GND)
3. Double-check all connections before powering on

### 2. Arduino Setup
1. Open Arduino IDE
2. Load the `gas_monitoring.ino` file
3. Select your Arduino board and COM port
4. Upload the code to Arduino

### 3. Python Setup
1. Install Python dependencies:
   ```bash
   pip install pyserial
   ```
2. Update the COM port in the Python script:
   ```python
   # Modify this line in the script
   self.ser = serial.Serial('COM3', 9600, timeout=1)  # Change COM3 to your port
   ```
3. Run the Python monitoring script:
   ```bash
   python gas_monitor.py
   ```

## 🔧 Configuration

### Sensor Calibration
- **Warm-up Time**: Allow 20-30 seconds for MQ-2 sensor stabilization
- **Threshold Setting**: Default threshold is 400 (adjustable in code)
- **Baseline Calibration**: Run in clean air for 2-3 minutes to establish baseline

### Port Detection
**Windows:**
- Check Device Manager → Ports (COM & LPT)
- Usually COM3, COM4, etc.

**Linux/Mac:**
```bash
ls /dev/tty*
# Look for /dev/ttyUSB* or /dev/ttyACM*
```

## 📊 Usage

### Basic Operation
1. Power on the Arduino
2. Wait for sensor warm-up (LED may blink during initialization)
3. Run Python monitoring script
4. System will automatically detect and log gas levels

### Manual Commands
- **Acknowledge Alarm**: Press any key in Python console to silence active alarms
- **View Logs**: Check `gas_monitoring_log.json` for historical data
- **Real-time Monitoring**: Watch console output for live readings

### Data Logging
- Logs saved to `gas_monitoring_log.json`
- Delta logging: Only saves readings with ≥10 point change
- Includes timestamp and gas level

## 📈 Sample Output

```
📋 LAST 10 LOG ENTRIES:
--------------------------------------------------
2025-06-18 13:29:02 - GAS: 284
2025-06-18 13:29:04 - GAS: 274
2025-06-18 13:29:07 - GAS: 264
2025-06-18 13:29:12 - GAS: 254
2025-06-18 13:29:22 - GAS: 244
2025-06-18 13:29:47 - GAS: 234
2025-06-18 23:29:58 - GAS: 682
2025-06-18 23:29:59 - GAS: 721
2025-06-18 23:30:00 - GAS: 739
2025-06-18 23:30:01 - GAS: 749

```

## 🔍 Troubleshooting

### Common Issues

**Arduino not detected:**
- Check USB cable and connection
- Verify correct COM port selection
- Install Arduino USB drivers if needed

**Serial communication errors:**
- Ensure Arduino is not connected to Serial Monitor
- Check baud rate (must be 9600)
- Try different USB ports

**Sensor readings unstable:**
- Allow proper warm-up time (20-30 seconds)
- Check wiring connections
- Ensure stable power supply

**False alarms:**
- Recalibrate sensor in clean environment
- Adjust threshold value in code
- Check for electromagnetic interference

## 🚧 Known Limitations

- MQ-2 sensor requires regular calibration
- Threshold value is fixed (manual adjustment needed)
- Single-sensor setup (no redundancy)
- Limited to analog readings (no digital output)

## 🔮 Future Enhancements

- [ ] MQTT integration for IoT ecosystem
- [ ] SQLite database for persistent logging
- [ ] Web dashboard with Flask/FastAPI
- [ ] Mobile notifications via Telegram Bot
- [ ] Multi-sensor support (temperature, humidity)
- [ ] Automatic port detection
- [ ] Configuration file support (.ini/.json)
- [ ] Exponential moving average for smoothing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

If you encounter any issues or have questions:
- Open an issue on GitHub
- Check the troubleshooting section above
- Review the wiring diagram for connection errors

## 🙏 Acknowledgments

- Arduino community for excellent documentation
- MQ-2 sensor manufacturers for technical specifications
- Python serial library contributors

---

**⚠️ Safety Notice**: This system is for educational/hobbyist purposes. For critical safety applications, use certified commercial gas detection equipment.
