# Documento de Requisitos de Produto
## Reframe Endpoint - Deploy Público em VPS com Easypanel

**Versão:** 1.0  
**Data:** Dezembro 2024  
**Autor:** Análise de Requisitos Técnicos

---

## 1. VISÃO GERAL DO PROJETO

### 1.1 Descrição
Serviço de API REST desenvolvido em Python/Flask que processa vídeos em tempo real para reenquadramento automático. O serviço converte vídeos de 16:9 para formato 9:16 (vertical), utilizando MediaPipe para detectar e seguir o falante principal.

### 1.2 Tecnologias Utilizadas
- **Backend:** Flask + Gunicorn
- **Processamento:** MediaPipe, OpenCV
- **Storage:** DigitalOcean Spaces (boto3)
- **Containerização:** Docker (via nixpacks.toml)
- **Deploy:** Easypanel + VPS

---

## 2. OBJETIVOS DO DEPLOY

### 2.1 Objetivo Principal
Disponibilizar o serviço publicamente em VPS através do Easypanel, permitindo que clientes externos enviem requisições de reframing de vídeos via API REST.

### 2.2 Casos de Uso
- Clientes externos via API REST
- Processamento assíncrono de vídeos
- Armazenamento público de vídeos processados
- Callbacks para notificação de conclusão

---

## 3. ANÁLISE DO ESTADO ATUAL

### 3.1 Arquivos Existentes ✅
- ✅ `app.py` - Aplicação Flask principal
- ✅ `Procfile` - Configuração Heroku/Railway
- ✅ `nixpacks.toml` - Configuração Nixpacks/Docker
- ✅ `requirements.txt` - Dependências Python
- ✅ `reframe_mediapipe_falante_v7.py` - Módulo de processamento
- ✅ `storage/spaces.py` - Integração DigitalOcean Spaces

### 3.2 Arquivos Faltantes ❌
1. **`.gitignore`** - Ignorar arquivos desnecessários no repositório
2. **`.env.example`** - Template de variáveis de ambiente
3. **README.md completo** - Documentação do projeto
4. **Configuração CI/CD** - GitHub Actions (opcional mas recomendado)
5. **Documentação de API** - Swagger/OpenAPI (opcional)

---

## 4. REQUISITOS FUNCIONAIS

### 4.1 Endpoints da API

#### 4.1.1 Health Check
- **GET** `/` - Status do serviço
- Retorna: `queue_size`, `workers`, status

#### 4.1.2 Enfileirar Processamento
- **POST** `/v1/video/reframe`
- **Body:**
  ```json
  {
    "input_url": "https://example.com/video.mp4",
    "callback_url": "https://example.com/webhook" // opcional
  }
  ```
- Retorna: `job_id`, status `queued`

#### 4.1.3 Status do Job
- **GET** `/v1/video/status/<job_id>`
- Retorna: progresso, stage atual, ETA, métricas

#### 4.1.4 Listar Jobs
- **GET** `/v1/video/jobs?status=done&limit=50`
- Retorna: lista de jobs com filtros

#### 4.1.5 Download do Vídeo
- **GET** `/v1/video/download/<job_id>`
- Retorna: arquivo ou URL pública

#### 4.1.6 Teste de Upload
- **POST** `/v1/test/upload`
- Testa conectividade com DigitalOcean Spaces

### 4.2 Fluxo de Processamento
1. **Queued** → Job enfileirado
2. **Downloading** → Download do vídeo de entrada
3. **Reframing** → Processamento com MediaPipe
4. **Muxing** → Incorporação de áudio
5. **Uploading** → Upload para Spaces
6. **Done** → Concluído com URL pública

---

## 5. REQUISITOS NÃO FUNCIONAIS

### 5.1 Performance
- **Workers Paralelos:** Configurável via `MAX_WORKERS` (default: 2)
- **Timeout:** 60s para download
- **Queue Management:** Sistema de fila com threading

