# IoT Gas Monitoring System

> **Reality Check**: This is an educational project, not a replacement for commercial gas detectors. If you smell gas for real, call the professionals and evacuate—don't wait for your Arduino to save you.

## What This Does

A real-time gas monitoring system that combines Arduino sensor reading with Python interfaces. Available in two flavors: CLI for terminal lovers and GUI for those who prefer clicking buttons. Perfect for labs, workshops, or impressing your professors.

**Core Features:**
- Real-time gas detection using MQ-2 sensor
- Dual alert system (LED + buzzer that might annoy your neighbors)
- Smart data logging with delta-based saving
- Manual override when the system gets too paranoid
- Auto-threshold detection at 400 ppm
- Two interface options: CLI or GUI

## Choose Your Adventure

### 🖥️ CLI Version (Terminal Warriors)
- Lightweight console-based monitoring
- Delta logging (saves only significant changes ≥10 points)
- Real-time console output with last 10 entries
- Perfect for headless systems or SSH sessions

### 🎨 GUI Version (Point & Click Enthusiasts)
- PyQt5-based graphical interface
- Real-time charts and visual status cards
- Historical data filtering and CSV export
- Demo mode for testing without hardware
- Multiple control panels and settings

## Hardware Requirements

| Component | Qty | Notes |
|-----------|-----|-------|
| Arduino Uno | 1x | Original preferred, clones tend to be... unreliable |
| MQ-2 Gas Sensor | 1x | Detects: LPG, smoke, alcohol, propane, hydrogen, methane |
| Buzzer | 1x | 5V type, not 12V (learned this the hard way) |
| LED (Red) | 1x | Red = danger, basic psychology |
| Resistor 220Ω | 1x | Keep that LED alive |
| Breadboard | 1x | Good quality, not the loose-contact ones |
| Jumper Wires | ~10pcs | More is always better |
| USB Cable | 1x | A-B type, data cable not charging-only |

**Estimated Cost**: ~$15-25 USD (depends on where you shop)

## Wiring Diagram

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

**Important**: MQ-2 needs 2-3 minutes warming up for accurate readings. Don't panic if initial readings look weird.

## Quick Start

### 1. Hardware Setup
1. Wire everything according to the diagram above
2. Double-check connections (especially power and ground)
3. Connect Arduino to computer via USB

### 2. Arduino Setup
```bash
# 1. Install Arduino IDE
# 2. Open and upload the appropriate sketch:
#    - gas_monitor_cli.ino for CLI version
#    - gas_monitor_gui.ino for GUI version
# 3. Test in Serial Monitor (9600 baud)
# 4. CLOSE Serial Monitor before running Python!
```

### 3. Python Setup

**For CLI Version:**
```bash
# Minimal dependencies
pip install pyserial

# Run the CLI monitor
python gas_monitor_cli.py
```

**For GUI Version:**
```bash
# Create virtual environment (recommended)
python -m venv gas_monitor_env
source gas_monitor_env/bin/activate  # Linux/Mac
# or
gas_monitor_env\Scripts\activate     # Windows

# Install GUI dependencies
pip install PyQt5 pyserial pyqtgraph

# Run the GUI application
python gas_monitor_gui.py
```

### 4. First Run
1. Application will auto-detect Arduino on COM ports
2. If not found, GUI version enters Demo Mode with simulated data
3. If Demo Mode also fails, restart and try again
4. Test with a lighter (CAREFULLY!) to trigger the sensor

## How It Works

### Arduino Side
- Reads MQ-2 sensor every 1 second
- Sends data via serial in format: `GAS:xxx,LED:ON/OFF,BUZZER:ON/OFF,AUTO:ON/OFF,THRESHOLD:yyy`
- Receives commands from Python for manual control
- Logic: `finalState = autoTrigger || manualState`

### Python Side

**CLI Version:**
- Simple serial communication
- Delta-based logging (only saves changes ≥10 points)
- Console output with last 10 log entries
- Manual alarm acknowledgment via keypress

**GUI Version:**
- Separate thread for non-blocking serial reading
- Real-time chart updates (when not lagging)
- Comprehensive data logging to JSON
- Multiple interface panels for control

### Control Logic
```cpp
// Arduino logic (simplified)
bool autoTrigger = (autoMode && gasValue > threshold && !alarmAcknowledged);
bool finalLedState = autoTrigger || manualLedState;
```

## Interface Features

### CLI Version
- **Real-time Console Output**: Live gas readings with timestamps
- **Delta Logging**: Efficient storage of significant changes only
- **Last 10 Entries**: Quick overview of recent readings
- **Manual Override**: Acknowledge alarms via console input

### GUI Version
- **Real-Time Monitor**: Live charts and status cards
- **Log History**: Filterable historical data table
- **Control Panel**: Manual LED/Buzzer toggle buttons
- **System Settings**: Threshold adjustment and configuration
- **Demo Mode**: Testing without hardware connection

## Technical Specifications

