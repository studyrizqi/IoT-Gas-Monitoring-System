#!/usr/bin/env python3
"""
Gas Monitor GUI Controller - Complete Version (Needed fix issues)
Author: Rizqi

Deskripsi:
Aplikasi GUI monitoring sensor gas berbasis PyQt5, terhubung ke Arduino via serial.
Fitur: real-time chart, log history, manual control, system setting, demo mode jika Arduino tidak terhubung.
"""

import sys
import serial
import serial.tools.list_ports
import json
import time
from datetime import datetime, timedelta
import os
import csv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                             QLineEdit, QComboBox, QSpinBox, QDateEdit, QTableWidget, QTableWidgetItem,
                             QFrame, QGroupBox, QSplitter, QMessageBox, QStackedWidget, QCheckBox, QInputDialog, QFileDialog, QToolTip)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QDate, Qt
from PyQt5.QtGui import QFont
import pyqtgraph as pg
from pyqtgraph import DateAxisItem
from collections import deque
import random

# --- Serial Thread ---
class SerialMonitorThread(QThread):
    """
    Thread untuk membaca data dari Arduino secara background.
    Mengirim data ke GUI hanya jika perubahan gas >= 10.
    """
    dataReceived = pyqtSignal(dict)
    connectionLost = pyqtSignal()
    
    def __init__(self, serial_conn):
        super().__init__()
        self.serial_conn = serial_conn
        self.running = True
        self.last_gas_value = None
        
    def run(self):
        """
        Loop utama thread: baca serial, parse, filter, emit data.
        """
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    if self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode().strip()
                        parsed_data = self.parse_arduino_data(line)
                        if parsed_data:
                            # Hanya emit jika perubahan gas >= 10
                            if self.should_log_data(parsed_data['gas']):
                                self.dataReceived.emit(parsed_data)
                                self.last_gas_value = parsed_data['gas']
            except Exception as e:
                print(f"Serial thread error: {e}")
                self.connectionLost.emit()
                break
            time.sleep(0.1)
    
    def should_log_data(self, current_gas):
        """
        Hanya log data jika perubahan gas >= 10 dari nilai sebelumnya.
        """
        if self.last_gas_value is None:
            return True
        return abs(current_gas - self.last_gas_value) >= 10
            
    def parse_arduino_data(self, data):
        """
        Parse string data dari Arduino ke dictionary.
        Format: GAS:xxx,LED:ON,BUZZER:OFF,AUTO:ON,THRESHOLD:400
        """
        try:
            if data.startswith("GAS:"):
                parts = data.split(',')
                return {
                    'gas': int(parts[0].split(':')[1]),
                    'led': parts[1].split(':')[1],
                    'buzzer': parts[2].split(':')[1],
                    'auto': parts[3].split(':')[1],
                    'threshold': int(parts[4].split(':')[1]),
                    'timestamp': datetime.now()
                }
        except Exception as e:
            print(f"Parse error: {e}")
        return None
        
    def stop(self):
        """Berhenti menjalankan thread serial."""
        self.running = False

# --- Demo Data Thread ---
class DemoDataThread(QThread):
    """
    Thread demo untuk menghasilkan data palsu jika Arduino tidak terhubung.
    """
    dataReceived = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.last_gas_value = 200
        self.gas_value = 200
        
    def run(self):
        """
        Loop utama thread demo: generate data gas random, emit jika perubahan >= 10.
        """
        while self.running:
            # Simulasi perubahan gas (naik turun, kadang spike)
            change = random.randint(-15, 20)
            self.gas_value = max(0, min(1023, self.gas_value + change))
            
            # Emit hanya jika perubahan >= 10
            if abs(self.gas_value - self.last_gas_value) >= 10:
                demo_data = {
                    'gas': self.gas_value,
                    'led': 'ON' if self.gas_value > 400 else 'OFF',
                    'buzzer': 'ON' if self.gas_value > 400 else 'OFF',
                    'auto': 'ON',
                    'threshold': 400,
                    'timestamp': datetime.now()
                }
                self.dataReceived.emit(demo_data)
                self.last_gas_value = self.gas_value
                
            time.sleep(random.uniform(2, 8))  # Interval random 2-8 detik
            
    def stop(self):
        """Berhenti menjalankan thread demo."""
        self.running = False

# --- Connection Status Widget ---
class ConnectionStatus(QLabel):
    """
    Widget label status koneksi di header aplikasi.
    """
    def __init__(self):
        super().__init__()
        self.setFixedHeight(30)
        self.update_status(False)
        self.setStyleSheet("""
            QLabel {
                padding: 8px 16px;
                border-radius: 15px;
                font-weight: 600;
                font-size: 12px;
            }
        """)
        
    def update_status(self, connected, port="", demo_mode=False):
        """
        Update tampilan status koneksi di header aplikasi.
        """
        if demo_mode:
            self.setText("🟡 Demo Mode - No Arduino Connected")
            self.setStyleSheet(self.styleSheet() + "background-color: #fff3cd; color: #856404;")
        elif connected:
            self.setText(f"🟢 Connected: {port}")
            self.setStyleSheet(self.styleSheet() + "background-color: #d4edda; color: #155724;")
        else:
            self.setText("🔴 Disconnected")
            self.setStyleSheet(self.styleSheet() + "background-color: #f8d7da; color: #721c24;")

