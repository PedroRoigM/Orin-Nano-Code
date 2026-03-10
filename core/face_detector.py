import numpy as np
from insightface.app import FaceAnalysis


class FaceDetector:
    """Modelo de detección de caras SCRFD de InsightFace."""

    def __init__(
        self,
        det_size: tuple[int, int] = (640, 480),
        conf_threshold: float = 0.5,
        model_pack: str = "buffalo_s",  # También existe buffalo_l que es mejor pero más pesado. Va desde sc hasta l
    ) -> None:

        self._conf = conf_threshold
        # Solo carga el modelo de detección (omite los modelos de reconocimiento/landmarks)
        self._app = FaceAnalysis(
            name=model_pack,
            allowed_modules=["detection"],
        )
        self._app.prepare(ctx_id=-1, det_size=det_size)
        print(
            f"[FaceDetector] SCRFD ({model_pack}) preparado — "
            f"det_size={det_size}, conf={conf_threshold}"
        )

    def detect(self, rgb_frame: np.ndarray):
        faces = self._app.get(rgb_frame)
        if not faces:
            return None, None

        boxes = np.array([f.bbox for f in faces], dtype=np.float32)
        scores = np.array([f.det_score for f in faces], dtype=np.float32)

        # Filtra por confianza
        mask = scores >= self._conf
        if not mask.any():
            return None, None

        return boxes[mask], scores[mask]
