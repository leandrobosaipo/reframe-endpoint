# app.py
import os, io, time, json, uuid, queue, threading, tempfile, shutil
from urllib.parse import urlparse, unquote
import requests
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from flasgger import Swagger
from reframe_mediapipe_falante_v7 import reframe_video
from storage.spaces import upload_public, make_key, delete_public
from config import Config
from utils.response import success_response, error_response, queued_response

app = Flask(__name__)

# Configuração CORS para permitir requisições do navegador
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     supports_credentials=True,
     expose_headers=["Content-Type", "X-Upload-ID"],
     allow_headers=["Content-Type", "X-Api-Token", "X-Requested-With", "Accept"])

# Configuração Swagger/OpenAPI
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/openapi.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}

# Configura o host/base URL do Swagger
# Prioriza PUBLIC_BASE_URL se definido (para deploy em Easypanel/VPS)
# Caso contrário, usa comportamento padrão (localhost)
if Config.PUBLIC_BASE_URL:
    # Usa URL pública configurada (ex: https://apis-reframe-endpoint.mhcqvd.easypanel.host)
    parsed_url = urlparse(Config.PUBLIC_BASE_URL)
    swagger_host = parsed_url.netloc  # Remove http:// ou https://
    swagger_schemes = [parsed_url.scheme] if parsed_url.scheme else ["https"]
    swagger_base_path = parsed_url.path if parsed_url.path else "/"
else:
    # Comportamento padrão para desenvolvimento local
    _swagger_host = Config.HOST
    if _swagger_host == "0.0.0.0":
        _swagger_host = "127.0.0.1"
    swagger_host = f"{_swagger_host}:{Config.PORT}"
    swagger_schemes = ["http", "https"]
    swagger_base_path = "/"

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Reframe Endpoint API",
        "description": "API para reenquadramento de vídeos de 16:9 para 9:16 com foco automático no falante",
        "version": Config.APP_VERSION,
        "contact": {
            "name": "API Support"
        }
    },
    "host": swagger_host,
    "basePath": swagger_base_path,
    "schemes": swagger_schemes,
    "securityDefinitions": {
        "ApiTokenAuth": {
            "type": "apiKey",
            "name": "X-Api-Token",
            "in": "header"
        }
    },
    "security": [
        {
            "ApiTokenAuth": []
        }
    ]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# -------- Autenticação --------
@app.before_request
def verificar_token():
    """Verifica token de autenticação antes de cada request"""
    # Pula verificação para endpoints públicos e OPTIONS (preflight CORS)
    if request.method == 'OPTIONS':
        return
    public_endpoints = ['root', 'get_swagger_ui', 'get_apispec_json', 'metrics_health']
    if request.endpoint in public_endpoints:
        return
    
    # Se não há token configurado, pula verificação
    if not Config.API_TOKEN:
        return
    
    # Verifica token no header
    token = request.headers.get('X-Api-Token')
    if token != Config.API_TOKEN:
        abort(401, description="Token de autenticação inválido ou ausente")

# Memória da fila/estado (gravamos um snapshot em /tmp pra facilitar depuração)
_jobs = {}
_jobs_lock = threading.Lock()
_q = queue.Queue()

# Memória dos uploads (com retenção de 7 dias)
_uploads = {}
_uploads_lock = threading.Lock()

def _now() -> int:
    """Retorna timestamp atual em segundos"""
    return int(time.time())

# Usa pesos dos estágios da configuração centralizada
STAGE_WEIGHTS = Config.STAGE_WEIGHTS

def _progress_for(job: dict) -> float:
    """Calcula progresso percentual do job baseado no estágio atual"""
    stage = job.get("stage", "queued")
    stage_prog = job.get("stage_progress", 0.0)
    done_before = 0.0
    for k, v in STAGE_WEIGHTS.items():
        if k == stage: 
            break
        done_before += v
    return round(100.0 * (done_before + STAGE_WEIGHTS.get(stage, 0.0) * max(0.0, min(1.0, stage_prog))), 1)