# --- Modern Button ---
class ModernButton(QPushButton):
    """
    Tombol custom dengan style modern dan warna dinamis.
    """
    def __init__(self, text, color="primary"):
        super().__init__(text)
        self.color = color
        self.setup_style()
        
    def setup_style(self):
        """
        Styling tombol modern dengan warna berbeda sesuai kebutuhan.
        """
        colors = {
            "primary": "#3498db",
            "success": "#2ecc71", 
            "warning": "#f39c12",
            "danger": "#e74c3c",
            "secondary": "#95a5a6"
        }
        base_color = colors.get(self.color, colors["primary"])
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {base_color};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: {self.darken_color(base_color)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(base_color, 0.2)};
            }}
            QPushButton:disabled {{
                background-color: #bdc3c7;
                color: #7f8c8d;
            }}
        """)
        
    def darken_color(self, hex_color, factor=0.1):
        """
        Utility untuk menggelapkan warna tombol saat hover/pressed.
        """
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(int(c * (1 - factor)) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"

# --- Status Card ---
class StatusCard(QFrame):
    """
    Widget kartu status untuk menampilkan nilai penting (Gas, Threshold, Mode, dsb).
    """
    def __init__(self, title, value="--", unit="", color="#3498db"):
        super().__init__()
        self.title = title
        self.color = color
        self.setup_ui()
        self.update_value(value, unit)
        
    def setup_ui(self):
        """
        Membuat tampilan kartu status (misal: Gas Level, Threshold, Mode).
        """
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 6px;
                border-left: 2px solid {self.color};
                padding: 8px;
                margin: 2px;
            }}
        """)
        layout = QVBoxLayout()
        
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("""
            color: #7f8c8d;
            font-size: 14px;
            font-weight: 300;
            margin-bottom: 2px;
        """)
        
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet(f"""
            color: {self.color};
            font-size: 14px;
            font-weight: bold;
            margin: 0;
        """)
        
        self.unit_label = QLabel("")
        self.unit_label.setStyleSheet("""
            color: #95a5a6;
            font-size: 14px;
            margin-top: -8px;
        """)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.unit_label)
        layout.addStretch()
        self.setLayout(layout)
        
    def update_value(self, value, unit=""):
        """
        Update nilai dan satuan pada kartu status.
        """
        self.value_label.setText(str(value))
        self.unit_label.setText(unit)

