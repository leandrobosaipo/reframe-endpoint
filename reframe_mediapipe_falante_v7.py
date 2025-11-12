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

# Parâmetros de suavização configuráveis
DEAD_ZONE_THRESHOLD_X = 0.03  # 3% da largura do frame
DEAD_ZONE_THRESHOLD_Y = 0.03  # 3% da altura do frame
SMOOTH_ALPHA = 0.08  # Reduzido de 0.12 para suavização mais lenta
CENTER_HISTORY_SIZE = 5  # Número de centros para média ponderada

def _apply_dead_zone(centro_detectado, centro_atual, width, height):
    """
    Aplica zona morta: só retorna novo centro se a diferença exceder threshold.
    Retorna o centro a usar (pode ser o atual se dentro da zona morta).
    """
    dx = abs(centro_detectado[0] - centro_atual[0])
    dy = abs(centro_detectado[1] - centro_atual[1])
    
    threshold_x = width * DEAD_ZONE_THRESHOLD_X
    threshold_y = height * DEAD_ZONE_THRESHOLD_Y
    
    # Se a diferença for menor que o threshold, mantém o centro atual
    if dx < threshold_x and dy < threshold_y:
        return centro_atual
    
    return centro_detectado

def _smooth_center(centro_detectado, centro_history, width, height):
    """
    Aplica média ponderada dos últimos centros detectados.
    Centros mais recentes têm peso maior.
    Retorna o centro suavizado e o histórico atualizado.
    """
    # Adiciona o novo centro ao histórico
    centro_history.append(centro_detectado)
    
    if len(centro_history) == 1:
        return centro_detectado
    
    # Calcula média ponderada (centros mais recentes têm peso maior)
    total_weight = 0.0
    weighted_sum = np.array([0.0, 0.0])
    
    for i, centro in enumerate(centro_history):
        weight = (i + 1) / len(centro_history)  # Peso crescente
        total_weight += weight
        weighted_sum += np.array(centro) * weight
    
    centro_suavizado = weighted_sum / total_weight
    return tuple(centro_suavizado)

def _detect_faces_haar(frame_gray, cascade_frontal, cascade_profile):
    """
    Detecta rostos usando Haar Cascades como fallback.
    Retorna lista de tuplas (centro_x, centro_y, largura, altura).
    """
    faces = []
    
    # Detecta rostos frontais
    frontal_faces = cascade_frontal.detectMultiScale(
        frame_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )
    for (x, y, w, h) in frontal_faces:
        centro_x = x + w // 2
        centro_y = y + h // 2
        faces.append((centro_x, centro_y, w, h))
    
    # Detecta rostos de perfil
    profile_faces = cascade_profile.detectMultiScale(
        frame_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )
    for (x, y, w, h) in profile_faces:
        centro_x = x + w // 2
        centro_y = y + h // 2
        faces.append((centro_x, centro_y, w, h))
    
    return faces

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

    # Carrega Haar Cascades para fallback de detecção de rostos de perfil
    cascade_path = cv2.data.haarcascades
    cascade_frontal = cv2.CascadeClassifier(
        os.path.join(cascade_path, 'haarcascade_frontalface_default.xml')
    )
    cascade_profile = cv2.CascadeClassifier(
        os.path.join(cascade_path, 'haarcascade_profileface.xml')
    )

    # histórico para decidir falante
    activity_hist = deque(maxlen=15)
    centro_atual  = (width // 2, height // 2)
    centro_antigo = np.array(centro_atual)
    centro_fallback = None  # rosto inicial para fallback quando não há falante detectado
    centro_history = deque(maxlen=CENTER_HISTORY_SIZE)  # Histórico para suavização

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

            # Define centro_fallback no primeiro frame com rostos detectados
            if centro_fallback is None and candidatos:
                # Escolhe o rosto mais próximo do centro horizontal como fallback
                idx_fallback = np.argmin([abs(c[0][0] - width//2) for c in candidatos])
                centro_fallback = np.array(candidatos[idx_fallback][0])

            max_faces = max(len(c) for c in [candidatos] + list(activity_hist)) if activity_hist else len(candidatos)
            atual = [a for _, a in candidatos] + [0.0] * (max_faces - len(candidatos))
            activity_hist.append(atual)

            hist_array = np.array([h + [0.0]*(max_faces - len(h)) for h in activity_hist])
            medias = np.mean(hist_array, axis=0)
            idx = int(np.argmax(medias))
            if idx >= len(candidatos):
                # fallback para rosto mais próximo do centro horizontal
                idx = np.argmin([abs(c[0][0] - width//2) for c in candidatos])

            centro_detectado = candidatos[idx][0]
            # Aplica zona morta para evitar movimentos pequenos
            centro_detectado = _apply_dead_zone(centro_detectado, centro_atual, width, height)
            # Aplica média ponderada dos últimos centros
            centro_detectado = _smooth_center(centro_detectado, centro_history, width, height)
            centro_atual = centro_detectado
        else:
            # Fallback: tenta detectar rostos usando Haar Cascades quando MediaPipe falha
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            haar_faces = _detect_faces_haar(frame_gray, cascade_frontal, cascade_profile)
            
            if haar_faces:
                faces_detected_sum += len(haar_faces)
                # Escolhe a maior face ou a mais próxima do centro horizontal
                # Prioriza tamanho (largura * altura) e depois proximidade do centro
                def score_face(face):
                    cx, cy, w, h = face
                    size_score = w * h
                    center_score = 1.0 / (1.0 + abs(cx - width//2) / width)
                    return size_score * (1.0 + center_score)
                
                melhor_face = max(haar_faces, key=score_face)
                centro_haar = (melhor_face[0], melhor_face[1])
                
                # Define centro_fallback se ainda não foi definido
                if centro_fallback is None:
                    centro_fallback = np.array(centro_haar)
                
                # Aplica zona morta e suavização antes de usar o centro detectado pelo Haar
                centro_haar = _apply_dead_zone(centro_haar, centro_atual, width, height)
                centro_haar = _smooth_center(centro_haar, centro_history, width, height)
                centro_atual = centro_haar
            elif centro_fallback is not None:
                # Quando não há rostos detectados por nenhum método, usa centro_fallback
                centro_atual = tuple(centro_fallback)
            # Se não há fallback definido ainda, mantém centro_atual (que pode ser o centro da tela inicialmente)

        # suavização final do corte (interpolação exponencial)
        centro_atual = centro_antigo + SMOOTH_ALPHA * (np.array(centro_atual) - np.array(centro_antigo))
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
