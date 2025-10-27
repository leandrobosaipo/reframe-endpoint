# reframe_mediapipe_falante_v7.py
import cv2
import mediapipe as mp
import numpy as np
import subprocess
import os
import tempfile
import time
from collections import deque

mp_face_mesh = mp.solutions.face_mesh

def _mux_audio(video_temp, source_with_audio, output_final):
    # copia o vídeo gerado e pega o áudio do original (sem re-encode adicional)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_temp,
        "-i", source_with_audio,
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest", output_final
    ], check=True)

def reframe_video(input_path: str,
                  output_path: str,
                  progress_cb=None) -> dict:
    """
    Reenquadra 16:9 -> 9:16 mantendo o falante principal.
    progress_cb(stage, progress, meta)  # progress: 0..1
    Retorna métricas para log.
    """

    cap = cv2.VideoCapture(input_path)
    fps    = cap.get(cv2.CAP_PROP_FPS) or 24.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

    crop_h = height
    crop_w = int(height * 9 / 16)
    tmp_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    out = cv2.VideoWriter(tmp_video, cv2.VideoWriter_fourcc(*'mp4v'), fps, (crop_w, crop_h))

    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=False, max_num_faces=4, refine_landmarks=True,
        min_detection_confidence=0.5, min_tracking_confidence=0.5
    )

    # histórico para decidir falante
    activity_hist = deque(maxlen=15)
    centro_atual  = (width // 2, height // 2)
    centro_antigo = np.array(centro_atual)

    faces_detected_sum = 0

    def report(i):
        if progress_cb:
            progress_cb(stage="reframing", progress=min(0.999, i/float(max(1,total))), meta={
                "frame": i, "total_frames": total
            })

    for i in range(total):
        ok, frame = cap.read()
        if not ok: break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        candidatos = []
        if results.multi_face_landmarks:
            faces_detected_sum += len(results.multi_face_landmarks)
            for landmarks in results.multi_face_landmarks:
                pts = np.array([(lm.x * width, lm.y * height) for lm in landmarks.landmark])
                top_lip    = np.mean(pts[[13, 14, 15, 16, 17]], axis=0)
                bottom_lip = np.mean(pts[[308,312,317,402,318]], axis=0)
                abertura   = float(np.linalg.norm(top_lip - bottom_lip))
                centro     = np.mean(pts, axis=0)
                candidatos.append((centro, abertura))

            max_faces = max(len(c) for c in [candidatos] + list(activity_hist)) if activity_hist else len(candidatos)
            atual = [a for _, a in candidatos] + [0.0] * (max_faces - len(candidatos))
            activity_hist.append(atual)

            hist_array = np.array([h + [0.0]*(max_faces - len(h)) for h in activity_hist])
            medias = np.mean(hist_array, axis=0)
            idx = int(np.argmax(medias))
            if idx >= len(candidatos):
                # fallback para rosto mais próximo do centro horizontal
                idx = np.argmin([abs(c[0][0] - width//2) for c in candidatos])

            centro_atual = candidatos[idx][0]
        # else: mantém último falante (centro_atual)

        # suavização do corte
        centro_atual = centro_antigo + 0.12 * (np.array(centro_atual) - np.array(centro_antigo))
        centro_antigo = np.array(centro_atual)

        x, y = centro_atual
        x1 = max(0, min(int(x - crop_w/2), width - crop_w))
        y1 = max(0, min(int(y - crop_h/2), height - crop_h))
        crop = frame[y1:y1+crop_h, x1:x1+crop_w]
        out.write(crop)

        if i % 50 == 0: report(i)

    cap.release()
    out.release()

    # mux de áudio
    if progress_cb: progress_cb(stage="muxing", progress=0.0, meta={})
    _mux_audio(tmp_video, input_path, output_path)
    if progress_cb: progress_cb(stage="muxing", progress=1.0, meta={})

    try: os.remove(tmp_video)
    except: pass

    return {
        "frames_processed": total,
        "fps": float(fps),
        "faces_detected_sum": int(faces_detected_sum),
        "status": "success"
    }
