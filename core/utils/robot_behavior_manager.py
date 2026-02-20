class RobotBehaviorManager:
    """
    Traduce estado emocional en comportamientos del robot R2.
    Cada behavior define: movimiento, luz, sonido, y duración.
    """
    def compute_behavior_params(self, emotions: dict) -> dict:
        arousal = emotions["arousal"]   # -1 a 1
        valence = emotions["valence"]   # -1 a 1
        
        # Arousal controla velocidad e intensidad de todo
        speed     = 0.2 + 0.8 * ((arousal + 1) / 2)
        intensity = 0.3 + 0.7 * ((arousal + 1) / 2)
        
        # Valence controla el "carácter" del movimiento
        # positivo = movimientos abiertos/expansivos
        # negativo = movimientos cerrados/contractivos
        movement_style = "expansive" if valence > 0 else "contractive"
        
        return {"speed": speed, "intensity": intensity, "style": movement_style}