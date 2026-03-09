"""
ultrasonic_observer.py
======================
Listener serial bidireccional para el nuevo firmware ArduinoBoardFirmware.

Lee TODAS las líneas que el Arduino envía y las despacha según su prefijo:

  US_<id>:<cm>           → lectura ultrasónica  (automática cada 500 ms)
  LED_<id>:STATE:<val>   → ACK de LED           (ignorado / logging)
  LCD_<id>:TEXT:<val>    → ACK de LCD           (ignorado / logging)
  MOT_<id>:DIR:<val>     → ACK de motor         (ignorado / logging)
  BUZZ_<id>:<val>        → ACK de buzzer        (ignorado / logging)
  EYES_ACK:<val>         → ACK de ojos          (ignorado / logging)
  GAZE_ACK:<val>         → ACK de mirada        (ignorado / logging)
  Otras líneas           → mensajes de debug / sanity test (logging)

API pública (igual que antes para no romper tensor_rt.py):
  .is_front_blocked  → True si la distancia < threshold_cm
  .is_back_blocked   → siempre False (el nuevo firmware tiene 1 sensor)
  .is_blocked        → alias de is_front_blocked
  .front_cm          → distancia del sensor en cm (-1 = sin dato)
  .back_cm           → siempre -1.0 (sin sensor trasero)
  .distance_cm       → alias de front_cm

Nuevo en este firmware:
  .ping()            → envía "US:PING\n" para forzar lectura inmediata

El objeto serial NO se cierra al detenerse (es de uso compartido).
"""

import serial
import threading
import time
from typing import Optional