# --- Real Time Chart ---
class RealTimeChart(QWidget):
    """
    Widget grafik real-time untuk menampilkan data gas.
    """
    def __init__(self):
        super().__init__()
        self.data_buffer = deque(maxlen=8640)  # 24 hours max
        self.time_buffer = deque(maxlen=8640)
        self.setup_ui()
        
    def setup_ui(self):
        """
        Membuat widget grafik real-time dengan kontrol time range dan auto-scroll.
        """
        layout = QVBoxLayout()
        
        # Control panel
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 8px;
                margin: 4px;
            }
        """)
        control_layout = QHBoxLayout()
        
        self.time_range = QComboBox()
        self.time_range.addItems(['10 Minutes', '1 Hour', '6 Hours', '24 Hours'])
        self.time_range.setCurrentText('10 Minutes')
        self.time_range.currentTextChanged.connect(self.update_time_range)
        
        self.auto_scroll_btn = QPushButton('Auto Scroll: ON')
        self.auto_scroll_btn.clicked.connect(self.toggle_auto_scroll)
        self.auto_scroll = True
        
        control_layout.addWidget(QLabel('Time Range:'))
        control_layout.addWidget(self.time_range)
        control_layout.addStretch()
        control_layout.addWidget(self.auto_scroll_btn)
        control_frame.setLayout(control_layout)
        
        # Plot widget
        axis = DateAxisItem(orientation='bottom')
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': axis})
        self.plot_widget.setBackground('white')
        self.plot_widget.setLabel('left', 'Gas Level (ppm)', color='#2c3e50', size='12pt')
        self.plot_widget.setLabel('bottom', 'Time', color='#2c3e50', size='12pt')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.getAxis('left').setTextPen('#2c3e50')
        self.plot_widget.getAxis('bottom').setTextPen('#2c3e50')
        self.plot_widget.setMouseEnabled(x=False, y=False)  # Disable zoom/pan

        self.data_line = self.plot_widget.plot([], [], pen=pg.mkPen('#3498db', width=2))
        self.threshold_line = self.plot_widget.plot([], [], pen=pg.mkPen('#e74c3c', width=2, style=Qt.DashLine))

        layout.addWidget(control_frame)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        # Tooltip interaktif
        self.plot_widget.scene().sigMouseMoved.connect(self.show_tooltip)
        QToolTip.setFont(QFont('Segoe UI', 11))

    def add_data_point(self, value, threshold=400):
        """
        Tambahkan data baru ke grafik real-time.
        """
        current_time = datetime.now()
        self.data_buffer.append(value)
        self.time_buffer.append(current_time)
        self.update_chart(threshold)
        
    def clear_data(self):
        """Bersihkan semua data di grafik."""
        self.data_buffer.clear()
        self.time_buffer.clear()

    def add_data_point_with_time(self, value, dt_obj, threshold=400):
        """
        Tambahkan data ke grafik dengan waktu custom (untuk data log/history).
        """
        self.data_buffer.append(value)
        self.time_buffer.append(dt_obj)
        
    def update_chart(self, threshold=400):
        """
        Update tampilan grafik berdasarkan data buffer dan time range.
        """
        if not self.data_buffer:
            return

        times = list(self.time_buffer)
        values = list(self.data_buffer)

        # Filter based on time range
        max_points = self.get_time_range_points()
        if len(times) > max_points:
            times = times[-max_points:]
            values = values[-max_points:]

        if times:
            x_data = [t.timestamp() for t in times]
            self.data_line.setData(x_data, values)
            self.threshold_line.setData(x_data, [threshold] * len(values))

            # Set y-axis range (misal 0-1023 untuk sensor gas)
            self.plot_widget.setYRange(0, 1023)

            if self.auto_scroll and x_data:
                time_range_sec = self.get_time_range_seconds()
                self.plot_widget.setXRange(x_data[-1] - time_range_sec, x_data[-1])
                
    def get_time_range_points(self):
        """
        Mengembalikan jumlah data point sesuai time range yang dipilih.
        """
        range_map = {
            '10 Minutes': 60,
            '1 Hour': 360,
            '6 Hours': 2160,
            '24 Hours': 8640
        }
        return range_map.get(self.time_range.currentText(), 60)
        
    def get_time_range_seconds(self):
        """
        Mengembalikan jumlah detik sesuai time range yang dipilih.
        """
        range_map = {
            '10 Minutes': 600,
            '1 Hour': 3600,
            '6 Hours': 21600,
            '24 Hours': 86400
        }
        return range_map.get(self.time_range.currentText(), 600)
        
    def update_time_range(self):
        """
        Update grafik saat user mengganti time range.
        """
        self.update_chart()
        
    def toggle_auto_scroll(self):
        """
        Aktif/nonaktifkan auto-scroll pada grafik.
        """
        self.auto_scroll = not self.auto_scroll
        status = "ON" if self.auto_scroll else "OFF"
        self.auto_scroll_btn.setText(f'Auto Scroll: {status}')

    def show_tooltip(self, pos):
        vb = self.plot_widget.getViewBox()
        if vb.sceneBoundingRect().contains(pos):
            mouse_point = vb.mapSceneToView(pos)
            x = mouse_point.x()
            # Cari titik terdekat
            if self.data_buffer and self.time_buffer:
                times = [t.timestamp() for t in self.time_buffer]
                values = list(self.data_buffer)
                if times:
                    idx = min(range(len(times)), key=lambda i: abs(times[i] - x))
                    t_val = datetime.fromtimestamp(times[idx]).strftime('%Y-%m-%d %H:%M:%S')
                    v_val = values[idx]
                    # Tampilkan tooltip di bawah kursor
                    QToolTip.showText(
                        self.plot_widget.mapToGlobal(self.plot_widget.mapFromScene(pos)),
                        f"<b>{v_val} ppm</b><br><span style='color:#888'>{t_val}</span>"
                    )
                    return
        QToolTip.hideText()

# --- Main GUI ---
class GasMonitorGUI(QMainWindow):
    """
    Kelas utama untuk aplikasi Gas Monitor Controller GUI
    Menggunakan PyQt5 dengan desain modern dan multiple pages
    """
    
    def __init__(self):
        """
        Inisialisasi aplikasi Gas Monitor GUI
        Setup semua komponen dasar dan konfigurasi awal
        """
        super().__init__()
        
        # Inisialisasi variabel instance untuk koneksi dan monitoring
        self.serial_conn = None          # Objek koneksi serial ke Arduino
        self.monitor_thread = None       # Thread untuk monitoring real-time
        self.demo_thread = None         # Thread untuk mode demo
        self.log_data = []              # List untuk menyimpan data log
        self.log_file = 'gas_monitor_log.json'  # File untuk menyimpan log
        self.demo_mode = False          # Flag untuk mode demo
        
        # Dictionary untuk menyimpan status sistem saat ini
        self.current_status = {
            'gas': 0,           # Nilai gas sensor (0-1023)
            'led': 'OFF',       # Status LED (ON/OFF)
            'buzzer': 'OFF',    # Status buzzer (ON/OFF)
            'auto': 'ON',       # Mode otomatis (ON/OFF)
            'threshold': 400,   # Nilai ambang batas gas
            'connected': False  # Status koneksi ke Arduino
        }
        
        # Konfigurasi window utama
        self.setWindowTitle("Gas Monitor Controller")
        self.setGeometry(100, 100, 1200, 800)  # x, y, width, height
        
        # Styling CSS untuk tampilan modern
        self.setStyleSheet("""
            QMainWindow {background-color: #f5f6fa;} 
            QWidget {font-family: 'Segoe UI', Arial, sans-serif;}
        """)
        
        # Setup layout utama - menggunakan central widget sebagai container
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.main_layout = QVBoxLayout(self.central)
        
        # Header section dengan status koneksi dan tombol reconnect
        header_layout = QHBoxLayout()
        self.connection_status = ConnectionStatus()  # Widget custom untuk status koneksi
        
        # Tombol untuk mencoba koneksi ulang
        reconnect_btn = ModernButton("Reconnect", "secondary")
        reconnect_btn.clicked.connect(self.attempt_reconnect)
        
        # Susunan header: status kiri, tombol kanan
        header_layout.addWidget(self.connection_status)
        header_layout.addStretch()  # Spacer untuk mendorong tombol ke kanan
        header_layout.addWidget(reconnect_btn)
        
        self.main_layout.addLayout(header_layout)
        
        # Stacked widget untuk navigasi antar halaman
        self.stacked = QStackedWidget()
        self.main_layout.addWidget(self.stacked)
        
        # Footer dengan credit
        self.footer = QLabel("Project By Rizqi")
        self.footer.setStyleSheet("color: #aaa; font-size: 12px;")
        self.footer.setAlignment(Qt.AlignRight)
        self.main_layout.addWidget(self.footer)
        
        # Panggil method untuk setup komponen
        self.setup_pages()              # Setup semua halaman GUI
        self.setup_logging()            # Setup sistem logging
        self.attempt_initial_connection()  # Coba koneksi awal ke Arduino
        
        # Timer untuk pengecekan koneksi berkala
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_connection)
        self.connection_timer.start(5000)  # Check setiap 5 detik
        
    def setup_pages(self):
        """
        Setup semua halaman GUI dan tambahkan ke stacked widget
        Membuat 5 halaman utama: Landing, Real-time, Log, Control, Settings
        """
        # Setup setiap halaman dengan method terpisah untuk modularitas
        self.setup_landing_page()    # Halaman utama/menu
        self.setup_realtime_page()   # Monitor real-time
        self.setup_log_page()        # Riwayat log
        self.setup_control_page()    # Panel kontrol manual
        self.setup_settings_page()   # Pengaturan sistem
        
        # Tampilkan landing page sebagai default
        self.show_landing()
        
    def setup_landing_page(self):
        """
        Setup halaman landing/menu utama
        Berisi tombol navigasi ke semua fitur aplikasi
        """
        landing = QWidget()
        vbox = QVBoxLayout(landing)
        vbox.setAlignment(Qt.AlignCenter)  # Center semua elemen
        vbox.setSpacing(20)  # Jarak antar elemen
        
        # Header title dengan styling besar
        header = QLabel("GAS MONITOR CONTROLLER")
        header.setStyleSheet("""
            font-size: 36px; 
            font-weight: bold; 
            color: #3498db; 
            margin-bottom: 40px;
        """)
        vbox.addWidget(header, alignment=Qt.AlignCenter)
        
        # Daftar tombol menu dengan (text, callback_function, color_style)
        menu_buttons = [
            ("Real Time Monitor", self.show_realtime_monitor, "primary"),
            ("Log History", self.show_log_history, "primary"),
            ("Control Panel", self.show_manual_control, "primary"),
            ("System Setting", self.show_settings, "primary"),
            ("Exit", self.close, "danger")  # Tombol keluar aplikasi
        ]
        
        # Buat dan tambahkan setiap tombol menu
        for text, callback, color in menu_buttons:
            btn = ModernButton(text, color)  # Custom button class
            btn.setFixedWidth(300)   # Lebar tetap untuk konsistensi
            btn.setFixedHeight(48)   # Tinggi tetap
            btn.clicked.connect(callback)  # Connect ke fungsi tujuan
            vbox.addWidget(btn, alignment=Qt.AlignCenter)
            
        # Tambahkan halaman ke stacked widget (index 0)
        self.stacked.addWidget(landing)
        
    def setup_realtime_page(self):
        """
        Setup halaman monitoring real-time
        Menampilkan data sensor secara live dengan chart dan status cards
        """
        self.realtime_page = QWidget()
        layout = QVBoxLayout(self.realtime_page)
        
        # Header halaman
        header = QLabel("Real Time Monitor")
        header.setStyleSheet("font-size: 28px; font-weight: 700; color: #2c3e50; margin: 20px 0;")
        layout.addWidget(header)
        
        # Layout horizontal untuk status cards
        cards_layout = QHBoxLayout()
        
        # Buat 3 status card untuk menampilkan info penting
        self.gas_card = StatusCard("Gas Level", "0", "ppm", "#e74c3c")      # Merah untuk gas
        self.threshold_card = StatusCard("Threshold", "400", "ppm", "#f39c12")  # Orange untuk threshold
        self.mode_card = StatusCard("Mode", "AUTO", "", "#2ecc71")          # Hijau untuk mode
        
        # Tambahkan cards ke layout
        cards_layout.addWidget(self.gas_card)
        cards_layout.addWidget(self.threshold_card)
        cards_layout.addWidget(self.mode_card)
        layout.addLayout(cards_layout)
        
        # Chart untuk menampilkan data real-time
        self.realtime_chart = RealTimeChart()  # Custom chart widget
        layout.addWidget(self.realtime_chart)
        
        # Tombol kembali ke menu utama
        back_btn = ModernButton("Back", "secondary")
        back_btn.clicked.connect(self.show_landing)
        layout.addWidget(back_btn, alignment=Qt.AlignRight)
        
        # Tambahkan ke stacked widget (index 1)
        self.stacked.addWidget(self.realtime_page)
        
    def setup_log_page(self):
        """
        Setup halaman riwayat log
        Menampilkan tabel log dengan fitur filter dan export
        """
        self.log_page = QWidget()
        layout = QVBoxLayout(self.log_page)
        
        # Header halaman
        header = QLabel("Log History")
        header.setStyleSheet("font-size: 28px; font-weight: 700; color: #2c3e50; margin: 20px 0;")
        layout.addWidget(header)
        
        # Frame untuk controls filter dengan background putih
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: white; 
                border-radius: 12px; 
                padding: 16px; 
                margin: 10px 0;
            }
        """)
        filter_layout = QGridLayout()
        
        # Filter berdasarkan tanggal - dari dan sampai
        filter_layout.addWidget(QLabel("From Date:"), 0, 0)
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-7))  # Default 7 hari lalu
        filter_layout.addWidget(self.date_from, 0, 1)
        
        filter_layout.addWidget(QLabel("To Date:"), 0, 2)
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())  # Default hari ini
        filter_layout.addWidget(self.date_to, 0, 3)
        
        # Filter berdasarkan nilai gas - minimum dan maksimum
        filter_layout.addWidget(QLabel("Min Gas Value:"), 1, 0)
        self.min_gas = QSpinBox()
        self.min_gas.setRange(0, 1023)  # Range sensor ADC Arduino (0-1023)
        filter_layout.addWidget(self.min_gas, 1, 1)
        
        filter_layout.addWidget(QLabel("Max Gas Value:"), 1, 2)
        self.max_gas = QSpinBox()
        self.max_gas.setRange(0, 1023)
        self.max_gas.setValue(1023)  # Default nilai maksimum
        filter_layout.addWidget(self.max_gas, 1, 3)
        
        # Tombol untuk apply filter dan export data
        filter_btn = ModernButton("Apply Filter", "primary")
        filter_btn.clicked.connect(self.apply_log_filter)
        filter_layout.addWidget(filter_btn, 2, 0, 1, 2)
        
        export_btn = ModernButton("Export CSV", "success")
        export_btn.clicked.connect(self.export_log_csv)
        filter_layout.addWidget(export_btn, 2, 2, 1, 2)
        
        filter_frame.setLayout(filter_layout)
        layout.addWidget(filter_frame)
        
        # Tabel untuk menampilkan data log
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(7)  # Tambah jadi 4 kolom
        self.log_table.setHorizontalHeaderLabels([
    'Timestamp', 'Gas Value (ppm)', 'Threshold', 'Auto', 'Buzzer', 'LED', 'Status'
])
        
        # Styling tabel untuk tampilan modern
        self.log_table.setStyleSheet("""
            QTableWidget {
                background-color: white; 
                border-radius: 8px; 
                gridline-color: #e1e8ed;
                selection-background-color: #3498db;
            }
            QHeaderView::section {
                background-color: #f8f9fa; 
                padding: 12px; 
                border: none; 
                font-weight: 600;
            }
        """)
        # Stretch kolom terakhir untuk mengisi ruang kosong
        self.log_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.log_table)
        
        # Tombol kembali
        back_btn = ModernButton("Back", "secondary")
        back_btn.clicked.connect(self.show_landing)
        layout.addWidget(back_btn, alignment=Qt.AlignRight)
        
        # Tambahkan ke stacked widget (index 2)
        self.stacked.addWidget(self.log_page)
        
    def setup_control_page(self):
        """
        Setup halaman kontrol manual
        Memungkinkan user mengontrol LED dan buzzer secara manual
        """
        self.control_page = QWidget()
        layout = QVBoxLayout(self.control_page)
        
        # Header halaman
        header = QLabel("Control Panel")
        header.setStyleSheet("font-size: 28px; font-weight: 700; color: #2c3e50; margin: 20px 0;")
        layout.addWidget(header)
        
        # Frame untuk kontrol dengan background putih
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: white; 
                border-radius: 12px; 
                padding: 20px; 
                margin: 10px 0;
            }
        """)
        grid = QGridLayout()
        
        # Kontrol LED dengan checkbox
        led_label = QLabel("LED Control")
        led_label.setStyleSheet("font-weight: 600; font-size: 16px; color: #2c3e50;")
        self.led_switch = QCheckBox("Turn LED ON/OFF")
        self.led_switch.setStyleSheet("QCheckBox { font-size: 14px; }")
        self.led_switch.stateChanged.connect(self.toggle_led)  # Connect ke fungsi toggle
        
        grid.addWidget(led_label, 0, 0)
        grid.addWidget(self.led_switch, 0, 1)
        
        # Kontrol Buzzer dengan checkbox
        buzzer_label = QLabel("Buzzer Control")
        buzzer_label.setStyleSheet("font-weight: 600; font-size: 16px; color: #2c3e50;")
        self.buzzer_switch = QCheckBox("Turn Buzzer ON/OFF")
        self.buzzer_switch.setStyleSheet("QCheckBox { font-size: 14px; }")
        self.buzzer_switch.stateChanged.connect(self.toggle_buzzer)  # Connect ke fungsi toggle
        
        grid.addWidget(buzzer_label, 1, 0)
        grid.addWidget(self.buzzer_switch, 1, 1)
        
        control_frame.setLayout(grid)
        layout.addWidget(control_frame)
        
        # Spacer untuk mendorong tombol back ke bawah
        layout.addStretch()
        
        # Tombol kembali
        back_btn = ModernButton("Back", "secondary")
        back_btn.clicked.connect(self.show_landing)
        layout.addWidget(back_btn, alignment=Qt.AlignRight)
        
        # Tambahkan ke stacked widget (index 3)
        self.stacked.addWidget(self.control_page)
        
    def setup_settings_page(self):
        """
        Setup halaman pengaturan sistem
        Berisi konfigurasi threshold, mode auto, dan maintenance
        """
        self.settings_page = QWidget()
        layout = QVBoxLayout(self.settings_page)
        
        # Header halaman
        header = QLabel("System Settings")
        header.setStyleSheet("font-size: 28px; font-weight: 700; color: #2c3e50; margin: 20px 0;")
        layout.addWidget(header)
        
        # Frame untuk pengaturan dengan background putih
        settings_frame = QFrame()
        settings_frame.setStyleSheet("""
            QFrame {
                background-color: white; 
                border-radius: 12px; 
                padding: 20px; 
                margin: 10px 0;
            }
        """)
        settings_layout = QVBoxLayout()
        
        # Tombol untuk setting threshold gas
        threshold_btn = ModernButton("Set Threshold", "primary")
        threshold_btn.clicked.connect(self.set_threshold_popup)
        settings_layout.addWidget(threshold_btn)
        
        # Toggle untuk mode otomatis
        self.mode_switch = QCheckBox("Auto Mode (Automatic LED/Buzzer control)")
        self.mode_switch.setChecked(True)  # Default aktif
        self.mode_switch.setStyleSheet("QCheckBox { font-size: 14px; font-weight: 500; }")
        self.mode_switch.stateChanged.connect(self.toggle_auto_mode)
        settings_layout.addWidget(self.mode_switch)
        
        # Tombol untuk membersihkan log lama
        clean_btn = ModernButton("Clean Old Logs", "warning")
        clean_btn.clicked.connect(self.confirm_clean_log)
        settings_layout.addWidget(clean_btn)
        
        # Tombol untuk menampilkan status sistem
        status_btn = ModernButton("Show System Status", "secondary")
        status_btn.clicked.connect(self.show_status_popup)
        settings_layout.addWidget(status_btn)
        
        settings_frame.setLayout(settings_layout)
        layout.addWidget(settings_frame)
        
        # Spacer untuk mendorong tombol back ke bawah
        layout.addStretch()
        
        # Tombol kembali
        back_btn = ModernButton("Back", "secondary")
        back_btn.clicked.connect(self.show_landing)
        layout.addWidget(back_btn, alignment=Qt.AlignRight)
        
        # Tambahkan ke stacked widget (index 4)
        self.stacked.addWidget(self.settings_page)
        
    # --- Navigation Methods ---
    def show_landing(self):
        """Navigasi ke halaman utama (index 0)"""
        self.stacked.setCurrentIndex(0)
        
    def show_realtime_monitor(self):
        """Navigasi ke halaman real-time monitor (index 1)"""
        self.stacked.setCurrentIndex(1)
        self.load_log_to_chart()  # <-- Tambahkan ini
        
    def show_log_history(self):
        """
        Navigasi ke halaman log history (index 2)
        Otomatis apply filter untuk refresh data
        """
        self.stacked.setCurrentIndex(2)
        self.apply_log_filter()  # Refresh data log saat masuk halaman
        
    def show_manual_control(self):
        """
        Navigasi ke halaman manual control (index 3)
        Update status kontrol sesuai kondisi terkini
        """
        self.stacked.setCurrentIndex(3)
        self.update_control_states()  # Sync status checkbox dengan kondisi aktual
        
    def show_settings(self):
        """Navigasi ke halaman settings (index 4)"""
        self.stacked.setCurrentIndex(4)

   # --- Connection Management ---
    def attempt_initial_connection(self):
        """Try to connect to Arduino on startup"""
        try:
            # Scan semua port serial yang tersedia di sistem
            ports = list(serial.tools.list_ports.comports())
            port_names = [p.device for p in ports]
            
            # Jika tidak ada port serial ditemukan, masuk ke demo mode
            if not port_names:
                print("No serial ports detected - running in demo mode")
                self.start_demo_mode()
                return
                
            # Coba koneksi ke port pertama yang tersedia (asumsi Arduino ada di situ)
            port = port_names[0]
            # Buka koneksi serial dengan baudrate 9600 dan timeout 1 detik
            self.serial_conn = serial.Serial(port, 9600, timeout=1)
            time.sleep(2)  # Wait for Arduino to initialize - Arduino butuh waktu boot
            
            # Update status koneksi ke connected
            self.current_status['connected'] = True
            self.demo_mode = False
            self.connection_status.update_status(True, port, False)
            
            # Start monitoring thread - buat thread terpisah untuk monitor data serial
            self.monitor_thread = SerialMonitorThread(self.serial_conn)
            # Connect signal untuk handle data yang masuk dan koneksi yang putus
            self.monitor_thread.dataReceived.connect(self.handle_serial_data)
            self.monitor_thread.connectionLost.connect(self.handle_connection_lost)
            self.monitor_thread.start()
            
            print(f"Connected to Arduino on {port}")
            
        except Exception as e:
            # Kalau koneksi gagal, fallback ke demo mode
            print(f"Initial connection failed: {e}")
            self.start_demo_mode()
            
    def attempt_reconnect(self):
        """Manual reconnect attempt - dipanggil ketika user klik tombol reconnect"""
        # Stop semua thread yang masih jalan untuk cleanup
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.wait()  # Tunggu thread benar-benar selesai
            self.monitor_thread = None
            
        if self.demo_thread:
            self.demo_thread.stop()
            self.demo_thread.wait()
            self.demo_thread = None
            
        # Tutup koneksi serial yang lama
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            
        # Try to reconnect - coba koneksi ulang
        try:
            # Scan ulang port yang tersedia
            ports = list(serial.tools.list_ports.comports())
            if not ports:
                print("No ports available - switching to demo mode")
                self.start_demo_mode()
                return
                
            # Show port selection dialog - kasih user pilihan port mana yang mau dipakai
            port_names = [f"{p.device} - {p.description}" for p in ports]
            port_choice, ok = QInputDialog.getItem(
                self, "Select Port", "Choose Arduino port:", port_names, 0, False
            )
            
            # Kalau user cancel dialog, keluar dari fungsi
            if not ok:
                return
                
            # Extract nama port dari pilihan user (format: "COM3 - Arduino Uno")
            selected_port = port_choice.split(' - ')[0]
            # Buka koneksi serial ke port yang dipilih
            self.serial_conn = serial.Serial(selected_port, 9600, timeout=1)
            time.sleep(2)  # Tunggu Arduino initialize
            
            # Update status koneksi
            self.current_status['connected'] = True
            self.demo_mode = False
            self.connection_status.update_status(True, selected_port, False)
            
            # Start monitoring thread lagi dengan koneksi baru
            self.monitor_thread = SerialMonitorThread(self.serial_conn)
            self.monitor_thread.dataReceived.connect(self.handle_serial_data)
            self.monitor_thread.connectionLost.connect(self.handle_connection_lost)
            self.monitor_thread.start()
            
            # Kasih feedback ke user kalau koneksi berhasil
            QMessageBox.information(self, "Success", f"Connected to {selected_port}")
            
        except Exception as e:
            # Kalau gagal koneksi, kasih pesan error dan fallback ke demo mode
            QMessageBox.warning(self, "Connection Failed", f"Failed to connect: {str(e)}")
            self.start_demo_mode()
            
    def start_demo_mode(self):
        """Start demo mode with fake data - untuk testing tanpa Arduino fisik"""
        # Set flag demo mode dan status koneksi
        self.demo_mode = True
        self.current_status['connected'] = False
        self.connection_status.update_status(False, "", True)
        
        # Stop demo thread yang lama kalau ada
        if self.demo_thread:
            self.demo_thread.stop()
            self.demo_thread.wait()
            
        # Start thread baru untuk generate data palsu
        self.demo_thread = DemoDataThread()
        self.demo_thread.dataReceived.connect(self.handle_serial_data)
        self.demo_thread.start()
        
    def check_connection(self):
        """Check if Arduino is still connected - dipanggil secara periodik"""
        # Cek koneksi serial masih hidup atau tidak (kalau bukan demo mode)
        if not self.demo_mode and self.serial_conn:
            try:
                # Kalau port serial udah close, berarti koneksi putus
                if not self.serial_conn.is_open:
                    self.handle_connection_lost()
            except:
                # Kalau error apapun saat cek koneksi, anggap koneksi putus
                self.handle_connection_lost()
                
    def handle_connection_lost(self):
        """Handle when Arduino connection is lost - cleanup dan switch ke demo mode"""
        print("Connection lost - switching to demo mode")
        self.current_status['connected'] = False
        
        # Stop monitoring thread
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread = None
            
        # Tutup koneksi serial dengan aman
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass  # Ignore error kalau udah close
            self.serial_conn = None
            
        # Switch ke demo mode supaya aplikasi tetap jalan
        self.start_demo_mode()
        
    # --- Data Handling ---
    def handle_serial_data(self, data):
        """Handle incoming data from Arduino or demo
        Args:
            data (dict): Dictionary containing sensor data with keys:
                        - timestamp, gas, led, buzzer, auto, threshold
        """
        # Update current status dengan data terbaru
        self.current_status.update(data)
        
        # Log data ke list untuk history - format data untuk disimpan
        self.log_data.append({
            'timestamp': data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'gas': data['gas'],
            'led': data['led'],
            'buzzer': data['buzzer'],
            'auto': data['auto'],
            'threshold': data['threshold']
        })
        
        # Save to file periodically - jangan save setiap data masuk, berat
        if len(self.log_data) % 10 == 0:  # Save every 10 data points
            self.save_log_to_file()
            
        # Update real-time display kalau user lagi di halaman monitor
        if self.stacked.currentIndex() == 1:  # Real-time monitor page
            self.update_realtime_display(data)
            
    def update_realtime_display(self, data):
        """Update real-time monitor display
        Args:
            data (dict): Current sensor readings
        """
        # Update status cards dengan nilai terbaru
        self.gas_card.update_value(data['gas'], "ppm")
        self.threshold_card.update_value(data['threshold'], "ppm")
        # Tampilkan mode auto/manual
        self.mode_card.update_value("AUTO" if data['auto'] == 'ON' else "MANUAL")
        
        # Update chart dengan data point baru
        self.realtime_chart.add_data_point(data['gas'], data['threshold'])
        
        # Update card colors based on status - merah kalau gas melebihi threshold
        if data['gas'] > data['threshold']:
            self.gas_card.color = "#e74c3c"  # Red - bahaya
        else:
            self.gas_card.color = "#2ecc71"  # Green - aman
        # Apply warna baru ke label
        self.gas_card.value_label.setStyleSheet(f"color: {self.gas_card.color}; font-size: 14px; font-weight: bold;")
        
        # --- Logging ---
    def setup_logging(self):
        """Setup logging system - initialize log data dari file atau buat baru"""
     # Cek apakah file log sudah ada
        if os.path.exists(self.log_file):
            try:
               # Load data log yang sudah ada dari file JSON
              with open(self.log_file, 'r') as f:
                self.log_data = json.load(f)
            except:
                # Kalau file corrupt atau error, buat list kosong
                self.log_data = []
        else:
            # File belum ada, inisialisasi list kosong
            self.log_data = []

    def save_log_to_file(self):
        """Save log data to file - simpan semua data log ke JSON file"""
        try:
            # Write data log ke file dengan format JSON yang rapi
            with open(self.log_file, 'w') as f:
                json.dump(self.log_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save log: {e}")

    def apply_log_filter(self):
        from_date = self.date_from.date().toPyDate()
        to_date = self.date_to.date().toPyDate()
        min_gas = self.min_gas.value()
        max_gas = self.max_gas.value()
        filtered = []
        for entry in self.log_data:
            try:
                ts = datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S")
                if from_date <= ts.date() <= to_date and min_gas <= entry['gas'] <= max_gas:
                    filtered.append(entry)
            except Exception as e:
                print("Filter error:", e, entry)
        self.log_table.setRowCount(len(filtered))
        for row, entry in enumerate(filtered):
            self.log_table.setItem(row, 0, QTableWidgetItem(entry['timestamp']))
            self.log_table.setItem(row, 1, QTableWidgetItem(str(entry['gas'])))
            self.log_table.setItem(row, 2, QTableWidgetItem(str(entry['threshold'])))
            self.log_table.setItem(row, 3, QTableWidgetItem(entry.get('auto', '-')))
            status = "WARNING" if entry['gas'] > entry['threshold'] else "NORMAL"
            self.log_table.setItem(row, 4, QTableWidgetItem(entry.get('buzzer', '-')))
            self.log_table.setItem(row, 5, QTableWidgetItem(entry.get('led', '-')))
            self.log_table.setItem(row, 6, QTableWidgetItem(status))

    def export_log_csv(self):
        """Export filtered log data to CSV - export data yang sudah difilter ke file CSV"""
        # Cek apakah ada data untuk di-export
        if self.log_table.rowCount() == 0:
            QMessageBox.warning(self, "No Data", "No data to export. Apply filter first.")
            return

        # Buka dialog untuk pilih lokasi save file
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", f"gas_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV files (*.csv)"
        )

        # Kalau user pilih file, lakukan export
        if filename:
            try:
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    # Write header row
                    writer.writerow(['Timestamp', 'Gas Value (ppm)', 'Threshold', 'Auto', 'Buzzer', 'LED', 'Status'])
                    for row in range(self.log_table.rowCount()):
                        writer.writerow([
                            self.log_table.item(row, 0).text(),
                            self.log_table.item(row, 1).text(),
                            self.log_table.item(row, 2).text(),
                            self.log_table.item(row, 3).text(),
                            self.log_table.item(row, 4).text(),
                            self.log_table.item(row, 5).text(),
                            self.log_table.item(row, 6).text()
                        ])
                # Kasih feedback sukses ke user
                QMessageBox.information(self, "Success", f"Data exported to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export: {str(e)}")
            
# --- Control Methods ---
    def update_control_states(self):
        """Update control panel switch states - sinkronisasi state UI dengan data aktual"""
         # Update toggle switch sesuai status aktual dari Arduino
        self.led_switch.setChecked(self.current_status['led'] == 'ON')
        self.buzzer_switch.setChecked(self.current_status['buzzer'] == 'ON')
    
    def toggle_led(self, state):
     """Toggle LED state
        Args:
          state (bool): True untuk nyalakan LED, False untuk matikan
     """
     # Tentukan command berdasarkan state
     command = "LED_ON" if state else "LED_OFF"
     self.send_command(command)
    
    def toggle_buzzer(self, state):
     """Toggle buzzer state
        Args:
         state (bool): True untuk nyalakan buzzer, False untuk matikan
        """
     # Tentukan command berdasarkan state
     command = "BUZZER_ON" if state else "BUZZER_OFF"
     self.send_command(command)
    
    def send_command(self, command):
        """Send command to Arduino"""
        # Demo mode check di awal - early return
        if self.demo_mode:
            print(f"Demo mode: Would send command {command}")
            # Update demo status berdasarkan command
            if command == "LED_ON":
                self.current_status['led'] = 'ON'
            elif command == "LED_OFF":
                self.current_status['led'] = 'OFF'
            elif command == "BUZZER_ON":
                self.current_status['buzzer'] = 'ON'
            elif command == "BUZZER_OFF":
                self.current_status['buzzer'] = 'OFF'
            elif command.startswith("THRESHOLD"):
                threshold = int(command.split('_')[1])
                self.current_status['threshold'] = threshold
            elif command == "AUTO_ON":
                self.current_status['auto'] = 'ON'
            elif command == "AUTO_OFF":
                self.current_status['auto'] = 'OFF'
            return
        
        # Real hardware communication
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(f"{command}\n".encode())
                print(f"Sent command to Arduino: {command}")
            
                # Debugging: wait for Arduino response
                time.sleep(0.1)
            
            except Exception as e:
                print(f"Failed to send command: {e}")
                QMessageBox.warning(self, "Command Failed", f"Failed to send command: {str(e)}")
        else:
            QMessageBox.warning(self, "Not Connected", "Arduino not connected!")
# --- Settings Methods ---
    def set_threshold_popup(self):
        """Show threshold setting popup - popup untuk set threshold gas"""
        # Ambil threshold saat ini sebagai default value
        current_threshold = self.current_status.get('threshold', 400)
        # Tampilkan input dialog untuk set threshold baru
        value, ok = QInputDialog.getInt(
            self, "Set Threshold", "Enter gas threshold (ppm):",
            current_threshold, 0, 1023, 1  # min=0, max=1023 (ADC range), step=1
        )
    
        # Kalau user klik OK, kirim command threshold baru
        if ok:
            self.send_command(f"THRESHOLD_{value}")
            QMessageBox.information(self, "Success", f"Threshold set to {value} ppm")
        
    def toggle_auto_mode(self, state):
        """Toggle auto mode
        Args:
            state (bool): True untuk auto mode, False untuk manual mode
        """
        # Tentukan command berdasarkan state
        command = "AUTO_ON" if state else "AUTO_OFF"
        self.send_command(command)
    
    def confirm_clean_log(self):
        """Confirm and clean log data - hapus data log dengan konfirmasi"""
        # Minta konfirmasi dari user sebelum hapus data
        reply = QMessageBox.question(
            self, "Confirm Clean Log",
            "Are you sure you want to delete all log data?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
    
        # Kalau user confirm, lanjut ke pemilihan range tanggal
        if reply == QMessageBox.Yes:
            # Ask for date range - tanggal mulai
            from_date, ok1 = self.get_date_input("Clean From Date", "Select start date:")
            if not ok1:
                return
            
            # Tanggal akhir
            to_date, ok2 = self.get_date_input("Clean To Date", "Select end date:")
            if not ok2:
                return
            
            # Clean logs in date range - hapus log dalam rentang tanggal
            original_count = len(self.log_data)
            # Filter out (hapus) entries yang ada dalam range tanggal
            self.log_data = [
                entry for entry in self.log_data
                if not (from_date <= datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M:%S').date() <= to_date)
            ]
        
            # Hitung berapa banyak yang dihapus
            cleaned_count = original_count - len(self.log_data)
            # Save data yang sudah dibersihkan
            self.save_log_to_file()
        
            # Kasih feedback ke user
            QMessageBox.information(
                self, "Log Cleaned", 
                f"Deleted {cleaned_count} log entries from {from_date} to {to_date}"
            )
        
    def get_date_input(self, title, prompt):
        """Get date input from user
        Args:
            title (str): Title untuk dialog
            prompt (str): Prompt text untuk user
        Returns:
            tuple: (date_object, success_flag)
        """
        date_dialog = QInputDialog()
        # Tampilkan input dialog untuk tanggal
        date_str, ok = QInputDialog.getText(
            self, title, f"{prompt}\nFormat: YYYY-MM-DD",
            text=datetime.now().strftime('%Y-%m-%d')  # Default ke tanggal hari ini
        )
    
        if ok:
            try:
                # Parse string tanggal ke date object
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                return date_obj, True
            except:
                # Kalau format salah, kasih peringatan
                QMessageBox.warning(self, "Invalid Date", "Please enter date in YYYY-MM-DD format")
                return None, False
        return None, False

    def show_status_popup(self):
        """Show system status popup - tampilkan popup dengan info status sistem"""
        # Format string status sistem
        status_text = f"""
