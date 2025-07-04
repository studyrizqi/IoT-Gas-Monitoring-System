# Gas Monitor Controller - IoT Project dengan Python
# Komunikasi 2 arah antara Arduino dan Python untuk monitoring gas sensor
# Author: Rizqi (dengan bimbingan mentor yang ganteng)

# Import library yang dibutuhkan
import serial                # Untuk komunikasi serial dengan Arduino
import json                  # Untuk menyimpan/load data log dalam format JSON
import threading             # Untuk menjalankan monitoring di background
import time                  # Untuk delay dan timing
from datetime import datetime, timedelta  # Untuk timestamp dan perhitungan waktu
import os                    # Untuk operasi file system

class GasMonitorController:
    """
    Class utama untuk mengontrol gas monitor
    Fungsi: komunikasi 2 arah dengan Arduino, logging data, dan interface user
    """
    
    def __init__(self, port='COM4', baudrate=9600):
        """
        Constructor - setup awal ketika object dibuat
        Args:
            port: Port COM yang digunakan Arduino (default COM4)
            baudrate: Kecepatan komunikasi serial (9600 bps standar Arduino)
        """
        # Konfigurasi koneksi serial
        self.port = port                    # Port COM Arduino (misal: COM4, /dev/ttyUSB0)
        self.baudrate = baudrate            # Kecepatan transfer data (bits per second)
        self.serial_conn = None             # Object koneksi serial (awalnya kosong)
        self.running = False                # Flag untuk mengontrol loop monitoring
        
        # Variabel untuk data tracking
        self.last_gas_value = None          # Nilai gas terakhir (untuk delta filtering)
        self.log_file = 'gas_monitor_log.json'  # Nama file untuk menyimpan log
        self.log_data = []                  # Array untuk menyimpan semua log entries
        
        # Status sistem real-time (sinkron dengan Arduino)
        self.current_status = {
            'gas': 0,                       # Nilai sensor gas saat ini
            'led': 'OFF',                   # Status LED (ON/OFF)
            'buzzer': 'OFF',                # Status buzzer (ON/OFF)
            'auto': 'ON',                   # Mode otomatis (ON/OFF)
            'threshold': 400                # Ambang batas gas untuk trigger alarm
        }
        
        # Flag untuk mengontrol tampilan real-time (supaya tidak spam console)
        self.in_monitoring_mode = False     # True = tampilkan data real-time
        
        # Setup sistem logging saat startup
        self.setup_logging()
        # NOTE: Tidak ada self.connect_serial() di sini - ini yang bikin bug sebelumnya!

    def setup_logging(self):
        """
        Initialize sistem logging - load data lama atau buat file baru
        Dipanggil sekali saat startup
        """
        # Cek apakah file log sudah ada
        if os.path.exists(self.log_file):
            try:
                # Buka dan load data log yang sudah ada
                with open(self.log_file, 'r') as file:
                    self.log_data = json.load(file)  # Parse JSON ke Python list
                print(f"📁 Loaded {len(self.log_data)} existing log entries")
                # Bersihkan log lama (>30 hari) untuk menghemat space
                self.cleanup_old_logs()
            except:
                # Kalau file rusak/corrupt, mulai dari awal
                print("⚠️  Error loading log file, creating new one")
                self.log_data = []
        else:
            # File belum ada, buat array kosong
            print("📝 Created new log file")

    def cleanup_old_logs(self):
        """
        Hapus log entries yang lebih dari 30 hari
        Fungsi: maintenance otomatis supaya file log tidak terlalu besar
        """
        try:
            # Hitung tanggal batas (30 hari yang lalu)
            cutoff_date = datetime.now() - timedelta(days=30)
            original_count = len(self.log_data)    # Jumlah log sebelum dibersihkan
            
            # Filter: simpan hanya log yang masih valid (< 30 hari)
            valid_logs = []
            for log_entry in self.log_data:
                try:
                    # Parse timestamp string ke datetime object
                    log_date = datetime.strptime(log_entry['timestamp'], '%Y-%m-%d %H:%M:%S')
                    if log_date >= cutoff_date:      # Kalau masih dalam 30 hari
                        valid_logs.append(log_entry)  # Simpan
                except (ValueError, KeyError):
                    # Skip kalau format timestamp rusak
                    continue
            
            # Update log_data dengan yang sudah difilter
            self.log_data = valid_logs
            deleted_count = original_count - len(self.log_data)  # Hitung yang dihapus
            
            if deleted_count > 0:
                self.save_logs()  # Simpan perubahan ke file
                print(f"🗑️  Cleaned {deleted_count} old log entries (>30 days)")
            else:
                print("✅ No old logs to clean")
                
        except Exception as e:
            print(f"❌ Error cleaning logs: {e}")

    def connect_serial(self):
        """
        Koneksi ke Arduino via serial port
        Return: True jika berhasil, False jika gagal
        Fungsi: establish komunikasi dengan Arduino
        """
        import serial.tools.list_ports  # Import khusus untuk list available ports
        max_attempts = 3                # Maksimal 3 kali percobaan
        
        def is_port_available():
            """
            Cek apakah COM port tersedia di sistem
            Return: True jika port ada, False jika tidak
            """
            # List semua port yang tersedia dan cek apakah port kita ada
            return any(p.device == self.port for p in serial.tools.list_ports.comports())
        
        def force_close_port():
            """
            Paksa tutup koneksi yang mungkin masih nempel di port
            Fungsi: cleanup sebelum koneksi baru (fix untuk Windows yang suka ngeyel)
            """
            try:
                # Buat koneksi sementara lalu langsung tutup (untuk "flush" port)
                temp_serial = serial.Serial(self.port)
                temp_serial.close()
                del temp_serial  # Hapus dari memory
            except:
                pass  # Ignore error (mungkin memang tidak ada koneksi)
            
            # Cleanup khusus Windows (advanced technique)
            try:
                import win32file  # Windows API untuk file handling
                # Buka port sebagai file, lalu tutup (force release)
                handle = win32file.CreateFile(
                    f"\\\\.\\{self.port}",                    # Device path format Windows
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,  # Read/write access
                    0,                                        # Exclusive access (no sharing)
                    None,                                     # Default security
                    win32file.OPEN_EXISTING,                  # Open existing device
                    win32file.FILE_ATTRIBUTE_NORMAL,          # Normal file attributes
                    None                                      # No template file
                )
                win32file.CloseHandle(handle)  # Tutup handle
            except:
                pass  # Ignore jika win32file tidak tersedia atau error
        
        # Step 1: Cek apakah port tersedia di sistem
        if not is_port_available():
            print(f"❌ Port {self.port} not found. Available ports:")
            # Tampilkan semua port yang tersedia untuk debugging
            for port in serial.tools.list_ports.comports():
                print(f"   - {port.device}")
            return False
        
        # Step 2: Loop percobaan koneksi (maksimal 3x)
        for attempt in range(max_attempts):
            try:
                print(f"🔄 Connection attempt {attempt + 1}...")
                
                # Bersihkan koneksi lama yang mungkin masih nempel
                force_close_port()
                time.sleep(3)  # Kasih waktu Windows untuk release port (increased dari 2 detik)
                
                # Buat koneksi serial baru dengan konfigurasi yang ketat
                self.serial_conn = serial.Serial(
                    port=self.port,         # Port yang digunakan
                    baudrate=self.baudrate, # Kecepatan komunikasi
                    timeout=1,              # Timeout read (1 detik)
                    write_timeout=1,        # Timeout write (1 detik)
                    exclusive=True          # Minta akses eksklusif (no sharing)
                )
                
                # Verifikasi koneksi berhasil
                if self.serial_conn.is_open:
                    print(f"✅ Connected to Arduino on {self.port}")
                    return True
                
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_attempts - 1:  # Kalau bukan percobaan terakhir
                    print("🔄 Retrying in 3 seconds...")
                    time.sleep(3)  # Tunggu sebelum percobaan berikutnya
        
        # Kalau semua percobaan gagal
        print(f"❌ Failed to connect after {max_attempts} attempts")
        return False

    def save_logs(self):
        """
        Simpan data log ke file JSON
        Dipanggil setiap kali ada log entry baru
        """
        try:
            # Tulis array log_data ke file dalam format JSON (dengan indentasi untuk readability)
            with open(self.log_file, 'w') as file:
                json.dump(self.log_data, file, indent=2)
        except Exception as e:
            print(f"❌ Error saving logs: {e}")

    def add_log_entry(self, gas_value):
        """
        Tambah entry baru ke log dengan delta filtering
        Args:
            gas_value: Nilai sensor gas yang akan dilog
        
        Delta filtering: hanya simpan jika perubahan >= 10 poin
        Tujuan: mengurangi spam data yang mirip-mirip
        """
        # Buat timestamp untuk entry ini
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Delta filtering: cek apakah perubahan signifikan (>= 10 poin)
        if self.last_gas_value is None or abs(gas_value - self.last_gas_value) >= 10:
            # Buat object log entry
            log_entry = {
                'timestamp': timestamp,    # Waktu pencatatan
                'gas_value': gas_value    # Nilai sensor gas
            }
            
            # Tambahkan ke array dan simpan ke file
            self.log_data.append(log_entry)
            self.save_logs()
            
            # Tampilkan log entry hanya jika sedang dalam monitoring mode
            if self.in_monitoring_mode:
                print(f"📝 LOG: {timestamp} - GAS: {gas_value}")
            
            # Update nilai terakhir untuk delta filtering berikutnya
            self.last_gas_value = gas_value

    def send_command(self, command):
        """
        Kirim command ke Arduino via serial
        Args:
            command: String command yang akan dikirim
        Return: True jika berhasil, False jika gagal
        """
        try:
            # Cek apakah koneksi serial masih aktif
            if self.serial_conn and self.serial_conn.is_open:
                # Kirim command dengan newline character (Arduino butuh ini untuk parsing)
                self.serial_conn.write(f"{command}\n".encode())
                time.sleep(0.1)  # Kasih waktu Arduino untuk proses command
                return True
        except Exception as e:
            print(f"❌ Error sending command: {e}")
        return False

    def monitor_serial(self):
        """
        Monitor data yang masuk dari Arduino (jalan di background thread)
        Fungsi: terus-menerus baca data dari Arduino dan update status sistem
        """
        while self.running:  # Loop selama sistem aktif
            try:
                # Cek apakah koneksi serial masih OK
                if self.serial_conn and self.serial_conn.is_open:
                    # Cek apakah ada data yang menunggu di buffer
                    if self.serial_conn.in_waiting > 0:
                        # Baca satu line data dan parse
                        line = self.serial_conn.readline().decode().strip()
                        self.parse_arduino_data(line)  # Proses data yang masuk
            except Exception as e:
                # Tampilkan error hanya jika sedang monitoring (supaya tidak spam)
                if self.in_monitoring_mode:
                    print(f"❌ Serial monitor error: {e}")
            time.sleep(0.1)  # Delay kecil untuk tidak overload CPU

    def parse_arduino_data(self, data):
        """
        Parse/olah data yang diterima dari Arduino
        Args:
            data: String data mentah dari Arduino
        
        Format data dari Arduino: "GAS:500,LED:ON,BUZZER:OFF,AUTO:ON,THRESHOLD:400"
        """
        try:
            # Cek apakah data adalah sensor reading (dimulai dengan "GAS:")
            if data.startswith("GAS:"):
                # Split data berdasarkan koma untuk parsing
                parts = data.split(',')
                
                # Parse setiap bagian data
                gas_value = int(parts[0].split(':')[1])      # GAS:500 -> 500
                led_state = parts[1].split(':')[1]           # LED:ON -> ON
                buzzer_state = parts[2].split(':')[1]        # BUZZER:OFF -> OFF
                auto_state = parts[3].split(':')[1]          # AUTO:ON -> ON
                threshold = int(parts[4].split(':')[1])      # THRESHOLD:400 -> 400
                
                # Update status sistem dengan data terbaru
                self.current_status.update({
                    'gas': gas_value,
                    'led': led_state,
                    'buzzer': buzzer_state,
                    'auto': auto_state,
                    'threshold': threshold
                })
                
                # Tambahkan ke log dengan delta filtering
                self.add_log_entry(gas_value)
                
                # Tampilkan data real-time hanya jika sedang dalam monitoring mode
                if self.in_monitoring_mode:
                    # Format tampilan yang rapi dengan emoji
                    status_display = (f"🌡️  GAS: {gas_value:4d} | "        # :4d = padding 4 digit
                                    f"💡 LED: {led_state:3s} | "           # :3s = padding 3 karakter
                                    f"🔊 BUZZ: {buzzer_state:3s} | "
                                    f"⚙️  AUTO: {auto_state:3s} | "
                                    f"🎚️  THRESHOLD: {threshold}")
                    # Print dengan \r untuk overwrite line yang sama (real-time update)
                    print(f"\r{status_display}", end='', flush=True)
                    
            elif self.in_monitoring_mode and data:
                # Data lain dari Arduino (misal: konfirmasi command)
                print(f"\n📟 Arduino: {data}")
                
        except Exception as e:
            # Tampilkan error parsing hanya jika sedang monitoring
            if self.in_monitoring_mode:
                print(f"\n❌ Parse error: {data}")

    def show_main_menu(self):
        """
        Tampilkan menu utama aplikasi
        """
        print("\n" + "="*60)
        print("🎛️  GAS MONITOR CONTROLLER - MAIN MENU")
        print("="*60)
        print("1. Real-time Monitoring Mode")    # Mode monitor real-time
        print("2. View Log History")             # Lihat history data
        print("3. Manual Control")               # Kontrol manual LED/buzzer
        print("4. System Settings")              # Pengaturan sistem
        print("5. Exit")                         # Keluar aplikasi
        print("-"*60)

    def monitoring_mode(self):
        """
        Mode monitoring real-time - tampilan dedicated untuk melihat data live
        User bisa melihat data sensor secara real-time tanpa clutter menu
        """
        print("\n🔄 REAL-TIME MONITORING MODE")
        print("Press 'q' + Enter to return to main menu...")
        print("-"*60)
        
        # Set flag monitoring supaya parse_arduino_data() tampilkan data
        self.in_monitoring_mode = True
        
        # Loop input user (blocking) - keluar jika user ketik 'q'
        while True:
            try:
                user_input = input().strip().lower()  # Ambil input user
                if user_input == 'q':                  # Jika 'q', keluar dari mode
                    break
            except KeyboardInterrupt:                  # Jika Ctrl+C
                break
        
        # Reset flag monitoring
        self.in_monitoring_mode = False
        print("\n🏠 Returning to main menu...")

    def view_logs(self):
        """
        Menu untuk melihat log history dengan berbagai opsi filter
        """
        while True:
            print("\n📊 LOG HISTORY MENU")
            print("-"*40)
            print("1. Show Recent Logs (10 entries)")      # 10 log terakhir
            print("2. Show All Logs")                       # Semua log
            print("3. Show Logs by Date (YYYY-MM-DD)")      # Filter berdasarkan tanggal
            print("4. Back to Main Menu")                   # Kembali ke menu utama
            
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == '1':
                self.show_recent_logs(10)           # Tampilkan 10 log terakhir
            elif choice == '2':
                self.show_all_logs()                # Tampilkan semua log
            elif choice == '3':
                self.show_logs_by_date()            # Filter berdasarkan tanggal
            elif choice == '4':
                break                               # Keluar dari loop
            else:
                print("❌ Invalid choice. Please select 1-4.")

    def show_recent_logs(self, count=10):
        """
        Tampilkan log entries terbaru
        Args:
            count: Jumlah entries yang akan ditampilkan (default 10)
        """
        if not self.log_data:                       # Cek apakah ada data log
            print("📝 No log entries available")
            return
        
        # Ambil log terakhir sebanyak 'count' (slice array dari belakang)
        recent_logs = self.log_data[-count:]
        print(f"\n📋 LAST {len(recent_logs)} LOG ENTRIES:")
        print("-"*50)
        
        # Loop dan tampilkan setiap entry
        for entry in recent_logs:
            timestamp = entry['timestamp']
            gas_value = entry['gas_value']
            print(f"{timestamp} - GAS: {gas_value}")

    def show_all_logs(self):
        """
        Tampilkan semua log entries (hati-hati kalau datanya banyak!)
        """
        if not self.log_data:
            print("📝 No log entries available")
            return
        
        print(f"\n📋 ALL LOG ENTRIES ({len(self.log_data)} total):")
        print("-"*50)
        
        # Loop semua entries dalam log_data
        for entry in self.log_data:
            timestamp = entry['timestamp']
            gas_value = entry['gas_value']
            print(f"{timestamp} - GAS: {gas_value}")

    def show_logs_by_date(self):
        """
        Tampilkan log yang difilter berdasarkan tanggal tertentu
        Format input: YYYY-MM-DD (misal: 2024-03-15)
        """
        date_str = input("Enter date (YYYY-MM-DD): ").strip()
        try:
            # Validasi format tanggal user
            datetime.strptime(date_str, '%Y-%m-%d')
            
            # Filter log yang timestampnya dimulai dengan tanggal yang diminta
            filtered_logs = [log for log in self.log_data 
                           if log['timestamp'].startswith(date_str)]
            
            if filtered_logs:
                print(f"\n📋 LOGS FOR {date_str} ({len(filtered_logs)} entries):")
                print("-"*50)
                for entry in filtered_logs:
                    timestamp = entry['timestamp']
                    gas_value = entry['gas_value']
                    print(f"{timestamp} - GAS: {gas_value}")
            else:
                print(f"📝 No logs found for {date_str}")
                
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")

    def manual_control_mode(self):
        """
        Mode kontrol manual untuk LED dan Buzzer
        Fungsi: override kontrol otomatis Arduino
        """
        while True:
            print("\n🎛️  MANUAL CONTROL MENU")
            print("-"*40)
            print("1. Turn ON LED + Buzzer")           # Nyalakan LED dan buzzer
            print("2. Turn OFF LED + Buzzer")          # Matikan LED dan buzzer
            print("3. Back to Main Menu")              # Kembali ke menu utama
            
            choice = input("\nSelect option (1-3): ").strip()
            
            if choice == '1':
                # Kirim command ke Arduino untuk nyalakan LED + buzzer
                if self.send_command("BOTH_ON"):
                    print("✅ LED + Buzzer turned ON")
                else:
                    print("❌ Failed to send command")
            elif choice == '2':
                # Kirim command ke Arduino untuk matikan LED + buzzer
                if self.send_command("BOTH_OFF"):
                    print("✅ LED + Buzzer turned OFF")
                else:
                    print("❌ Failed to send command")
            elif choice == '3':
                break
            else:
                print("❌ Invalid choice. Please select 1-3.")

    def system_settings(self):
        """
        Menu pengaturan sistem
        """
        while True:
            print("\n⚙️  SYSTEM SETTINGS MENU")
            print("-"*40)
            print("1. Set Gas Threshold")                # Atur ambang batas gas
            print("2. Toggle Auto Mode")                 # On/off mode otomatis
            print("3. Clean Old Logs (>30 days)")        # Bersihkan log lama
            print("4. Show Current System Status")       # Tampilkan status sistem
            print("5. Back to Main Menu")                # Kembali ke menu utama
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == '1':
                self.set_threshold()            # Panggil fungsi set threshold
            elif choice == '2':
                self.toggle_auto_mode()        # Toggle mode otomatis
            elif choice == '3':
                self.cleanup_old_logs()        # Bersihkan log lama
            elif choice == '4':
                self.show_system_status()      # Tampilkan status sistem
            elif choice == '5':
                break
            else:
                print("❌ Invalid choice. Please select 1-5.")

    def set_threshold(self):
        """
        Set ambang batas gas untuk trigger alarm
        Range: 1-1023 (resolusi ADC Arduino 10-bit)
        """
        try:
            current_threshold = self.current_status['threshold']
            print(f"Current threshold: {current_threshold}")
            
            # Input threshold baru dari user
            new_threshold = int(input("Enter new threshold (1-1023): ").strip())
            
            # Validasi range (ADC Arduino 10-bit: 0-1023)
            if 1 <= new_threshold <= 1023:
                # Kirim command ke Arduino dengan format "THRESHOLD_xxx"
                if self.send_command(f"THRESHOLD_{new_threshold}"):
                    print(f"✅ Threshold set to {new_threshold}")
                else:
                    print("❌ Failed to set threshold")
            else:
                print("❌ Threshold must be between 1-1023")
        except ValueError:
            print("❌ Please enter a valid number")

    def toggle_auto_mode(self):
        """
        Toggle mode otomatis on/off
        Auto mode ON: Arduino otomatis nyalakan alarm jika gas > threshold
        Auto mode OFF: Hanya manual control yang bisa nyalakan alarm
        """
        current_auto = self.current_status['auto']
        
        if current_auto == 'ON':
            # Jika sekarang ON, matikan
            if self.send_command("AUTO_OFF"):
                print("✅ Auto mode turned OFF")
            else:
                print("❌ Failed to turn off auto mode")
        else:
            # Jika sekarang OFF, nyalakan
            if self.send_command("AUTO_ON"):
                print("✅ Auto mode turned ON")
            else:
                print("❌ Failed to turn on auto mode")

    def show_system_status(self):
        """
        Tampilkan status sistem saat ini
        Info: semua parameter yang sedang aktif
        """
        print("\n📊 CURRENT SYSTEM STATUS:")
        print("-"*40)
        print(f"🌡️  Gas Level: {self.current_status['gas']}")           # Nilai sensor gas
        print(f"🎚️  Threshold: {self.current_status['threshold']}")     # Ambang batas
        print(f"💡 LED Status: {self.current_status['led']}")           # Status LED
        print(f"🔊 Buzzer Status: {self.current_status['buzzer']}")     # Status buzzer
        print(f"⚙️  Auto Mode: {self.current_status['auto']}")          # Mode otomatis
        print(f"📝 Total Log Entries: {len(self.log_data)}")           # Jumlah log

    def start(self):
        """
        Fungsi utama untuk memulai sistem monitoring
        Flow: koneksi -> start monitoring thread -> main menu loop
        """
        # Step 1: Coba koneksi ke Arduino
        if not self.connect_serial():
            return  # Keluar jika gagal koneksi
        
        print("🚀 Starting Gas Monitor Controller...")
        self.running = True  # Set flag untuk jalankan monitoring
        
        # Step 2: Start background thread untuk monitoring serial data
        monitor_thread = threading.Thread(target=self.monitor_serial, daemon=True)
        monitor_thread.start()
        # daemon=True: thread akan mati otomatis ketika main program selesai
        
        # Step 3: Main menu loop (user interface)
        while True:
            try:
                self.show_main_menu()                    # Tampilkan menu
                choice = input("Select option (1-5): ").strip()  # Ambil pilihan user
                
                # Route ke fungsi yang sesuai berdasarkan pilihan
                if choice == '1':
                    self.monitoring_mode()               # Real-time monitoring
                elif choice == '2':
                    self.view_logs()                     # Lihat log history
                elif choice == '3':
                    self.manual_control_mode()           # Kontrol manual
                elif choice == '4':
                    self.system_settings()               # Pengaturan sistem
                elif choice == '5':
                    print("👋 Shutting down Gas Monitor Controller...")
                    break                                # Keluar dari loop
                else:
                    print("❌ Invalid choice. Please select 1-5.")
                    
            except KeyboardInterrupt:
                # Handle Ctrl+C untuk shutdown graceful
                print("\n👋 Shutting down Gas Monitor Controller...")
                break
        
        # Step 4: Cleanup saat shutdown
        self.running = False                             # Stop monitoring thread
        if self.serial_conn:
            self.serial_conn.close()                     # Tutup koneksi serial
        print("✅ System shutdown complete.")

# Entry point program
if __name__ == "__main__":
    """
    Main execution block - dijalankan hanya jika file ini dijalankan langsung
    (tidak dijalankan jika di-import sebagai module)
    """
    # Buat instance controller dengan port yang sesuai
    controller = GasMonitorController(port='COM4')  # Ganti 'COM4' sesuai port Arduino kamu
    
    # Mulai sistem monitoring
    controller.start()