def _save_job(job_id: str) -> None:
    """Salva snapshot do job em disco para auditoria"""
    try:
        p = os.path.join(Config.JOBS_SNAPSHOT_DIR, f"job_{job_id}.json")
        with open(p, "w") as f:
            json.dump(_jobs[job_id], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _save_uploads() -> None:
    """Salva snapshot de todos os uploads em disco"""
    try:
        p = os.path.join(Config.UPLOADS_SNAPSHOT_DIR, "uploads.json")
        with _uploads_lock:
            with open(p, "w") as f:
                json.dump(list(_uploads.values()), f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _load_uploads() -> None:
    """Carrega uploads do snapshot em disco"""
    try:
        p = os.path.join(Config.UPLOADS_SNAPSHOT_DIR, "uploads.json")
        if os.path.exists(p):
            with open(p) as f:
                uploads_list = json.load(f)
                with _uploads_lock:
                    for upload in uploads_list:
                        _uploads[upload.get("upload_id")] = upload
    except Exception:
        pass

def _cleanup_expired_uploads() -> None:
    """Remove uploads expirados do Spaces e da memória"""
    now = _now()
    expired_ids = []
    
    with _uploads_lock:
        for upload_id, upload in list(_uploads.items()):
            expires_at = upload.get("expires_at")
            if expires_at and now >= expires_at:
                expired_ids.append(upload_id)
                key = upload.get("key")
                if key:
                    delete_public(key)
    
    # Remove da memória
    with _uploads_lock:
        for upload_id in expired_ids:
            _uploads.pop(upload_id, None)
    
    if expired_ids:
        _save_uploads()

def _set(job_id: str, **kwargs) -> None:
    """Atualiza dados do job e recalcula progresso"""
    with _jobs_lock:
        _jobs[job_id].update(kwargs)
        _jobs[job_id]["progress"] = _progress_for(_jobs[job_id])
    _save_job(job_id)


def _download_to_tmp(input_url: str) -> str:
    """
    Suporta:
      • http(s)://...  -> baixa para /tmp
      • file:///abs/path ou file://localhost/abs/path -> usa caminho local
      • caminho puro (/Users/... ou ./video.mp4)      -> também aceita (converte internamente)
    Sempre retorna um caminho local legível.
    """
    if not input_url:
        raise ValueError("input_url vazio")

    u = urlparse(input_url)

    # -------- 1) http(s) -> download --------
    if u.scheme in ("http", "https"):
        try:
            r = requests.get(input_url, stream=True, timeout=60)
            r.raise_for_status()
        except Exception as e:
            raise ValueError(f"Falha ao baixar URL remota: {e}") from e

        ext = os.path.splitext(u.path)[1] or ".mp4"
        fd, tmp_path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
        return tmp_path

    # -------- 2) file:// -> caminho local --------
    if u.scheme == "file" or input_url.startswith("file:"):
        if u.netloc not in ("", "localhost", "127.0.0.1"):
            raise ValueError("file:// só é suportado para caminhos locais (host vazio/localhost).")

        # file:///Users/...  ou file://localhost/Users/...
        local_path = unquote(u.path or "")
        if not local_path:
            local_path = input_url.replace("file://", "").replace("file:", "")
        local_path = os.path.expanduser(local_path.strip())
        if not os.path.isabs(local_path):
            local_path = "/" + local_path if not local_path.startswith("/") else local_path

        candidates = [local_path, os.path.realpath(local_path)]
        for c in candidates:
            if os.path.exists(c) and os.access(c, os.R_OK):
                return c
        raise FileNotFoundError(f"Arquivo local não encontrado: {local_path}")

    # -------- 3) Sem esquema -> trate como caminho local puro --------
    local_path = os.path.abspath(os.path.expanduser(unquote(input_url).strip()))
    candidates = [local_path, os.path.realpath(local_path)]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.R_OK):
            return c

    raise FileNotFoundError(
        f"Caminho local não encontrado: {local_path} "
        f"(se for remoto, use http(s)://; se for file URL, use file:///caminho/absoluto)"
    )

def _worker() -> None:
    """Worker thread que processa jobs da fila"""
    while True:
        job_id = _q.get()
        if job_id is None:  # sentinela para encerrar
            break
        
        in_path = None
        tmp_out = None
        
        try:
            job = _jobs[job_id]
            _set(job_id, stage="downloading", stage_progress=0.0, started_at=_now())

            # 1) download (ou caminho local)
            in_path = _download_to_tmp(job["input_url"])
            _set(job_id, stage="downloading", stage_progress=1.0)

            # 2) reframe (com callback p/ progresso)
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                tmp_out = tmp_file.name
            
            def progress_cb(stage: str, progress: float, meta: dict = None) -> None:
                """Callback para atualizar progresso do reframe"""
                if stage == "reframing":
                    _set(job_id, stage="reframing", stage_progress=float(progress), meta=meta)
                elif stage == "muxing":
                    _set(job_id, stage="muxing", stage_progress=float(progress))

            debug_mode = job.get("debug", False)
            debug_output_path = None
            if debug_mode:
                debug_output_path = os.path.join(Config.TMP_DIR, f"debug_{job_id}.mp4")
            
            metrics = reframe_video(in_path, tmp_out, progress_cb=progress_cb, debug=debug_mode, debug_output=debug_output_path)

            # 3) upload ao Spaces (ou salvar localmente se falhar)
            _set(job_id, stage="uploading", stage_progress=0.0)
            try:
                key = make_key(Config.OUTPUT_PREFIX, os.path.basename(tmp_out))
                url = upload_public(tmp_out, key)
                _set(job_id, stage="uploading", stage_progress=1.0)
            except Exception as upload_error:
                # Se upload falhar, salva localmente
                local_output = os.path.join(Config.TMP_DIR, f"reframe_output_{job_id}.mp4")
                shutil.copy2(tmp_out, local_output)
                _set(job_id, stage="uploading", stage_progress=1.0, 
                     upload_error=str(upload_error), local_output=local_output)
                url = f"file://{local_output}"
                key = f"local_{job_id}"

            # 4) finaliza
            job_update = {
                "status": "done",
                "stage": "done",
                "stage_progress": 1.0,
                "finished_at": _now(),
                "output_key": key,
                "output_url": url,
                "metrics": metrics
            }
            
            # Se debug foi ativado e arquivo existe, adiciona ao job
            if debug_mode and debug_output_path and os.path.exists(debug_output_path):
                job_update["debug_output_local"] = debug_output_path
            
            _set(job_id, **job_update)

            # callback opcional
            cb = job.get("callback_url")
            if cb:
                try:
                    requests.post(cb, json={
                        "status": "done",
                        "job_id": job_id,
                        "output_url": url,
                        "output_key": key,
                        "metrics": metrics
                    }, timeout=10)
                except Exception:
                    pass

        except Exception as e:
            _set(job_id, status="error", error=str(e), stage="error")
        finally:
            # Limpa arquivos temporários usando context managers
            try:
                if in_path and not job["input_url"].startswith("file://") and not os.path.exists(job["input_url"]):
                    if os.path.isfile(in_path) and os.path.dirname(in_path).startswith("/var/folders/"):
                        os.remove(in_path)
            except Exception:
                pass

            try:
                if tmp_out and os.path.isfile(tmp_out):
                    os.remove(tmp_out)
            except Exception:
                pass

            _q.task_done()

# Carrega uploads do snapshot ao iniciar
_load_uploads()

# Worker para limpeza periódica de uploads expirados
def _cleanup_worker():
    """Worker que limpa uploads expirados periodicamente"""
    while True:
        time.sleep(3600)  # Executa a cada hora
        _cleanup_expired_uploads()

_cleanup_thread = threading.Thread(target=_cleanup_worker, daemon=True)
_cleanup_thread.start()

# inicia os workers
_workers = []
for _ in range(Config.MAX_WORKERS):
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    _workers.append(t)

@app.route("/")
def root() -> tuple:
    """
    Health check endpoint
    ---
    tags:
      - Health
    responses:
      200:
        description: Status do serviço
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: Service is running
            data:
              type: object
              properties:
                service:
                  type: string
                  example: reframe-endpoint
                queue_size:
                  type: integer
                  example: 0
                workers:
                  type: integer
                  example: 2
            build:
              type: object
    """
    return success_response(
        data={
            "service": Config.APP_NAME,
        "queue_size": _q.qsize(), 
            "workers": len(_workers)
        },
        message="Service is running"
    )

@app.route("/v1/video/reframe", methods=["POST"])
def enqueue_reframe() -> tuple:
    """
    Enfileira um vídeo para reframe
    ---
    tags:
      - Video
    security:
      - ApiTokenAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            input_url:
              type: string
              description: URL do vídeo (http/https/file) ou caminho local
              example: "file:///path/to/video.mp4"
            input_path:
              type: string
              description: Caminho local alternativo (se não usar input_url)
              example: "/path/to/video.mp4"
            input_upload_id:
              type: string
              description: ID do upload realizado via /v1/uploads (alternativa a input_url)
              example: "upl_abc123def4"
            callback_url:
              type: string
              description: URL opcional para callback quando concluído
              example: "https://example.com/callback"
            debug:
              type: boolean
              description: Ativa modo debug para gerar vídeo com overlays
              default: false
    responses:
      202:
        description: Job enfileirado com sucesso
        schema:
          type: object
          properties:
            status:
              type: string
              example: queued
            message:
              type: string
              example: processamento enfileirado
            job_id:
              type: string
              example: job_abc123def4
            build:
              type: object
        examples:
          application/json:
            status: queued
            message: processamento enfileirado
            job_id: job_abc123def4
            build:
              version: 1.0.0
              build_number: dev
              app_name: reframe-endpoint
      400:
        description: Dados inválidos
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: Envie 'input_url' (http/https/file) ou 'input_path' (caminho local).
            build:
              type: object
        examples:
          application/json:
            status: error
            message: Envie 'input_url' (http/https/file) ou 'input_path' (caminho local).
            build:
              version: 1.0.0
              build_number: dev
              app_name: reframe-endpoint
    """
    data = request.get_json(force=True, silent=True) or {}
    input_url = data.get("input_url")
    input_path = data.get("input_path")  # novo: permite caminho local puro
    input_upload_id = data.get("input_upload_id")  # novo: permite usar upload_id
    callback_url = data.get("callback_url")
    debug = data.get("debug", False)  # modo debug para gerar vídeo com overlays

    # Se veio input_upload_id, busca a URL do upload
    if input_upload_id:
        upload = _uploads.get(input_upload_id)
        if not upload:
            return error_response(
                message=f"Upload não encontrado: {input_upload_id}",
                status_code=404
            )
        input_url = upload.get("upload_url")
    
    # Se veio input_path, converte automaticamente para file://
    if not input_url and input_path:
        p = os.path.abspath(os.path.expanduser(input_path.strip()))
        input_url = f"file://{p}"

    if not input_url:
        return error_response(
            message="Envie 'input_url' (http/https/file), 'input_path' (caminho local) ou 'input_upload_id' (ID do upload).",
            status_code=400
        )

    job_id = f"job_{uuid.uuid4().hex[:10]}"
    with _jobs_lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "created_at": _now(),
            "status": "queued",
            "stage": "queued",
            "stage_progress": 0.0,
            "progress": 0.0,
            "input_url": input_url,
            "callback_url": callback_url,
            "debug": bool(debug)
        }
    _save_job(job_id)
    _q.put(job_id)

    return queued_response(
        message="processamento enfileirado",
        job_id=job_id
    )