### 5.2 Escalabilidade
- Suporte a múltiplos workers simultâneos
- Persistência de estado em `/tmp/job_*.json`
- Cleanup automático de arquivos temporários

### 5.3 Segurança
- **Variáveis de Ambiente:** Credenciais sensíveis via `.env`
- **Validação de Input:** Sanitização de URLs e caminhos
- **Rate Limiting:** Não implementado (⚠️ pendência)
- **CORS:** Não configurado (⚠️ pendência)

### 5.4 Confiabilidade
- Tratamento de erros em todas as etapas
- Callback opcional para notificação de conclusão
- Fallback para salvar localmente se upload falhar
- Snapshot de jobs para recuperação

---

## 6. DEPENDÊNCIAS E CONFIGURAÇÃO

### 6.1 Variáveis de Ambiente Necessárias

```bash
# DigitalOcean Spaces
SPACES_REGION=nyc3                    # Região do Space
SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
SPACES_BUCKET=seu-bucket              # Nome do bucket
SPACES_KEY=SUA_KEY                    # Access Key
SPACES_SECRET=SUA_SECRET_KEY          # Secret Key
SPACES_CDN_BASE=https://cdn.example.com  # Opcional

# Configuração do Serviço
MAX_WORKERS=2                          # Número de workers (default: 2)
OUTPUT_PREFIX=reframes                 # Prefixo para uploads

# Porta (geralmente definida pelo container)
PORT=8080                               # Padrão para container

# Python (opcional para debug)
FLASK_ENV=production
```

### 6.2 Dependências Python
```txt
flask
requests
mediapipe
opencv-python-headless
numpy
boto3
python-dotenv
gunicorn  # ❌ FALTANDO - necessário para produção
```

⚠️ **ISSUE CRÍTICA:** `gunicorn` não está listado em `requirements.txt` mas é usado no `Procfile`.

---

## 7. REQUISITOS DE INFRAESTRUTURA

### 7.1 Easypanel
- **Plataforma:** Container Linux
- **Build System:** Nixpacks (via `nixpacks.toml`)
- **Runtime:** Gunicorn (via `Procfile`)
- **Porta:** 8080 (configurada automaticamente)

### 7.2 Recursos Necessários
- **CPU:** Mínimo 2 cores (recomendado 4+)
- **RAM:** Mínimo 2GB (recomendado 4GB+)
- **Disco:** 10GB+ para arquivos temporários
- **Bandwidth:** Alto para upload/download de vídeos

### 7.3 Pacotes Sistema
✅ Já configurado em `nixpacks.toml`:
- `ffmpeg` (necessário para muxing de áudio)

### 7.4 Storage Externo
- **DigitalOcean Spaces:** Configuração S3-compatible
- **Bucket:** Público para upload de vídeos processados
- **CDN:** Opcional via `SPACES_CDN_BASE`

---

## 8. GAPS IDENTIFICADOS E CORREÇÕES NECESSÁRIAS

### 8.1 🔴 CRÍTICO - Correções Obrigatórias

#### 8.1.1 Adicionar `gunicorn` ao requirements.txt
**Problema:** Procfile usa gunicorn mas não está instalado.

**Solução:**
```python
# requirements.txt - ADICIONAR:
gunicorn>=21.2.0
```

#### 8.2.2 Criar arquivo `.gitignore`
**Problema:** Arquivos desnecessários sendo versionados.

**Arquivo necessário:**
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/

# Flask
instance/
.webassets-cache

# Media files
*.mp4
*.avi
*.mov
temp/

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
/tmp/job_*.json
/tmp/test_upload.txt
```

### 8.2 🟡 IMPORTANTE - Melhorias Recomendadas

#### 8.2.1 Criar `.env.example`
**Problema:** Desenvolvedores não sabem quais variáveis configurar.

**Arquivo necessário:**
```bash
# DigitalOcean Spaces
SPACES_REGION=nyc3
SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
SPACES_BUCKET=seu-bucket
SPACES_KEY=sua-access-key
SPACES_SECRET=sua-secret-key
SPACES_CDN_BASE=  # Opcional

