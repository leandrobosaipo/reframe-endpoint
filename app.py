# app.py
import os, io, time, json, uuid, queue, threading, tempfile, shutil
from urllib.parse import urlparse, unquote
import requests
from flask import Flask, request, jsonify, send_file
from reframe_mediapipe_falante_v7 import reframe_video
from storage.spaces import upload_public, make_key

# Carrega variáveis de ambiente do .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# -------- Config --------
MAX_WORKERS   = int(os.getenv("MAX_WORKERS", "2"))   # quantos vídeos processar em paralelo
OUTPUT_PREFIX = os.getenv("OUTPUT_PREFIX", "reframes")  # subpasta no Spaces

app = Flask(__name__)

# Memória da fila/estado (gravamos um snapshot em /tmp pra facilitar depuração)
_jobs = {}
_jobs_lock = threading.Lock()
_q = queue.Queue()

def _now():
    return int(time.time())

# pesos dos estágios para % (aprox.)
STAGE_WEIGHTS = {
    "queued":       0.0,
    "downloading":  0.05,
    "reframing":    0.80,
    "muxing":       0.05,
    "uploading":    0.10
}

def _progress_for(job):
    stage = job.get("stage","queued")
    stage_prog = job.get("stage_progress", 0.0)
    done_before = 0.0
    for k,v in STAGE_WEIGHTS.items():
        if k == stage: break
        done_before += v
    return round(100.0 * (done_before + STAGE_WEIGHTS.get(stage,0.0)*max(0.0,min(1.0,stage_prog))), 1)

def _save_job(job_id):
    # snapshot em disco p/ auditoria simples
    try:
        p = f"/tmp/job_{job_id}.json"
        with open(p,"w") as f:
            json.dump(_jobs[job_id], f, ensure_ascii=False, indent=2)
    except:
        pass

def _set(job_id, **kw):
    with _jobs_lock:
        _jobs[job_id].update(kw)
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

def _worker():
    while True:
        job_id = _q.get()
        if job_id is None:  # sentinela para encerrar
            break
        try:
            job = _jobs[job_id]
            _set(job_id, stage="downloading", stage_progress=0.0, started_at=_now())

            # 1) download (ou caminho local)
            in_path = _download_to_tmp(job["input_url"])
            _set(job_id, stage="downloading", stage_progress=1.0)

            # 2) reframe (com callback p/ progresso)
            tmp_out = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
            def progress_cb(stage, progress, meta):
                if stage == "reframing":
                    _set(job_id, stage="reframing", stage_progress=float(progress), meta=meta)
                elif stage == "muxing":
                    _set(job_id, stage="muxing", stage_progress=float(progress))

            metrics = reframe_video(in_path, tmp_out, progress_cb=progress_cb)

            # 3) upload ao Spaces (ou salvar localmente se falhar)
            _set(job_id, stage="uploading", stage_progress=0.0)
            try:
                key = make_key(OUTPUT_PREFIX, os.path.basename(tmp_out))
                url = upload_public(tmp_out, key)
                _set(job_id, stage="uploading", stage_progress=1.0)
            except Exception as upload_error:
                # Se upload falhar, salva localmente
                local_output = f"/tmp/reframe_output_{job_id}.mp4"
                shutil.copy2(tmp_out, local_output)
                _set(job_id, stage="uploading", stage_progress=1.0, 
                     upload_error=str(upload_error), local_output=local_output)
                url = f"file://{local_output}"
                key = f"local_{job_id}"

            # 4) finaliza
            _set(job_id,
                 status="done",
                 stage="done",
                 stage_progress=1.0,
                 finished_at=_now(),
                 output_key=key,
                 output_url=url,
                 metrics=metrics)

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
                except:
                    pass

        except Exception as e:
            _set(job_id, status="error", error=str(e), stage="error")
        finally:
            # limpa temporários se foram criados no download
            try:
                if 'in_path' in locals() and not job["input_url"].startswith("file://") and not os.path.exists(job["input_url"]):
                    if os.path.isfile(in_path) and os.path.dirname(in_path).startswith("/var/folders/"):
                        os.remove(in_path)
            except: pass

            try:
                if 'tmp_out' in locals() and os.path.isfile(tmp_out):
                    os.remove(tmp_out)
            except: pass

            _q.task_done()

# inicia os workers
_workers = []
for _ in range(MAX_WORKERS):
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    _workers.append(t)