@app.route("/v1/video/jobs", methods=["GET"])
def list_jobs():
    """
    Lista todos os trabalhos com filtros opcionais por status
    ---
    tags:
      - Video
    security:
      - ApiTokenAuth: []
    parameters:
      - in: query
        name: status
        type: string
        enum: [queued, downloading, reframing, muxing, uploading, done, error]
        description: Filtro opcional por status
      - in: query
        name: limit
        type: integer
        default: 50
        description: Limite de resultados
    responses:
      200:
        description: Lista de jobs
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            data:
              type: object
              properties:
                jobs:
                  type: array
                total:
                  type: integer
                queue_size:
                  type: integer
                active_workers:
                  type: integer
    """
    status_filter = request.args.get("status")
    limit = int(request.args.get("limit", "50"))
    
    with _jobs_lock:
        jobs_list = []
        for job_id, job in _jobs.items():
            # Aplica filtro de status se especificado
            if status_filter and job.get("status") != status_filter:
                continue
            
            # Calcula ETA se aplicável
            eta = None
            if job.get("progress") and job.get("started_at"):
                elapsed = max(1, _now() - job["started_at"])
                pct = max(1e-3, job["progress"]/100.0)
                total_est = elapsed / pct
                eta = int(total_est - elapsed)
            
            job_view = dict(job)
            job_view["eta_seconds"] = eta
            jobs_list.append(job_view)
    
    # Ordena por data de criação (mais recentes primeiro)
    jobs_list.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    
    # Aplica limite
    jobs_list = jobs_list[:limit]
    
    return success_response(
        data={
        "jobs": jobs_list,
        "total": len(jobs_list),
        "queue_size": _q.qsize(),
        "active_workers": len(_workers)
        },
        message="Jobs retrieved successfully"
    )

