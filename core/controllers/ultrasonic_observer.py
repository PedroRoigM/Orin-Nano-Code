import serial
import threading


class UltrasonicObserver:
    """
    Escucha un Arduino a través de un objeto serial ya abierto y compartido.
    El Arduino envía las lecturas de dos sensores ultrasónicos en una sola
    línea CSV por iteración de su loop():

        "front_cm,back_cm\n"    p.ej.  "12.5,8.3\n"

    Cuando la distancia de un sensor cae por debajo de `threshold_cm` se
    activa la bandera de bloqueo correspondiente. El código de movimiento
    debe consultar `is_front_blocked` e `is_back_blocked` antes de enviar
    comandos de avance o retroceso respectivamente.

    Se ejecuta en un hilo demonio para que muera automáticamente cuando el
    programa principal termina. El objeto serial NO se cierra al detenerse,
    ya que es de uso compartido.
    """

    def __init__(self, ser: serial.Serial, threshold_cm: float = 10.0):
        self._ser         = ser
        self.threshold_cm = threshold_cm

        self._front_blocked = threading.Event()  # delantero muy cerca del borde
        self._back_blocked  = threading.Event()  # trasero muy cerca del borde
        self._stop          = threading.Event()  # señal para detener el hilo
        self._thread        = threading.Thread(target=self._run, name="UltrasonicObserver", daemon=True)

        self._front_cm: float = -1.0   # última lectura del sensor delantero (-1 = sin dato)
        self._back_cm:  float = -1.0   # última lectura del sensor trasero

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    @property
    def is_front_blocked(self) -> bool:
        """Verdadero cuando el sensor delantero detecta el borde de la mesa."""
        return self._front_blocked.is_set()

    @property
    def is_back_blocked(self) -> bool:
        """Verdadero cuando el sensor trasero detecta el borde de la mesa."""
        return self._back_blocked.is_set()

    @property
    def is_blocked(self) -> bool:
        """Verdadero cuando cualquiera de los dos sensores está bloqueado."""
        return self._front_blocked.is_set() or self._back_blocked.is_set()

    @property
    def front_cm(self) -> float:
        """Última distancia leída por el sensor delantero en cm. -1 si no hay dato."""
        return self._front_cm

    @property
    def back_cm(self) -> float:
        """Última distancia leída por el sensor trasero en cm. -1 si no hay dato."""
        return self._back_cm

    def _update_sensor(self, event: threading.Event, distance_cm: float, label: str) -> None:
        if distance_cm < self.threshold_cm:
            if not event.is_set():
                print(f"[Ultrasonic] {label} BLOCKED — {distance_cm:.1f} cm < {self.threshold_cm} cm")
            event.set()
        else:
            if event.is_set():
                print(f"[Ultrasonic] {label} clear — {distance_cm:.1f} cm")
            event.clear()

    def _run(self) -> None:
        print(f"[Ultrasonic] Observer started (threshold: {self.threshold_cm} cm, sensors: front + back)")
        try:
            while not self._stop.is_set():
                raw = self._ser.readline()
                if not raw:
                    continue

                line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                parts = line.split(",")
                if len(parts) != 2:
                    continue  # ignorar líneas mal formadas o mensajes de arranque

                try:
                    front_cm = float(parts[0])
                    back_cm  = float(parts[1])
                except ValueError:
                    continue

                self._front_cm = front_cm
                self._back_cm  = back_cm
                self._update_sensor(self._front_blocked, front_cm, "FRONT")
                self._update_sensor(self._back_blocked,  back_cm,  "BACK")

        except Exception as exc:
            print(f"[Ultrasonic] Error in observer thread: {exc}")
        finally:
            print("[Ultrasonic] Observer stopped.")