# Configuração do Serviço
MAX_WORKERS=2
OUTPUT_PREFIX=reframes
PORT=8080
```

#### 8.2.2 Melhorar `README.md`
**Status Atual:** Apenas "# reframe-endpoint"

**Conteúdo necessário:**
- Descrição do projeto
- Instruções de setup local
- Documentação da API
- Variáveis de ambiente
- Exemplos de uso
- Troubleshooting

### 8.3 🟢 SUGERIDO - Otimizações Futuras

#### 8.3.1 Configurar CORS
```python
from flask_cors import CORS
CORS(app)  # ou CORS(app, resources={r"/*": {"origins": "https://meudominio.com"}})
```

#### 8.3.2 Implementar Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

#### 8.3.3 Adicionar Logging Estruturado
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

#### 8.3.4 Documentação OpenAPI/Swagger
```python
from flask_swagger_ui import get_swaggerui_blueprint
```

---

## 9. PLANO DE DEPLOY

### 9.1 Fase 1: Preparação do Código (ANTES DO PUSH)
1. ✅ Criar `.gitignore`
2. ✅ Adicionar `gunicorn` ao `requirements.txt`
3. ✅ Criar `.env.example`
4. ✅ Melhorar `README.md`
5. ✅ Testar localmente com Docker

### 9.2 Fase 2: Push para GitHub
1. Inicializar repositório (se não existe)
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/seu-usuario/reframe-endpoint.git
   git push -u origin main
   ```

### 9.3 Fase 3: Configuração Easypanel
1. Conectar repositório GitHub no Easypanel
2. Configurar build via Nixpacks
3. Adicionar variáveis de ambiente no Easypanel
4. Configurar domínio/path (opcional)

### 9.4 Fase 4: Deploy e Teste
1. Deploy automático via GitHub
2. Testar endpoint de health: `GET /`
3. Testar upload: `POST /v1/test/upload`
4. Testar reframing: `POST /v1/video/reframe`
5. Monitorar logs

---

## 10. CHECKLIST DE DEPLOY

### 10.1 Antes do Deploy
- [ ] Criar arquivo `.gitignore`
- [ ] Adicionar `gunicorn` ao `requirements.txt`
- [ ] Criar arquivo `.env.example`
- [ ] Atualizar `README.md` com documentação completa
- [ ] Testar localmente com `docker build` (opcional)
- [ ] Verificar todas as variáveis de ambiente necessárias

### 10.2 Configuração do Easypanel
- [ ] Criar novo app no Easypanel
- [ ] Conectar repositório GitHub
- [ ] Adicionar variáveis de ambiente no painel
- [ ] Configurar porta 8080
- [ ] Verificar configuração de build (nixpacks)

### 10.3 Pós-Deploy
- [ ] Testar health check: `curl https://seu-app.com/`
- [ ] Testar upload: `POST /v1/test/upload`
- [ ] Testar processamento completo
- [ ] Verificar logs no Easypanel
- [ ] Configurar domínio customizado (opcional)
- [ ] Configurar SSL/HTTPS (geralmente automático)

---

## 11. ARQUITETURA DE DEPLOY

```
┌─────────────────┐
│   Cliente API   │
└────────┬────────┘
         │ HTTP/HTTPS
         ▼
┌─────────────────────────────────────┐
│      Easypanel (VPS)                │
│  ┌───────────────────────────────┐  │
│  │    Container Docker           │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  Flask + Gunicorn       │  │  │
│  │  │  (Port 8080)            │  │  │
│  │  └─────────────────────────┘  │  │
│  │         │                     │  │
│  │    ┌────┴────┐                │  │
│  │    │ Workers │                │  │
│  │    │  Queue  │                │  │
│  │    └────┬────┘                │  │
│  │         │                     │  │
│  │  ┌──────┴────────┐           │  │
│  │  │ MediaPipe      │           │  │
│  │  │ OpenCV          │           │  │
│  │  │ FFmpeg          │           │  │
│  │  └────────────────┘           │  │
│  └───────────────────────────────┘  │
└───────────────────┬─────────────────┘
                    │ Upload
                    ▼
        ┌─────────────────────┐
        │ DigitalOcean Spaces │
        │   (S3 Compatible)   │
        └─────────────────────┘
```