@app.route("/v1/video/status/<job_id>", methods=["GET"])
def status(job_id):
    """
    Obtém status de um job específico
    ---
    tags:
      - Video
    security:
      - ApiTokenAuth: []
    parameters:
      - in: path
        name: job_id
        type: string
        required: true
        description: ID do job
    responses:
      200:
        description: Status do job
        schema:
          type: object
      404:
        description: Job não encontrado
    """
    job = _jobs.get(job_id)
    if not job:
        # tenta ler snapshot
        snap = os.path.join(Config.JOBS_SNAPSHOT_DIR, f"job_{job_id}.json")
        if os.path.exists(snap):
            with open(snap) as f:
                job = json.load(f)
                _jobs[job_id] = job
        else:
            return error_response(
                message="job não encontrado",
                status_code=404
            )

    # ETA simples (estimativa) com base no tempo e progresso
    eta = None
    if job.get("progress") and job.get("started_at"):
        elapsed = max(1, _now() - job["started_at"])
        pct = max(1e-3, job["progress"]/100.0)
        total_est = elapsed / pct
        eta = int(total_est - elapsed)

    job_view = dict(job)
    job_view["eta_seconds"] = eta
    return success_response(
        data=job_view,
        message="Job status retrieved"
    )

@app.route("/v1/video/download/<job_id>", methods=["GET"])
def download_video(job_id):
    """
    Baixa o arquivo de vídeo processado
    ---
    tags:
      - Video
    security:
      - ApiTokenAuth: []
    parameters:
      - in: path
        name: job_id
        type: string
        required: true
        description: ID do job
    responses:
      200:
        description: Arquivo de vídeo ou URL de download
      400:
        description: Job ainda não foi concluído
      404:
        description: Job ou arquivo não encontrado
    """
    job = _jobs.get(job_id)
    if not job:
        # tenta ler snapshot
        snap = os.path.join(Config.JOBS_SNAPSHOT_DIR, f"job_{job_id}.json")
        if os.path.exists(snap):
            with open(snap) as f:
                job = json.load(f)
                _jobs[job_id] = job
        else:
            return error_response(
                message="job não encontrado",
                status_code=404
            )
    
    if job.get("status") != "done":
        return error_response(
            message="job ainda não foi concluído",
            status_code=400
        )
    
    # Verifica se tem arquivo local
    local_output = job.get("local_output")
    if local_output and os.path.exists(local_output):
        return send_file(local_output, as_attachment=True, 
                        download_name=f"reframe_{job_id}.mp4")
    
    # Se não tem arquivo local, retorna URL do Spaces
    output_url = job.get("output_url")
    if output_url:
        return success_response(
            data={
            "download_url": output_url,
            "message": "Arquivo disponível no DigitalOcean Spaces"
            },
            message="Download URL retrieved"
        )
    
    return error_response(
        message="arquivo de saída não encontrado",
        status_code=404
    )

