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
DEAD_ZONE_THRESHOLD_X = 0.05  # 5% da largura do frame (aumentado para reduzir movimentos pequenos)
DEAD_ZONE_THRESHOLD_Y = 0.05  # 5% da altura do frame (aumentado para reduzir movimentos pequenos)
SMOOTH_ALPHA = 0.05  # Reduzido para suavização ainda mais lenta
CENTER_HISTORY_SIZE = 7  # Número de centros para média ponderada (aumentado para mais suavização)
CENTER_OFFSET_Y = 0.05  # Offset vertical para focar acima do nariz (5% da altura)

def _calculate_focused_center(landmarks, width, height):
    """
    Calcula centro focado acima do nariz usando landmarks específicos.
    Usa nariz e olhos para posicionar o centro mais alto, evitando seguir movimentos da boca.
    """
    pts = np.array([(lm.x * width, lm.y * height) for lm in landmarks.landmark])
    
    # Landmarks importantes: nariz (1), olhos (33, 263), centro da testa (10)
    nose_tip = pts[1]  # Ponta do nariz
    left_eye = pts[33]  # Olho esquerdo
    right_eye = pts[263]  # Olho direito
    
    # Calcula centro entre os olhos e nariz (mais estável que média de todos os pontos)
    eye_center = (left_eye + right_eye) / 2
    focused_center = (eye_center + nose_tip) / 2
    
    # Aplica offset vertical para focar acima do nariz
    focused_center[1] -= height * CENTER_OFFSET_Y
    
    return focused_center

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

def _adjust_bbox_for_head(x, y, w, h, height_frame):
    """
    Ajusta bounding box para focar apenas na cabeça, removendo área de ombros/mãos.
    Aplica offset vertical para focar acima do nariz (similar ao MediaPipe).
    Retorna (x_head, y_head, w_head, h_head, centro_x, centro_y)
    """
    # Reduz altura: remove parte inferior (ombros/mãos) - mantém apenas 60% superior
    h_head = int(h * 0.6)
    y_head = y + int(h * 0.1)  # Move um pouco para cima
    
    # Reduz largura: foca no centro da cabeça - mantém 50% central
    w_head = int(w * 0.5)
    x_head = x + int(w * 0.25)  # Centraliza
    
    # Calcula centro da região da cabeça
    centro_x = x_head + w_head // 2
    centro_y = y_head + h_head // 2
    
    # Aplica offset vertical para focar acima do nariz (consistente com MediaPipe)
    centro_y -= height_frame * CENTER_OFFSET_Y
    
    return (x_head, y_head, w_head, h_head, centro_x, centro_y)

def _detect_faces_haar(frame_gray, cascade_frontal, cascade_profile, height_frame):
    """
    Detecta rostos usando Haar Cascades como fallback.
    Retorna lista de tuplas (centro_x, centro_y, largura_cabeça, altura_cabeça, x_original, y_original, w_original, h_original).
    """
    faces = []
    
    # Detecta rostos frontais
    frontal_faces = cascade_frontal.detectMultiScale(
        frame_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )
    for (x, y, w, h) in frontal_faces:
        x_head, y_head, w_head, h_head, centro_x, centro_y = _adjust_bbox_for_head(x, y, w, h, height_frame)
        faces.append((centro_x, centro_y, w_head, h_head, x, y, w, h))
    
    # Detecta rostos de perfil
    profile_faces = cascade_profile.detectMultiScale(
        frame_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )
    for (x, y, w, h) in profile_faces:
        x_head, y_head, w_head, h_head, centro_x, centro_y = _adjust_bbox_for_head(x, y, w, h, height_frame)
        faces.append((centro_x, centro_y, w_head, h_head, x, y, w, h))
    
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