---

## 12. TROUBLESHOOTING

### 12.1 Problemas Comuns

#### Erro: "gunicorn: command not found"
**Causa:** Gunicorn não está em requirements.txt  
**Solução:** Adicionar `gunicorn` ao `requirements.txt`

#### Erro: "ModuleNotFoundError: No module named 'mediapipe'"
**Causa:** Dependências não instaladas  
**Solução:** Verificar `requirements.txt` e build logs

#### Erro: "403 Forbidden - DigitalOcean Spaces"
**Causa:** Credenciais inválidas  
**Solução:** Verificar `SPACES_KEY` e `SPACES_SECRET`

#### Erro: "ffmpeg: command not found"
**Causa:** FFmpeg não instalado no container  
**Solução:** Verificar `nixpacks.toml` - deve conter `"ffmpeg"`

#### Timeout no download
**Causa:** Vídeo muito grande ou conexão lenta  
**Solução:** Aumentar timeout ou usar vídeos menores

---

## 13. MÉTRICAS E MONITORAMENTO

### 13.1 Endpoints de Monitoramento
- `GET /` - Health check simples
- `GET /v1/video/jobs` - Status da fila

### 13.2 Métricas Recomendadas (Implementar Futuramente)
- Taxa de sucesso/erro
- Tempo médio de processamento
- Uso de CPU/RAM
- Tamanho médio de vídeos

---

## 14. SEGURANÇA

### 14.1 Implementado ✅
- Variáveis de ambiente para credenciais
- Validação básica de input
- Cleanup de arquivos temporários

### 14.2 Pendente ⚠️
- **Rate Limiting** - Prevenir abuso
- **CORS** - Controlar origens permitidas
- **Autenticação** - API keys ou tokens
- **HTTPS** - Geralmente automático no Easypanel
- **Input Validation** - Limitar tamanho de vídeos

---

## 15. ESCALABILIDADE FUTURA

### 15.1 Quando Crescer
- **Redis** para fila distribuída
- **Celery** para processamento assíncrono
- **Kubernetes** para scaling horizontal
- **S3/CDN** para distribuição global
- **Database** para persistência de jobs

---

## 16. CONCLUSÃO

### 16.1 Estado Atual
✅ **Quase pronto para deploy!** O projeto está bem estruturado e funcionalmente completo.

### 16.2 Ações Necessárias Antes do Deploy Público

**CRÍTICO (Fazer agora):**
1. Adicionar `gunicorn` ao `requirements.txt`
2. Criar arquivo `.gitignore`
3. Criar arquivo `.env.example`
4. Atualizar `README.md` com documentação

**Importante (Fazer em breve):**
5. Implementar CORS
6. Adicionar Rate Limiting
7. Melhorar tratamento de erros
8. Adicionar logging estruturado

**Opcional (Melhorias futuras):**
9. Documentação OpenAPI
10. Testes automatizados
11. CI/CD pipeline
12. Monitoramento avançado

### 16.3 Estimativa
- **Tempo de correção:** ~1 hora (críticas)
- **Tempo de deploy:** ~30 minutos (EasyPanel)
- **Total para produção:** ~2 horas

---

**Próximos Passos Recomendados:**
1. Implementar as correções críticas (itens 1-4)
2. Fazer push para GitHub
3. Configurar no Easypanel
4. Fazer deploy e testes
5. Monitorar e iterar

---

*Documento gerado automaticamente em: {{DATA_ATUAL}}*