@app.route("/v1/video/debug/<job_id>", methods=["GET"])
def download_debug_video(job_id):
    """
    Baixa o arquivo de vídeo debug (se disponível)
    ---
    tags:
      - Video
    security:
      - ApiTokenAuth: []
    parameters:
      - in: path
        name: job_id
        type: string
        required: true
        description: ID do job
    responses:
      200:
        description: Arquivo de vídeo debug
      400:
        description: Job ainda não foi concluído
      404:
        description: Job ou vídeo debug não encontrado
    """
    job = _jobs.get(job_id)
    if not job:
        # tenta ler snapshot
        snap = os.path.join(Config.JOBS_SNAPSHOT_DIR, f"job_{job_id}.json")
        if os.path.exists(snap):
            with open(snap) as f:
                job = json.load(f)
                _jobs[job_id] = job
        else:
            return error_response(
                message="job não encontrado",
                status_code=404
            )
    
    if job.get("status") != "done":
        return error_response(
            message="job ainda não foi concluído",
            status_code=400
        )
    
    debug_output = job.get("debug_output_local")
    if debug_output and os.path.exists(debug_output):
        return send_file(debug_output, as_attachment=True, 
                        download_name=f"debug_{job_id}.mp4")
    
    return error_response(
        message="vídeo debug não disponível. Certifique-se de que o job foi processado com debug=true",
        status_code=404
    )

@app.route("/v1/test/upload", methods=["POST"])
def test_upload():
    """
    Endpoint para testar upload diretamente
    ---
    tags:
      - Test
    security:
      - ApiTokenAuth: []
    responses:
      200:
        description: Upload testado com sucesso
      500:
        description: Erro no upload
    """
    try:
        # Cria um arquivo de teste
        test_content = b"teste de upload"
        test_file = os.path.join(Config.TMP_DIR, "test_upload.txt")
        with open(test_file, "wb") as f:
            f.write(test_content)
        
        # Tenta fazer upload
        key = make_key("test", "test_upload.txt")
        url = upload_public(test_file, key)
        
        # Remove arquivo de teste
        os.remove(test_file)
        
        return success_response(
            data={
            "url": url,
            "key": key
            },
            message="Upload funcionando!"
        )
        
    except Exception as e:
        return error_response(
            message=str(e),
            status_code=500
        )

