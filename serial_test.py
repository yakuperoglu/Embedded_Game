# -*- coding: utf-8 -*-
"""
serial_test.py
ESP'den gelen seri veriyi OYUNU ACMADAN ham olarak gosterir.
Kablolama/firmware dogru mu diye once bunu calistir.

Kullanim:
    python serial_test.py            # settings.SERIAL_PORT kullanir
    python serial_test.py COM5       # portu elle ver

Beklenen cikti (her satir): "x1,y1,b1,x2,y2,b2"  ornek: '2048,3900,1,2050,150,0'
Joystick'i oynatinca x/y degerleri ~0..4095 arasinda degismeli, butona
basinca ilgili b degeri 1 olmali. Ctrl+C ile cik.
"""

import sys
import time

import settings

try:
    import serial
except ImportError:
    print("pyserial kurulu degil. Once:  pip install pyserial")
    sys.exit(1)

port = sys.argv[1] if len(sys.argv) > 1 else settings.SERIAL_PORT
baud = settings.SERIAL_BAUD

print("Aciliyor: %s @ %d baud  (Ctrl+C ile cik)" % (port, baud))
try:
    ser = serial.Serial(port, baud, timeout=1)
except Exception as e:
    print("Acilamadi: %s" % e)
    print("-> Dogru COM portu mu? ESP takili mi? Arduino Serial Monitor acik "
          "olmamali (portu kilitler).")
    sys.exit(1)

time.sleep(0.5)
ser.reset_input_buffer()
try:
    while True:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line:
            parts = line.split(",")
            ok = "OK" if len(parts) == 6 else "?? (6 alan bekleniyor)"
            print("%-40s %s" % (line, ok))
except KeyboardInterrupt:
    print("\nKapaniyor.")
finally:
    ser.close()
