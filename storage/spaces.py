# storage/spaces.py
import os
import boto3
import mimetypes
import uuid
import datetime

SPACES_REGION   = os.getenv("SPACES_REGION",  "nyc3")
SPACES_ENDPOINT = os.getenv("SPACES_ENDPOINT","https://nyc3.digitaloceanspaces.com")
SPACES_BUCKET   = os.getenv("SPACES_BUCKET",  "cod5")
SPACES_KEY      = os.getenv("SPACES_KEY")
SPACES_SECRET   = os.getenv("SPACES_SECRET")

# Opcional: se você tiver um CDN/CNAME (ex.: https://cdn.seudominio.com)
SPACES_CDN_BASE = os.getenv("SPACES_CDN_BASE")  # e.g. https://cdn.meuspace.com

import ssl
import urllib3
import warnings

# Suprime warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Configura SSL context para resolver problemas de certificado
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Configura botocore para usar SSL customizado
import botocore
from botocore.config import Config

config = Config(
    signature_version='s3v4',
    s3={
        'addressing_style': 'virtual'
    }
)

_session = boto3.session.Session(
    aws_access_key_id=SPACES_KEY,
    aws_secret_access_key=SPACES_SECRET,
    region_name=SPACES_REGION,
)
_s3 = _session.client("s3", endpoint_url=SPACES_ENDPOINT, 
                     use_ssl=True, verify=False, config=config)

def make_key(prefix: str, filename: str) -> str:
    ext = os.path.splitext(filename)[1] or ".mp4"
    date = datetime.datetime.utcnow().strftime("%Y/%m/%d")
    return f"{prefix.strip('/')}/{date}/{uuid.uuid4().hex}{ext}"

def public_url_for(key: str) -> str:
    if SPACES_CDN_BASE:
        return f"{SPACES_CDN_BASE.rstrip('/')}/{key}"
    # URL pública default do Spaces
    return f"https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com/{key}"

def upload_public(file_path: str, key: str) -> str:
    ctype = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        _s3.put_object(
            Bucket=SPACES_BUCKET,
            Key=key,
            Body=f,
            ACL="public-read",
            ContentType=ctype,
            CacheControl="public, max-age=31536000, immutable"
        )
    return public_url_for(key)
