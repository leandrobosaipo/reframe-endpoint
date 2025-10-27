# reframe-endpoint

Serviço de API REST para reframing automático de vídeos utilizando MediaPipe.

## 🎯 Descrição

Este projeto processa vídeos em formato 16:9 e converte automaticamente para 9:16 (formato vertical), mantendo o foco no falante principal detectado por IA. Ideal para conteúdo de redes sociais como TikTok, Instagram Reels, YouTube Shorts.

## 🚀 Funcionalidades

- ✅ Detecção automática de falantes usando MediaPipe
- ✅ Reenquadramento inteligente 16:9 → 9:16
- ✅ Preservação de áudio original
- ✅ Processamento assíncrono com sistema de fila
- ✅ Upload automático para DigitalOcean Spaces
- ✅ Callbacks para notificação de conclusão
- ✅ API REST completa com status de progresso

## 📋 Requisitos

- Python 3.8+
- FFmpeg
- DigitalOcean Spaces (ou S3-compatible storage)
- Container/VPS com Easypanel

## 🛠️ Instalação Local

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/reframe-endpoint.git
cd reframe-endpoint
```

### 2. Crie e ative um ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Copie o arquivo de exemplo e configure:

```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais:

```bash
# DigitalOcean Spaces
SPACES_REGION=nyc3
SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
SPACES_BUCKET=seu-bucket
SPACES_KEY=sua-access-key
SPACES_SECRET=sua-secret-key

# Configuração
MAX_WORKERS=2
OUTPUT_PREFIX=reframes
```

### 5. Execute o servidor

```bash
python app.py
# ou com gunicorn (produção)
gunicorn -b 0.0.0.0:8080 app:app
```

O servidor estará disponível em `http://localhost:8080`

## 📡 API Endpoints

### Health Check
```bash
GET /
```
Retorna informações sobre o serviço e status da fila.

**Resposta:**
```json
{
  "service": "reframe-endpoint",
  "queue_size": 0,
  "workers": 2
}
```

### Enfileirar Processamento
```bash
POST /v1/video/reframe
Content-Type: application/json

{
  "input_url": "https://example.com/video.mp4",
  "callback_url": "https://seusite.com/webhook"  // opcional
}
```

**Resposta:**
```json
{
  "status": "queued",
  "message": "processamento enfileirado",
  "job_id": "job_abc123def4"
}
```

### Status do Job
```bash
GET /v1/video/status/<job_id>
```

**Resposta:**
```json
{
  "job_id": "job_abc123def4",
  "status": "reframing",
  "progress": 45.5,
  "stage": "reframing",
  "stage_progress": 0.56,
  "eta_seconds": 120
}
```

### Listar Jobs
```bash
GET /v1/video/jobs?status=done&limit=50
```

**Query Parameters:**
- `status` (opcional): filtrar por status (queued, downloading, reframing, done, error)
- `limit` (opcional): número máximo de resultados (default: 50)

### Download do Vídeo
```bash
GET /v1/video/download/<job_id>
```
Retorna o arquivo de vídeo processado ou URL pública.

### Teste de Upload
```bash
POST /v1/test/upload
```
Testa a conectividade com DigitalOcean Spaces.

## 🔄 Fluxo de Processamento

1. **Queued** - Job enfileirado (0%)
2. **Downloading** - Download do vídeo (0-5%)
3. **Reframing** - Processamento com MediaPipe (5-85%)
4. **Muxing** - Incorporação de áudio (85-90%)
5. **Uploading** - Upload para Spaces (90-100%)
6. **Done** - Concluído com URL pública

## 🐳 Deploy com Easypanel

### Configuração no Easypanel

1. **Conecte o repositório GitHub**
   - Vá em "New App" → "Connect GitHub"
   - Selecione o repositório

2. **Adicione as variáveis de ambiente:**
   ```
   SPACES_REGION=nyc3
   SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
   SPACES_BUCKET=seu-bucket
   SPACES_KEY=***
   SPACES_SECRET=***
   MAX_WORKERS=2
   OUTPUT_PREFIX=reframes
   ```

3. **Configure o build:**
   - Build System: Nixpacks (automático)
   - Porta: 8080

4. **Deploy:**
   - Easypanel detecta o `Procfile` e `nixpacks.toml`
   - Build automático via GitHub push

## 📝 Exemplo de Uso

### Usando cURL

```bash
# Enfileirar processamento
curl -X POST https://seu-app.easypanel.app/v1/video/reframe \
  -H "Content-Type: application/json" \
  -d '{
    "input_url": "https://example.com/video.mp4",
    "callback_url": "https://seusite.com/webhook"
  }'

# Verificar status
curl https://seu-app.easypanel.app/v1/video/status/job_abc123def4

# Baixar vídeo processado
curl https://seu-app.easypanel.app/v1/video/download/job_abc123def4
```

### Usando Python

```python
import requests

# Enfileirar
response = requests.post(
    "https://seu-app.easypanel.app/v1/video/reframe",
    json={
        "input_url": "https://example.com/video.mp4",
        "callback_url": "https://seusite.com/webhook"
    }
)
data = response.json()
job_id = data["job_id"]

# Verificar status
status = requests.get(
    f"https://seu-app.easypanel.app/v1/video/status/{job_id}"
)
print(status.json())

# Download
video = requests.get(
    f"https://seu-app.easypanel.app/v1/video/download/{job_id}"
)
with open("output.mp4", "wb") as f:
    f.write(video.content)
```

## 🔧 Configuração Avançada

### Aumentar Workers
```bash
MAX_WORKERS=4  # Processar 4 vídeos simultaneamente
```

### Customizar Prefixo de Upload
```bash
OUTPUT_PREFIX=meus-reframes  # Arquivos vão para spaces/bucket/meus-reframes/
```

### Usar CDN Customizado
```bash
SPACES_CDN_BASE=https://cdn.seudominio.com
# URLs retornadas usarão este domínio
```

## 🐛 Troubleshooting

### Erro: "gunicorn: command not found"
```bash
pip install gunicorn
# ou adicione ao requirements.txt
```

### Erro: "ffmpeg: command not found"
FFmpeg é instalado automaticamente via `nixpacks.toml`. Verifique os logs de build.

### Erro: "403 Forbidden - Spaces"
Verifique as credenciais `SPACES_KEY` e `SPACES_SECRET` no Easypanel.

### Timeout no download
Para vídeos muito grandes, considere aumentar o timeout ou usar vídeos menores.

## 📊 Estrutura do Projeto

```
reframe-endpoint/
├── app.py                          # Aplicação Flask principal
├── reframe_mediapipe_falante_v7.py # Módulo de processamento
├── storage/
│   └── spaces.py                   # Integração DigitalOcean Spaces
├── requirements.txt                # Dependências Python
├── Procfile                        # Configuração Heroku/Railway
├── nixpacks.toml                   # Configuração Docker/Nixpacks
├── .env.example                    # Template de variáveis
└── README.md                        # Este arquivo
```

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT.

## 👤 Autor

Seu Nome - [@seu-usuario](https://github.com/seu-usuario)

---

Made with ❤️ using Flask, MediaPipe, and OpenCV