@app.route("/")
def root():
    return jsonify({"service": "reframe-endpoint", "queue_size": _q.qsize(), "workers": len(_workers)})

@app.route("/v1/video/reframe", methods=["POST"])
def enqueue_reframe():
    data = request.get_json(force=True, silent=True) or {}
    input_url = data.get("input_url")
    input_path = data.get("input_path")  # novo: permite caminho local puro
    callback_url = data.get("callback_url")

    # Se veio input_path, converte automaticamente para file://
    if not input_url and input_path:
        p = os.path.abspath(os.path.expanduser(input_path.strip()))
        input_url = f"file://{p}"

    if not input_url:
        return jsonify({
            "status": "error",
            "message": "Envie 'input_url' (http/https/file) ou 'input_path' (caminho local)."
        }), 400

    job_id = f"job_{uuid.uuid4().hex[:10]}"
    with _jobs_lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "created_at": _now(),
            "status": "queued",
            "stage":  "queued",
            "stage_progress": 0.0,
            "progress": 0.0,
            "input_url": input_url,
            "callback_url": callback_url
        }
    _save_job(job_id)
    _q.put(job_id)

    return jsonify({
        "status": "queued",
        "message": "processamento enfileirado",
        "job_id": job_id
    }), 202

@app.route("/v1/video/jobs", methods=["GET"])
def list_jobs():
    """
    Lista todos os trabalhos com filtros opcionais por status.
    Query params: ?status=queued|downloading|reframing|muxing|uploading|done|error
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
    
    return jsonify({
        "jobs": jobs_list,
        "total": len(jobs_list),
        "queue_size": _q.qsize(),
        "active_workers": len(_workers)
    })

@app.route("/v1/video/status/<job_id>", methods=["GET"])
def status(job_id):
    job = _jobs.get(job_id)
    if not job:
        # tenta ler snapshot
        snap = f"/tmp/job_{job_id}.json"
        if os.path.exists(snap):
            with open(snap) as f:
                job = json.load(f)
                _jobs[job_id] = job
        else:
            return jsonify({"error": "job não encontrado"}), 404

    # ETA simples (estimativa) com base no tempo e progresso
    eta = None
    if job.get("progress") and job.get("started_at"):
        elapsed = max(1, _now() - job["started_at"])
        pct = max(1e-3, job["progress"]/100.0)
        total_est = elapsed / pct
        eta = int(total_est - elapsed)

    job_view = dict(job)
    job_view["eta_seconds"] = eta
    return jsonify(job_view)

@app.route("/v1/video/download/<job_id>", methods=["GET"])
def download_video(job_id):
    """
    Baixa o arquivo de vídeo processado.
    """
    job = _jobs.get(job_id)
    if not job:
        # tenta ler snapshot
        snap = f"/tmp/job_{job_id}.json"
        if os.path.exists(snap):
            with open(snap) as f:
                job = json.load(f)
                _jobs[job_id] = job
        else:
            return jsonify({"error": "job não encontrado"}), 404
    
    if job.get("status") != "done":
        return jsonify({"error": "job ainda não foi concluído"}), 400
    
    # Verifica se tem arquivo local
    local_output = job.get("local_output")
    if local_output and os.path.exists(local_output):
        return send_file(local_output, as_attachment=True, 
                        download_name=f"reframe_{job_id}.mp4")
    
    # Se não tem arquivo local, retorna URL do Spaces
    output_url = job.get("output_url")
    if output_url:
        return jsonify({
            "download_url": output_url,
            "message": "Arquivo disponível no DigitalOcean Spaces"
        })
    
    return jsonify({"error": "arquivo de saída não encontrado"}), 404

@app.route("/v1/test/upload", methods=["POST"])
def test_upload():
    """
    Endpoint para testar upload diretamente.
    """
    try:
        # Cria um arquivo de teste
        test_content = b"teste de upload"
        test_file = "/tmp/test_upload.txt"
        with open(test_file, "wb") as f:
            f.write(test_content)
        
        # Tenta fazer upload
        from storage.spaces import upload_public, make_key
        key = make_key("test", "test_upload.txt")
        url = upload_public(test_file, key)
        
        # Remove arquivo de teste
        os.remove(test_file)
        
        return jsonify({
            "status": "success",
            "message": "Upload funcionando!",
            "url": url,
            "key": key
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == "__main__":
    # Porta 8080 para bater com EasyPanel/Nixpacks
    app.run(host="0.0.0.0", port=8080)