def _draw_debug_overlays(frame, results, haar_faces, centro_atual, centro_detectado, width, height, debug_info=None):
    """
    Desenha overlays de debug no frame: bounding boxes, centros, landmarks.
    """
    frame_debug = frame.copy()
    
    # Desenha bounding boxes do MediaPipe
    if results.multi_face_landmarks:
        for landmarks in results.multi_face_landmarks:
            pts = np.array([(lm.x * width, lm.y * height) for lm in landmarks.landmark])
            # Bounding box do MediaPipe
            x_min, y_min = int(pts[:, 0].min()), int(pts[:, 1].min())
            x_max, y_max = int(pts[:, 0].max()), int(pts[:, 1].max())
            cv2.rectangle(frame_debug, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            
            # Desenha alguns landmarks importantes
            # Olhos
            left_eye = pts[33]
            right_eye = pts[263]
            cv2.circle(frame_debug, (int(left_eye[0]), int(left_eye[1])), 3, (255, 0, 0), -1)
            cv2.circle(frame_debug, (int(right_eye[0]), int(right_eye[1])), 3, (255, 0, 0), -1)
            
            # Boca (pontos usados para detecção de fala)
            top_lip = np.mean(pts[[13, 14, 15, 16, 17]], axis=0)
            bottom_lip = np.mean(pts[[308,312,317,402,318]], axis=0)
            cv2.circle(frame_debug, (int(top_lip[0]), int(top_lip[1])), 3, (0, 0, 255), -1)
            cv2.circle(frame_debug, (int(bottom_lip[0]), int(bottom_lip[1])), 3, (0, 0, 255), -1)
    
    # Desenha bounding boxes do Haar Cascade
    for face_info in haar_faces:
        cx, cy, w_head, h_head, x_orig, y_orig, w_orig, h_orig = face_info
        # Bounding box original (verde claro)
        cv2.rectangle(frame_debug, (x_orig, y_orig), (x_orig + w_orig, y_orig + h_orig), (0, 255, 255), 2)
        # Bounding box ajustado para cabeça (azul)
        x_head = int(cx - w_head/2)
        y_head = int(cy - h_head/2)
        cv2.rectangle(frame_debug, (x_head, y_head), (x_head + w_head, y_head + h_head), (255, 0, 255), 2)
        # Centro da cabeça
        cv2.circle(frame_debug, (int(cx), int(cy)), 5, (255, 0, 255), -1)
    
    # Desenha centro atual (usado para corte)
    if centro_atual is not None:
        centro_atual_tuple = tuple(centro_atual) if isinstance(centro_atual, np.ndarray) else centro_atual
        cv2.circle(frame_debug, (int(centro_atual_tuple[0]), int(centro_atual_tuple[1])), 8, (0, 255, 255), 2)
        cv2.putText(frame_debug, "CENTER", (int(centro_atual_tuple[0]) + 10, int(centro_atual_tuple[1])), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    # Desenha centro detectado (antes da suavização)
    if centro_detectado is not None:
        centro_detectado_tuple = tuple(centro_detectado) if isinstance(centro_detectado, np.ndarray) else centro_detectado
        cv2.circle(frame_debug, (int(centro_detectado_tuple[0]), int(centro_detectado_tuple[1])), 5, (255, 255, 0), 2)
    
    # Informações de debug
    if debug_info:
        y_offset = 20
        for key, value in debug_info.items():
            cv2.putText(frame_debug, f"{key}: {value}", (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 20
    
    return frame_debug

def reframe_video(input_path: str,
                  output_path: str,
                  progress_cb=None,
                  debug=False,
                  debug_output=None) -> dict:
    """
    Reenquadra 16:9 -> 9:16 mantendo o falante principal.
    progress_cb(stage, progress, meta)  # progress: 0..1
    debug: se True, gera vídeo com overlays de debug
    debug_output: caminho para salvar vídeo debug (se debug=True)
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
    
    # VideoWriter para debug (vídeo completo com overlays)
    out_debug = None
    if debug and debug_output:
        out_debug = cv2.VideoWriter(debug_output, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

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
        
        # Variáveis para debug
        centro_detectado_debug = None
        haar_faces_debug = []

        candidatos = []
        if results.multi_face_landmarks:
            faces_detected_sum += len(results.multi_face_landmarks)
            for landmarks in results.multi_face_landmarks:
                pts = np.array([(lm.x * width, lm.y * height) for lm in landmarks.landmark])
                top_lip    = np.mean(pts[[13, 14, 15, 16, 17]], axis=0)
                bottom_lip = np.mean(pts[[308,312,317,402,318]], axis=0)
                abertura   = float(np.linalg.norm(top_lip - bottom_lip))
                # Usa centro focado acima do nariz em vez da média de todos os pontos
                centro     = _calculate_focused_center(landmarks, width, height)
                candidatos.append((centro, abertura))

            # Define centro_fallback no primeiro frame com rostos detectados
            if centro_fallback is None and candidatos:
                # Escolhe o rosto mais próximo do centro horizontal como fallback
                idx_fallback = np.argmin([abs(c[0][0] - width//2) for c in candidatos])
                centro_fallback_raw = candidatos[idx_fallback][0]
                # Aplica estabilização desde o primeiro frame
                centro_fallback_stable = _apply_dead_zone(centro_fallback_raw, centro_atual, width, height)
                centro_fallback_stable = _smooth_center(centro_fallback_stable, centro_history, width, height)
                centro_fallback = np.array(centro_fallback_stable)

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
            centro_detectado_debug = centro_detectado
            # Aplica zona morta para evitar movimentos pequenos
            centro_detectado = _apply_dead_zone(centro_detectado, centro_atual, width, height)
            # Aplica média ponderada dos últimos centros
            centro_detectado = _smooth_center(centro_detectado, centro_history, width, height)
            centro_atual = centro_detectado
        else:
            # Fallback: tenta detectar rostos usando Haar Cascades quando MediaPipe falha
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            haar_faces = _detect_faces_haar(frame_gray, cascade_frontal, cascade_profile, height)
            haar_faces_debug = haar_faces
            
            if haar_faces:
                faces_detected_sum += len(haar_faces)
                # Escolhe a melhor face focando na cabeça
                # Prioriza aspect ratio de cabeça (mais vertical) e tamanho consistente
                def score_face(face):
                    cx, cy, w_head, h_head, x_orig, y_orig, w_orig, h_orig = face
                    # Aspect ratio típico de cabeça (mais vertical = melhor)
                    aspect_ratio = h_head / max(w_head, 1)
                    aspect_score = aspect_ratio if aspect_ratio > 1.0 else 1.0 / aspect_ratio
                    # Tamanho da cabeça (prioriza tamanhos médios)
                    size_score = w_head * h_head
                    # Proximidade do centro
                    center_score = 1.0 / (1.0 + abs(cx - width//2) / width)
                    return size_score * aspect_score * (1.0 + center_score)
                
                melhor_face = max(haar_faces, key=score_face)
                centro_haar = (melhor_face[0], melhor_face[1])
                centro_detectado_debug = centro_haar
                
                # Define centro_fallback se ainda não foi definido (primeiro frame com cabeça)
                if centro_fallback is None:
                    # No primeiro frame, aplica estabilização desde o início
                    centro_haar_stable = _apply_dead_zone(centro_haar, centro_atual, width, height)
                    centro_haar_stable = _smooth_center(centro_haar_stable, centro_history, width, height)
                    centro_fallback = np.array(centro_haar_stable)
                    centro_atual = centro_haar_stable
                else:
                    # Aplica zona morta e suavização antes de usar o centro detectado pelo Haar
                    centro_haar = _apply_dead_zone(centro_haar, centro_atual, width, height)
                    centro_haar = _smooth_center(centro_haar, centro_history, width, height)
                    centro_atual = centro_haar
            elif centro_fallback is not None:
                # Quando não há rostos detectados por nenhum método, usa centro_fallback
                # MAS aplica zona morta e suavização para evitar balanço
                centro_fallback_tuple = tuple(centro_fallback)
                centro_fallback_tuple = _apply_dead_zone(centro_fallback_tuple, centro_atual, width, height)
                centro_fallback_tuple = _smooth_center(centro_fallback_tuple, centro_history, width, height)
                centro_atual = centro_fallback_tuple
            # Se não há fallback definido ainda, mantém centro_atual (que pode ser o centro da tela inicialmente)

        # suavização final do corte (interpolação exponencial)
        centro_atual = centro_antigo + SMOOTH_ALPHA * (np.array(centro_atual) - np.array(centro_antigo))
        centro_antigo = np.array(centro_atual)

        x, y = centro_atual
        x1 = max(0, min(int(x - crop_w/2), width - crop_w))
        y1 = max(0, min(int(y - crop_h/2), height - crop_h))
        crop = frame[y1:y1+crop_h, x1:x1+crop_w]
        out.write(crop)
        
        # Gera vídeo debug se solicitado
        if debug and out_debug:
            debug_info = {
                "Frame": i,
                "Method": "MediaPipe" if results.multi_face_landmarks else ("Haar" if haar_faces_debug else "Fallback"),
                "Faces": len(results.multi_face_landmarks) if results.multi_face_landmarks else len(haar_faces_debug)
            }
            frame_debug = _draw_debug_overlays(frame, results, haar_faces_debug, centro_atual, centro_detectado_debug, width, height, debug_info)
            out_debug.write(frame_debug)

        if i % 50 == 0: report(i)

    cap.release()
    out.release()
    if out_debug:
        out_debug.release()

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