System Status:

Connection: {'Connected' if self.current_status['connected'] else 'Demo Mode'}
Gas Level: {self.current_status['gas']} ppm
Threshold: {self.current_status['threshold']} ppm
Mode: {'Auto' if self.current_status['auto'] == 'ON' else 'Manual'}
LED Status: {self.current_status['led']}
Buzzer Status: {self.current_status['buzzer']}
Total Log Entries: {len(self.log_data)}
        """
        
        # Tampilkan popup dengan info status
        QMessageBox.information(self, "System Status", status_text.strip())
    
    def load_log_to_chart(self):
        """
        Load data log 24 jam terakhir ke grafik real-time.
        """
        if not hasattr(self, 'realtime_chart'):
            return
        self.realtime_chart.clear_data()  # Bersihkan grafik dulu

        now = datetime.now()
        time_limit = now - timedelta(hours=24)
        for entry in self.log_data:
            try:
                ts = datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S")
                if ts >= time_limit:
                    self.realtime_chart.add_data_point_with_time(
                        entry['gas'],
                        ts,
                        entry.get('threshold', 400)
                    )
            except Exception as e:
                print("Chart log load error:", e, entry)
        self.realtime_chart.update_chart()
    
    # --- Cleanup ---
def closeEvent(self, event):
    """Clean up when closing application - cleanup resources saat tutup aplikasi
    Args:
        event: Close event dari Qt
    """
    # Stop threads dengan aman
    if self.monitor_thread:
        self.monitor_thread.stop()
        self.monitor_thread.wait()  # Tunggu sampai thread selesai
        
    if self.demo_thread:
        self.demo_thread.stop()
        self.demo_thread.wait()
        
    # Close serial connection
    if self.serial_conn and self.serial_conn.is_open:
        self.serial_conn.close()
        
    # Save final log sebelum tutup aplikasi
    self.save_log_to_file()
    
    # Accept event untuk tutup aplikasi
    event.accept()

# --- Main Application ---
def main():
    """Main function - entry point aplikasi"""
    # Buat QApplication instance
    app = QApplication(sys.argv)
    # Set global stylesheet untuk font
    app.setStyleSheet("""
        QApplication {
            font-family: 'Segoe UI', Arial, sans-serif;
        }
    """)
    
    # Buat dan tampilkan main window
    window = GasMonitorGUI()
    window.show()
    
    # Start event loop dan exit dengan proper code
    sys.exit(app.exec_())
    


if __name__ == "__main__":
    main()