# Endpoints de Upload
@app.route("/v1/uploads", methods=["POST"])
def upload_file():
    """
    Faz upload de um arquivo para a CDN
    ---
    tags:
      - Uploads
    security:
      - ApiTokenAuth: []
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: Arquivo a ser enviado
      - in: formData
        name: folder
        type: string
        required: false
        description: "Pasta de destino (padrão: upload/reframe)"
      - in: formData
        name: ttl_days
        type: integer
        required: false
        description: "Dias até expiração (padrão: 7, máximo: 30)"
    responses:
      200:
        description: Upload realizado com sucesso
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: Upload realizado com sucesso
            data:
              type: object
              properties:
                upload_id:
                  type: string
                  example: upl_b7e12b661e
                upload_url:
                  type: string
                  example: https://cod5.nyc3.digitaloceanspaces.com/upload/reframe/2025/11/12/abc123.mp4
                key:
                  type: string
                  example: upload/reframe/2025/11/12/abc123.mp4
                folder:
                  type: string
                  example: upload/reframe
                expires_at:
                  type: integer
                  example: 1763580531
            build:
              type: object
        examples:
          application/json:
            status: success
            message: Upload realizado com sucesso
            data:
              upload_id: upl_b7e12b661e
              upload_url: https://cod5.nyc3.digitaloceanspaces.com/upload/reframe/2025/11/12/abc123.mp4
              key: upload/reframe/2025/11/12/abc123.mp4
              folder: upload/reframe
              expires_at: 1763580531
            build:
              version: 1.0.0
              build_number: dev
              app_name: reframe-endpoint
      400:
        description: Erro na requisição
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: Nenhum arquivo enviado. Use o campo 'file' no form-data.
            build:
              type: object
    """
    if 'file' not in request.files:
        return error_response(
            message="Nenhum arquivo enviado. Use o campo 'file' no form-data.",
            status_code=400
        )
    
    file = request.files['file']
    if file.filename == '':
        return error_response(
            message="Nome do arquivo vazio",
            status_code=400
        )
    
    # Parâmetros opcionais
    folder = request.form.get('folder', Config.UPLOAD_DEFAULT_FOLDER).strip()
    ttl_days = int(request.form.get('ttl_days', Config.UPLOAD_TTL_DAYS))
    
    # Valida TTL máximo
    if ttl_days > Config.UPLOAD_MAX_TTL_DAYS:
        ttl_days = Config.UPLOAD_MAX_TTL_DAYS
    if ttl_days < 1:
        ttl_days = Config.UPLOAD_TTL_DAYS
    
    # Valida nome da pasta (evita path traversal)
    if '..' in folder or '/' not in folder:
        folder = Config.UPLOAD_DEFAULT_FOLDER
    
    try:
        # Salva arquivo temporariamente
        ext = os.path.splitext(file.filename)[1] or ""
        fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=Config.TMP_DIR)
        with os.fdopen(fd, "wb") as f:
            file.save(f)
        
        # Faz upload para Spaces
        key = make_key(folder, file.filename)
        url = upload_public(tmp_path, key)
        
        # Remove arquivo temporário
        os.remove(tmp_path)
        
        # Cria registro do upload
        upload_id = f"upl_{uuid.uuid4().hex[:10]}"
        created_at = _now()
        expires_at = created_at + (ttl_days * 86400)
        
        upload_record = {
            "upload_id": upload_id,
            "key": key,
            "upload_url": url,
            "folder": folder,
            "filename": file.filename,
            "created_at": created_at,
            "expires_at": expires_at,
            "ttl_days": ttl_days
        }
        
        with _uploads_lock:
            _uploads[upload_id] = upload_record
        
        _save_uploads()
        
        return success_response(
            data={
                "upload_id": upload_id,
                "upload_url": url,
                "key": key,
                "folder": folder,
                "expires_at": expires_at
            },
            message="Upload realizado com sucesso"
        )
        
    except Exception as e:
        return error_response(
            message=f"Erro ao fazer upload: {str(e)}",
            status_code=500
        )

