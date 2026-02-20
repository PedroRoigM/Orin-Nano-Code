from core.devices.neurosky_client import NeuroSkyClient
from core.processing.emotion_normalizer import EmotionNormalizer
from core.processing.emotion_classifier import EmotionClassifier
from core.processing.emotion_color_mapper import EmotionColorMapper
from core.udp_sender import UDPSender
from core.utils.port import Port
from core.controllers.holo_controller import HoloController
from core.utils.eeg_plotter import EEGPlotter
from core.utils.brain_controller import BrainController
from core.utils.robot_behavior_manager import RobotBehaviorManager
import json
import time

def main():
    holoController = HoloController(port_name='COM5')
    brainController = BrainController()
    robotBehaviorManager = RobotBehaviorManager()
    
    #plotter = EEGPlotter()
    
    print("Conectando a la diadema NeuroSky...")
    client = NeuroSkyClient()
    client.connect()
    port = Port(port_name='COM5')
    print("Conectado a NeuroSky")

    print("Inicializando módulos de procesamiento...")
    normalizer = EmotionNormalizer()
    classifier = EmotionClassifier()
    color_mapper = EmotionColorMapper()
    udp_sender = UDPSender(ip='127.0.0.1', port=7000)
    print("Módulos inicializados")

    print("\nGenerando colores RGB desde emociones... Presiona CTRL+C para detener.\n")

    try:
        while True:
            raw_data = client.read_data()
            if not raw_data:
                continue
            if raw_data.get("poorSignalLevel", 0) > 50:  # 200 = no signal, 0 = perfect
                print(f"[SIGNAL] Poor signal: {raw_data.get('poorSignalLevel')}, skipping frame")
                continue
            if "eegPower" not in raw_data or "eSense" not in raw_data:
                continue

            # Unificar eegPower y eSense en un solo diccionario
            eeg_values = {**raw_data["eegPower"], **raw_data["eSense"]}
            
            # Plot mostrando todos los valores
            #plotter.update(eeg_values)
            

            # Normalizar y clasificar
            normalized = normalizer.normalize_all(eeg_values)
            emotions = classifier.classify_emotions(normalized)
            brain_results = brainController.update(emotions)
            behavior = robotBehaviorManager.compute_behavior_params(emotions)
            print("="*50)
            print(emotions)
            print("="*50)
            print(brain_results)
            print("=" * 50)
            print(behavior)
            print("=" * 50)

            # ===== GENERAR COLORES =====
            
            # Opción 1: Color basado en categoría de Russell
            russell_rgb = color_mapper.get_russell_color(emotions)
            
            # Opción 2: Color mezclado de todas las emociones
            blended_rgb = color_mapper.get_blended_color(emotions)
            
            # Opción 3: Color de la emoción dominante
            top3_rgb = color_mapper.get_top3_blended_color(emotions)
            top3_info = color_mapper.get_top3_info(emotions)

            
            # Opción 4: Color basado en valencia y activación
            valence_rgb = color_mapper.get_valence_arousal_color(emotions)
            
            # Opción 5: Obtener todo en un diccionario
            all_colors = color_mapper.get_color_dict(emotions)

            # ===== MOSTRAR RESULTADOS =====
            print("=" * 60)
            print(f"Categoría Russell: {emotions['categoria_russell']}")
            print(f"  └─ Color RGB: {russell_rgb}")
            print(f"  └─ Color HEX: {color_mapper.rgb_to_hex(russell_rgb)}")
            print()
            print("Top 3 emociones:")
            for name, score, color in top3_info:
                print(f"  └─ {name:<12} {score:>3}/100  RGB{color}")
            print(f"  └─ Blended RGB: {top3_rgb}  HEX: {color_mapper.rgb_to_hex(top3_rgb)}")
            print()
            print(f"Color mezclado: RGB{blended_rgb}")
            print(f"Color valencia/activación: RGB{valence_rgb}")
            print()

            # Añadir colores al diccionario de emociones para enviar por UDP
            emotions_with_colors = {
                **emotions,
                "colors": {
                    "russell": russell_rgb,
                    "blended": blended_rgb,
                    "dominant": top3_rgb,
                    "valence_arousal": valence_rgb
                }
            }
            colors = list(top3_rgb) + [0]
            
            # Enviar por el puerto
            holoController.changeHoloRGBColor(3, 1, colors)

            # Enviar por UDP
            udp_sender.send(emotions_with_colors)

            time.sleep(0.5)  # Pequeña pausa para no saturar la consola

    except KeyboardInterrupt:
        print("\nConexión finalizada por el usuario.")
    finally:
        client.close()


if __name__ == "__main__":
    main()           # Ejecutar con datos reales del MindWave