class UltrasonicObserver:
    """
    Hilo daemon que escucha el puerto serial del nuevo firmware y:
      · Actualiza la distancia del sensor ultrasónico.
      · Activa/desactiva la bandera de bloqueo para la seguridad del movimiento.
      · Despacha los ACKs del resto de controladores (LED, LCD, MOT, BUZZ).
    """

    def __init__(
        self,
        ser: serial.Serial,
        threshold_cm: float = 10.0,
        write_port=None,          # SharedPort opcional para enviar PING
        controller_id: str = "US_1",
        verbose_acks: bool = False,
        verbose_us:   bool = True,
    ):
        self._ser           = ser
        self._id            = controller_id
        self.threshold_cm   = threshold_cm
        self._write_port    = write_port   # SharedPort para send_line("US:PING")
        self._verbose_acks  = verbose_acks
        self._verbose_us    = verbose_us

        # Estado del sensor ultrasónico (1 sensor en el nuevo firmware)
        self._distance_cm: float  = -1.0
        self._blocked             = threading.Event()
        self._stop                = threading.Event()

        # Callbacks opcionales: se llaman cuando llega un ACK de otro tipo
        # Uso: observer.on_ack["MOT"] = lambda controller_id, payload: ...
        self.on_ack: dict[str, Optional[callable]] = {
            "LED":  None,
            "LCD":  None,
            "MOT":  None,
            "BUZZ": None,
            "EYES": None,
            "GAZE": None,
        }

        self._thread = threading.Thread(
            target=self._run,
            name="ArduinoListener",
            daemon=True,
        )

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    # ── API de seguridad (igual que antes) ────────────────────────────────────

    @property
    def is_front_blocked(self) -> bool:
        """Verdadero cuando el sensor detecta un obstáculo muy cercano."""
        return self._blocked.is_set()

    @property
    def is_back_blocked(self) -> bool:
        """Siempre False — el nuevo firmware tiene UN solo sensor."""
        return False

    @property
    def is_blocked(self) -> bool:
        """Verdadero cuando el sensor (delantero) está bloqueado."""
        return self._blocked.is_set()

    @property
    def front_cm(self) -> float:
        """Distancia del sensor en cm. -1 si no hay dato todavía."""
        return self._distance_cm

    @property
    def back_cm(self) -> float:
        """Siempre -1.0 — sin sensor trasero en el nuevo firmware."""
        return -1.0

    @property
    def distance_cm(self) -> float:
        """Alias de front_cm."""
        return self._distance_cm

    def ping(self) -> None:
        """
        Envía "US:{id}:PING\n" al Arduino para solicitar una lectura inmediata.
        """
        if self._write_port is not None:
            # Nuevo protocolo: {BASE_ID}:{SPECIFIC_ID}:{COMMAND}
            self._write_port.send_line(f"US:{self._id}:PING")
        else:
            print(f"[Ultrasonic] ping() ignorado para {self._id} — write_port no configurado")

    # ── Unit Test ────────────────────────────────────────────────────────────

    def test_interface(self) -> bool:
        """
        Prueba la interfaz enviando un PING (si write_port está configurado).
        Retorna True si no hubo excepciones.
        """
        print(f"--- Testing UltrasonicObserver ({self._id}) ---")
        try:
            self.ping()
            print("[Ultrasonic] Test interface OK")
            return True
        except Exception as e:
            print(f"[Ultrasonic] Test interface FAILED: {e}")
            return False

    # ── Hilo de escucha ───────────────────────────────────────────────────────

    def _run(self) -> None:
        print(
            f"[Ultrasonic] Listener serial iniciado "
            f"(umbral: {self.threshold_cm} cm)"
        )
        try:
            while not self._stop.is_set():
                raw = self._ser.readline()
                if not raw:
                    continue

                line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                self._dispatch(line)

        except Exception as exc:
            print(f"[Ultrasonic] Error en hilo listener: {exc}")
        finally:
            print("[Ultrasonic] Listener serial detenido.")

    def _dispatch(self, line: str) -> None:
        """Despacha una línea recibida del Arduino según su prefijo."""
        colon = line.find(':')
        if colon <= 0:
            # Línea sin formato TIPO:VALOR (sanity test, debug, etc.)
            if self._verbose_acks:
                print(f"[Arduino←] {line}")
            return

        controller_id = line[:colon]       # e.g.  "US_1", "LED_2", "MOT_1"
        payload       = line[colon + 1:]   # e.g.  "42", "STATE:ON", "DIR:FWD,SPD:80"

        # ── Resolve pending Promises in SharedPort ────────────────────────────
        if self._write_port is not None:
            # SharedPort matches the controller_id to the oldest pending Future
            self._write_port.resolve_response(controller_id, payload)

        # ── Sensor ultrasónico ────────────────────────────────────────────────
        if controller_id.startswith("US"):
            self._handle_us(controller_id, payload)
            return

        # ── ACKs de otros controladores ───────────────────────────────────────
        for prefix, cb_key in (
            ("LED",  "LED"),
            ("LCD",  "LCD"),
            ("MOT",  "MOT"),
            ("BUZZ", "BUZZ"),
            ("EYES", "EYES"),
            ("GAZE", "GAZE"),
        ):
            if controller_id.startswith(prefix):
                if self._verbose_acks:
                    print(f"[Arduino←] {line}")
                cb = self.on_ack.get(cb_key)
                if cb is not None:
                    try:
                        cb(controller_id, payload)
                    except Exception as e:
                        print(f"[Ultrasonic] Error en callback {cb_key}: {e}")
                return

        # Línea desconocida
        if self._verbose_acks:
            print(f"[Arduino←] {line}")

    def _handle_us(self, controller_id: str, payload: str) -> None:
        """Procesa una lectura ultrasónica: 'US_1:<cm>'."""
        try:
            cm = float(payload)
        except ValueError:
            return

        self._distance_cm = cm

        # Actualizar bandera de bloqueo
        was_blocked = self._blocked.is_set()
        if cm > 0 and cm < self.threshold_cm:
            if not was_blocked and self._verbose_us:
                print(
                    f"[Ultrasonic] {controller_id} BLOQUEADO — "
                    f"{cm:.1f} cm < {self.threshold_cm} cm"
                )
            self._blocked.set()
        else:
            if was_blocked and self._verbose_us:
                print(f"[Ultrasonic] {controller_id} despejado — {cm:.1f} cm")
            self._blocked.clear()