@app.route("/v1/uploads", methods=["GET"])
def list_uploads():
    """
    Lista uploads realizados
    ---
    tags:
      - Uploads
    security:
      - ApiTokenAuth: []
    parameters:
      - in: query
        name: limit
        type: integer
        default: 20
        description: Limite de resultados
      - in: query
        name: folder
        type: string
        description: Filtro por pasta
      - in: query
        name: status
        type: string
        enum: [active, expired]
        description: Filtro por status
    responses:
      200:
        description: Lista de uploads
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: Uploads retrieved successfully
            data:
              type: object
              properties:
                uploads:
                  type: array
                  items:
                    type: object
                total:
                  type: integer
                  example: 1
            build:
              type: object
        examples:
          application/json:
            status: success
            message: Uploads retrieved successfully
            data:
              uploads:
                - upload_id: upl_b7e12b661e
                  upload_url: https://cod5.nyc3.digitaloceanspaces.com/upload/reframe/2025/11/12/abc123.mp4
                  key: upload/reframe/2025/11/12/abc123.mp4
                  folder: upload/reframe
                  filename: video.mp4
                  created_at: 1762975731
                  expires_at: 1763580531
                  ttl_days: 7
              total: 1
            build:
              version: 1.0.0
              build_number: dev
              app_name: reframe-endpoint
    """
    limit = int(request.args.get("limit", "20"))
    folder_filter = request.args.get("folder")
    status_filter = request.args.get("status")
    
    now = _now()
    
    with _uploads_lock:
        uploads_list = list(_uploads.values())
    
    # Filtra por pasta
    if folder_filter:
        uploads_list = [u for u in uploads_list if u.get("folder") == folder_filter]
    
    # Filtra por status
    if status_filter == "expired":
        uploads_list = [u for u in uploads_list if u.get("expires_at", 0) < now]
    elif status_filter == "active":
        uploads_list = [u for u in uploads_list if u.get("expires_at", 0) >= now]
    
    # Ordena por data de criação (mais recentes primeiro)
    uploads_list.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    
    # Aplica limite
    uploads_list = uploads_list[:limit]
    
    return success_response(
        data={
            "uploads": uploads_list,
            "total": len(uploads_list)
        },
        message="Uploads retrieved successfully"
    )

@app.route("/v1/uploads/<upload_id>", methods=["GET"])
def get_upload(upload_id):
    """
    Obtém detalhes de um upload específico
    ---
    tags:
      - Uploads
    security:
      - ApiTokenAuth: []
    parameters:
      - in: path
        name: upload_id
        type: string
        required: true
        description: ID do upload
    responses:
      200:
        description: Detalhes do upload
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: Upload details retrieved
            data:
              type: object
            build:
              type: object
        examples:
          application/json:
            status: success
            message: Upload details retrieved
            data:
              upload_id: upl_b7e12b661e
              upload_url: https://cod5.nyc3.digitaloceanspaces.com/upload/reframe/2025/11/12/abc123.mp4
              key: upload/reframe/2025/11/12/abc123.mp4
              folder: upload/reframe
              filename: video.mp4
              created_at: 1762975731
              expires_at: 1763580531
              ttl_days: 7
            build:
              version: 1.0.0
              build_number: dev
              app_name: reframe-endpoint
      404:
        description: Upload não encontrado
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: Upload não encontrado
            build:
              type: object
    """
    upload = _uploads.get(upload_id)
    if not upload:
        return error_response(
            message="Upload não encontrado",
            status_code=404
        )
    
    return success_response(
        data=upload,
        message="Upload details retrieved"
    )

@app.route("/v1/uploads/<upload_id>", methods=["DELETE"])
def delete_upload(upload_id):
    """
    Remove um upload manualmente
    ---
    tags:
      - Uploads
    security:
      - ApiTokenAuth: []
    parameters:
      - in: path
        name: upload_id
        type: string
        required: true
        description: ID do upload
    responses:
      200:
        description: Upload removido com sucesso
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: Upload removido com sucesso
            data:
              type: object
              properties:
                upload_id:
                  type: string
                  example: upl_b7e12b661e
            build:
              type: object
        examples:
          application/json:
            status: success
            message: Upload removido com sucesso
            data:
              upload_id: upl_b7e12b661e
            build:
              version: 1.0.0
              build_number: dev
              app_name: reframe-endpoint
      404:
        description: Upload não encontrado
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: Upload não encontrado
            build:
              type: object
    """
    upload = _uploads.get(upload_id)
    if not upload:
        return error_response(
            message="Upload não encontrado",
            status_code=404
        )
    
    # Remove do Spaces
    key = upload.get("key")
    if key:
        delete_public(key)
    
    # Remove da memória
    with _uploads_lock:
        _uploads.pop(upload_id, None)
    
    _save_uploads()
    
    return success_response(
        data={"upload_id": upload_id},
        message="Upload removido com sucesso"
    )

# Endpoints de Métricas
@app.route("/metrics/queue", methods=["GET"])
def metrics_queue():
    """
    Métricas da fila de processamento
    ---
    tags:
      - Metrics
    responses:
      200:
        description: Métricas da fila
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            data:
              type: object
              properties:
                queue_size:
                  type: integer
                active_workers:
                  type: integer
                max_workers:
                  type: integer
                jobs_in_queue:
                  type: array
            build:
              type: object
    """
    with _jobs_lock:
        queued_jobs = [j for j in _jobs.values() if j.get("status") == "queued"]
    
    return success_response(
        data={
            "queue_size": _q.qsize(),
            "active_workers": len(_workers),
            "max_workers": Config.MAX_WORKERS,
            "jobs_in_queue": [
                {
                    "job_id": j.get("job_id"),
                    "created_at": j.get("created_at"),
                    "input_url": j.get("input_url")
                }
                for j in queued_jobs
            ]
        },
        message="Queue metrics retrieved"
    )


