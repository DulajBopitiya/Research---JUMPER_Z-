# src/services/serial_service.py

import threading
import time
import serial
import serial.tools.list_ports

from src.core.event_bus import event_bus
from src.core.events import Serial   


class SerialService:
    def __init__(self):
        self._ser: serial.Serial | None = None
        self._reader_thread: threading.Thread | None = None
        self._running = False
        self._busy = False
        self._lock = threading.Lock()

    # -----------------------------
    # Public API
    # -----------------------------
    def connect(self, port: str, baudrate: int):
        with self._lock:
            if self._ser or self._busy:
                self._emit_busy()
                return

            try:
                self._ser = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=0.1
                )
                self._running = True
                self._reader_thread = threading.Thread(
                    target=self._read_loop,
                    daemon=True
                )
                self._reader_thread.start()

                event_bus.emit(
                    Serial.OPENED,
                    port=port,
                    baudrate=baudrate
                )

            except Exception as e:
                self._emit_error(str(e))

    def disconnect(self):
        with self._lock:
            self._running = False

            if self._ser:
                try:
                    self._ser.close()
                except Exception:
                    pass
                finally:
                    self._ser = None

            event_bus.emit(Serial.CLOSED)

    def write(self, data: str):
        with self._lock:
            if not self._ser or self._busy:
                self._emit_busy()
                return

            try:
                self._ser.write(data.encode())
                event_bus.emit(
                    Serial.SERIAL_WRITE_ACK,
                    data=data
                )
            except Exception as e:
                self._emit_error(str(e))

    def list_ports(self) -> list[str]:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        event_bus.emit(
            Serial.AVAILABLE_PORTS,
            ports=ports
        )
        return ports

    def set_busy(self, flag: bool):
        with self._lock:
            self._busy = flag
            if flag:
                event_bus.emit(Serial.BUSY)

    # -----------------------------
    # Internal
    # -----------------------------
    def _read_loop(self):
        while self._running and self._ser:
            try:
                line = self._ser.readline()
                if line:
                    event_bus.emit(
                        Serial.DATA_RECEIVED,
                        data=line.decode(errors="ignore")
                    )
            except Exception as e:
                self._emit_error(str(e))
                break

            time.sleep(0.01)

    def _emit_busy(self):
        event_bus.emit(Serial.BUSY)

    def _emit_error(self, msg: str):
        event_bus.emit(
            Serial.SERIAL_ERROR,
            message=msg
        )