| Parameter | Value | Notes |
|-----------|-------|-------|
| Gas Detection Range | 200-10000 ppm | MQ-2 sensor spec |
| Response Time | ~10 seconds | Includes sensor + processing delay |
| Operating Voltage | 5V DC | Arduino power requirement |
| Current Consumption | ~100mA | Estimate with all components active |
| Data Update Rate | 1 Hz | Every second |
| Log File Format | JSON | Human-readable format |
| Threshold Default | 400 ppm | Adjustable in code |

## Configuration

### Port Detection
**Windows:**
- Check Device Manager → Ports (COM & LPT)
- Usually COM3, COM4, etc.

**Linux/Mac:**
```bash
ls /dev/tty*
# Look for /dev/ttyUSB* or /dev/ttyACM*
```

### Sensor Calibration
- **Warm-up Time**: 2-3 minutes for stabilization
- **Baseline Setup**: Run in clean air initially
- **Threshold Adjustment**: Modify in Arduino code or GUI settings

## Sample Output

**CLI Version:**
```
📋 LAST 10 LOG ENTRIES:
--------------------------------------------------
2025-06-18 13:29:02 - GAS: 284
2025-06-18 13:29:04 - GAS: 274
2025-06-18 13:29:07 - GAS: 264
2025-06-18 13:29:12 - GAS: 254
2025-06-18 23:29:58 - GAS: 682  ⚠️ ALERT!
2025-06-18 23:29:59 - GAS: 721  ⚠️ ALERT!
```

**GUI Version:**
- Real-time charts with trend visualization
- Status cards showing current levels
- Historical data in sortable tables

## Troubleshooting

### Arduino Not Detected
1. Check USB cable (data capable, not charging-only)
2. Install CH340 drivers for clone boards
3. Try different USB ports
4. Restart Arduino IDE and check port selection

### Serial Communication Issues
1. Ensure Serial Monitor is closed before running Python
2. Verify baud rate is 9600 on both sides
3. Check for permission issues on Linux/Mac
4. Try different COM ports

### Sensor Reading Problems
1. Allow proper warm-up time (2-3 minutes)
2. Check all wiring connections
3. Calibrate in clean air environment
4. Consider humidity and temperature effects

### GUI Specific Issues
1. Check Python version (3.7+ required)
2. Reinstall PyQt5 if crashes occur
3. Run from terminal to see error messages
4. Clear old log files if performance degrades

## File Structure
```
gas_monitor_project/
├── arduino_sketches/
│   ├── gas_monitor_cli.ino      # Arduino code for CLI version
│   └── gas_monitor_gui.ino      # Arduino code for GUI version
├── python_scripts/
│   ├── gas_monitor_cli.py       # CLI Python script
│   └── gas_monitor_gui.py       # GUI Python application
├── logs/
│   ├── gas_monitoring_log.json  # CLI log file
│   └── gas_log.json            # GUI log file
├── README.md                    # This file
└── requirements.txt             # Python dependencies
```

## Known Issues

**Both Versions:**
- Serial connection occasionally times out (restart fixes)
- MQ-2 sensor requires periodic recalibration
- Fixed threshold values (manual code adjustment needed)

**CLI Version:**
- Limited visual feedback
- No real-time graphing
- Console-only interface

**GUI Version:**
- Chart performance degrades after ~1000 data points
- Demo mode data somewhat unrealistic
- Threading cleanup sometimes incomplete on exit

## Future Improvements

**Planned Features:**
- [ ] Automatic port detection
- [ ] SQLite database integration
- [ ] Web dashboard (Flask/FastAPI)
- [ ] MQTT/IoT platform integration
- [ ] Multi-sensor support
- [ ] Mobile notifications
- [ ] Sensor calibration wizard

**Nice-to-Haves:**
- [ ] Configuration file support
- [ ] Data export formats (CSV, Excel)
- [ ] Email/SMS alerts
- [ ] Cloud data backup
- [ ] Machine learning anomaly detection

## Safety Notes

⚠️ **CRITICAL REMINDERS**:
- This is educational equipment, not safety-certified
- Never rely on this for life-safety applications
- Test in safe, controlled environments
- Have proper fire safety equipment nearby
- If you smell gas, evacuate first, debug Arduino later

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Test thoroughly (don't just commit and pray)
4. Submit PR with clear description
5. Be patient with code reviews

## License

MIT License - Use it, modify it, break it, fix it. Just don't blame us when things go sideways.

## Support

- **GitHub Issues**: For bug reports and feature requests
- **Stack Overflow**: For Python/Arduino programming questions
- **Google**: For basic stuff you should probably already know
- **Documentation**: Read the code comments, they're actually useful

## Acknowledgments

- Arduino community for excellent documentation
- MQ-2 sensor manufacturers for (mostly) accurate datasheets
- Python library contributors for making serial communication bearable
- Coffee shops for providing the caffeine that made this possible

---

*Crafted with ☕ and excessive debugging by a telecommunications student who definitely should be studying for finals instead of building gas detectors.*