@app.route("/metrics/history", methods=["GET"])
def metrics_history():
    """
    Histórico dos últimos jobs processados
    ---
    tags:
      - Metrics
    parameters:
      - in: query
        name: limit
        type: integer
        default: 20
        description: Número de jobs a retornar
      - in: query
        name: status
        type: string
        enum: [done, error]
        description: Filtro por status
    responses:
      200:
        description: Histórico de jobs
    """
    limit = int(request.args.get("limit", "20"))
    status_filter = request.args.get("status")
    
    with _jobs_lock:
        jobs_list = list(_jobs.values())
    
    # Filtra por status se especificado
    if status_filter:
        jobs_list = [j for j in jobs_list if j.get("status") == status_filter]
    
    # Ordena por data de criação (mais recentes primeiro)
    jobs_list.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    
    # Aplica limite
    jobs_list = jobs_list[:limit]
    
    return success_response(
        data={
            "jobs": jobs_list,
            "total": len(jobs_list)
        },
        message="History retrieved"
    )


@app.route("/metrics/kpi", methods=["GET"])
def metrics_kpi():
    """
    KPIs agregados do sistema
    ---
    tags:
      - Metrics
    responses:
      200:
        description: KPIs agregados
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: object
              properties:
                total_jobs:
                  type: integer
                jobs_by_status:
                  type: object
                jobs_by_stage:
                  type: object
                average_processing_time:
                  type: number
                success_rate:
                  type: number
            build:
              type: object
    """
    with _jobs_lock:
        jobs_list = list(_jobs.values())
    
    # Contadores por status
    status_counts = {}
    stage_counts = {}
    processing_times = []
    success_count = 0
    error_count = 0
    
    for job in jobs_list:
        status = job.get("status", "unknown")
        stage = job.get("stage", "unknown")
        
        status_counts[status] = status_counts.get(status, 0) + 1
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        if status == "done":
            success_count += 1
            if job.get("started_at") and job.get("finished_at"):
                processing_times.append(job["finished_at"] - job["started_at"])
        elif status == "error":
            error_count += 1
    
    # Calcula média de tempo de processamento
    avg_processing_time = None
    if processing_times:
        avg_processing_time = sum(processing_times) / len(processing_times)
    
    # Taxa de sucesso
    total_completed = success_count + error_count
    success_rate = None
    if total_completed > 0:
        success_rate = (success_count / total_completed) * 100
    
    return success_response(
        data={
            "total_jobs": len(jobs_list),
            "jobs_by_status": status_counts,
            "jobs_by_stage": stage_counts,
            "average_processing_time_seconds": avg_processing_time,
            "success_rate_percent": success_rate,
            "success_count": success_count,
            "error_count": error_count
        },
        message="KPIs retrieved"
    )


@app.route("/metrics/health", methods=["GET"])
def metrics_health():
    """
    Health check detalhado do servidor
    ---
    tags:
      - Metrics
    responses:
      200:
        description: Status de saúde do servidor
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            data:
              type: object
              properties:
                service:
                  type: string
                queue_size:
                  type: integer
                workers:
                  type: object
                storage:
                  type: object
                uptime_seconds:
                  type: integer
            build:
              type: object
    """
    # Verifica se workers estão vivos
    active_workers = sum(1 for w in _workers if w.is_alive())
    
    # Verifica storage (tenta criar arquivo temporário)
    storage_ok = True
    try:
        test_file = os.path.join(Config.TMP_DIR, f"health_check_{_now()}.tmp")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
    except Exception:
        storage_ok = False
    
    return success_response(
        data={
            "service": Config.APP_NAME,
            "queue_size": _q.qsize(),
            "workers": {
                "active": active_workers,
                "total": len(_workers),
                "max": Config.MAX_WORKERS,
                "all_alive": active_workers == len(_workers)
            },
            "storage": {
                "tmp_dir": Config.TMP_DIR,
                "accessible": storage_ok
            },
            "config": {
                "output_prefix": Config.OUTPUT_PREFIX,
                "spaces_bucket": Config.SPACES_BUCKET,
                "has_api_token": bool(Config.API_TOKEN)
            }
        },
        message="Health check completed"
    )


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT)
