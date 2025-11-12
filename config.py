"""
Configuração centralizada do projeto.
Carrega variáveis de ambiente e expõe configurações dinâmicas.
"""
import os
from datetime import datetime

# Carrega variáveis de ambiente do .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """Configurações centralizadas do aplicativo"""
    
    # Informações da aplicação
    APP_NAME = "reframe-endpoint"
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    BUILD_NUMBER = os.getenv("BUILD_NUMBER", "dev")
    BUILD_DATE = os.getenv("BUILD_DATE", datetime.now().isoformat())
    
    # Servidor
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8080"))
    
    # URL pública para Swagger (usado quando acessado remotamente)
    # Exemplo: https://apis-reframe-endpoint.mhcqvd.easypanel.host
    # Se não definido, usa comportamento padrão (localhost)
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
    
    # Workers e fila
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
    
    # Storage (DigitalOcean Spaces)
    OUTPUT_PREFIX = os.getenv("OUTPUT_PREFIX", "reframes")
    SPACES_REGION = os.getenv("SPACES_REGION", "nyc3")
    SPACES_ENDPOINT = os.getenv("SPACES_ENDPOINT", "https://nyc3.digitaloceanspaces.com")
    SPACES_BUCKET = os.getenv("SPACES_BUCKET", "cod5")
    SPACES_KEY = os.getenv("SPACES_KEY")
    SPACES_SECRET = os.getenv("SPACES_SECRET")
    SPACES_CDN_BASE = os.getenv("SPACES_CDN_BASE")
    
    # Autenticação
    API_TOKEN = os.getenv("API_TOKEN")
    
    # Pesos dos estágios para cálculo de progresso
    STAGE_WEIGHTS = {
        "queued": 0.0,
        "downloading": 0.05,
        "reframing": 0.80,
        "muxing": 0.05,
        "uploading": 0.10
    }
    
    # Paths
    TMP_DIR = os.getenv("TMP_DIR", "/tmp")
    JOBS_SNAPSHOT_DIR = os.getenv("JOBS_SNAPSHOT_DIR", "/tmp")
    
    # Uploads
    UPLOAD_DEFAULT_FOLDER = os.getenv("UPLOAD_DEFAULT_FOLDER", "upload/reframe")
    UPLOAD_TTL_DAYS = int(os.getenv("UPLOAD_TTL_DAYS", "7"))
    UPLOAD_MAX_TTL_DAYS = int(os.getenv("UPLOAD_MAX_TTL_DAYS", "30"))
    UPLOADS_SNAPSHOT_DIR = os.getenv("UPLOADS_SNAPSHOT_DIR", "/tmp")
    
    @classmethod
    def get_build_info(cls) -> dict:
        """Retorna informações de build"""
        return {
            "version": cls.APP_VERSION,
            "build_number": cls.BUILD_NUMBER,
            "build_date": cls.BUILD_DATE,
            "app_name": cls.APP_NAME
        }
    
    @classmethod
    def to_dict(cls) -> dict:
        """Retorna todas as configurações como dicionário (sem secrets)"""
        return {
            "app_name": cls.APP_NAME,
            "app_version": cls.APP_VERSION,
            "build_number": cls.BUILD_NUMBER,
            "build_date": cls.BUILD_DATE,
            "host": cls.HOST,
            "port": cls.PORT,
            "max_workers": cls.MAX_WORKERS,
            "output_prefix": cls.OUTPUT_PREFIX,
            "spaces_region": cls.SPACES_REGION,
            "spaces_endpoint": cls.SPACES_ENDPOINT,
            "spaces_bucket": cls.SPACES_BUCKET,
            "spaces_cdn_base": cls.SPACES_CDN_BASE,
            "has_api_token": bool(cls.API_TOKEN),
            "stage_weights": cls.STAGE_WEIGHTS,
            "tmp_dir": cls.TMP_DIR,
            "jobs_snapshot_dir": cls.JOBS_SNAPSHOT_DIR,
            "upload_default_folder": cls.UPLOAD_DEFAULT_FOLDER,
            "upload_ttl_days": cls.UPLOAD_TTL_DAYS,
            "upload_max_ttl_days": cls.UPLOAD_MAX_TTL_DAYS
        }

