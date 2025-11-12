# Guia de Configuração - Dashboard Reframe API

## Problemas Identificados e Soluções

### 1. URL Incorreta no Dashboard

**Problema:** O dashboard está configurado para usar:
```
http://apis-reframe-endpoint.mhcqvd.easypanel.host:8080
```

**Solução:** A URL correta no Easypanel é:
```
https://apis-reframe-endpoint.mhcqvd.easypanel.host
```

**Por quê?**
- O Easypanel expõe aplicações via HTTPS na porta padrão (443)
- Não é necessário especificar a porta `:8080` na URL pública
- A porta 8080 é apenas interna do container
- O protocolo deve ser HTTPS (não HTTP)

**O que fazer no dashboard:**
1. Abra o arquivo `public/assets/config.js`
2. Altere a URL base de:
   ```javascript
   API_BASE_URL: 'http://apis-reframe-endpoint.mhcqvd.easypanel.host:8080'
   ```
   Para:
   ```javascript
   API_BASE_URL: 'https://apis-reframe-endpoint.mhcqvd.easypanel.host'
   ```

---

### 2. Endpoints de Métricas Precisam Ser Públicos

**Problema:** Os endpoints que o dashboard consome não estão na lista de endpoints públicos:
- `GET /metrics/kpi` → função `metrics_kpi()`
- `GET /metrics/queue` → função `metrics_queue()`
- `GET /metrics/history` → função `metrics_history()`
- `GET /v1/video/jobs` → função `list_jobs()`
- `GET /v1/uploads` → função `list_uploads()`

**Solução:** Adicionar esses endpoints à lista de públicos em `app.py`

**Alteração necessária em `app.py`:**

Localize a linha 92:
```python
public_endpoints = ['root', 'get_swagger_ui', 'get_apispec_json', 'metrics_health']
```

Altere para:
```python
public_endpoints = [
    'root', 
    'get_swagger_ui', 
    'get_apispec_json', 
    'metrics_health',
    'metrics_kpi',
    'metrics_queue',
    'metrics_history',
    'list_jobs',
    'list_uploads'
]
```

**Alternativa (se preferir usar autenticação):**
Se você quiser manter esses endpoints protegidos, o dashboard precisa enviar o token de autenticação no header `X-Api-Token` em todas as requisições.

---

### 3. CORS Já Está Configurado Corretamente

✅ **Status:** CORS já está configurado para aceitar requisições de qualquer origem (`origins: "*"`)

**Localização:** Linha 16-20 de `app.py`
```python
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     supports_credentials=True,
     expose_headers=["Content-Type", "X-Upload-ID"],
     allow_headers=["Content-Type", "X-Api-Token", "X-Requested-With", "Accept"])
```

**Não é necessário alterar nada aqui.**

---

### 4. Verificação de Protocolo (Mixed Content)

**Problema:** Se o dashboard roda em `http://localhost:3000` e tenta acessar `https://...`, alguns navegadores podem bloquear por "Mixed Content".

**Solução:** 
- Opção 1: Servir o dashboard também via HTTPS
- Opção 2: O CORS já permite, mas verifique o console do navegador para erros de Mixed Content

---

## Checklist de Implementação

### No Backend (API - `app.py`)

- [ ] Adicionar endpoints de métricas à lista `public_endpoints` (linha 92)
- [ ] Fazer commit e push das alterações
- [ ] Aguardar deploy automático no Easypanel (ou fazer deploy manual)

### No Frontend (Dashboard)

- [ ] Alterar `API_BASE_URL` em `public/assets/config.js`:
  - De: `http://apis-reframe-endpoint.mhcqvd.easypanel.host:8080`
  - Para: `https://apis-reframe-endpoint.mhcqvd.easypanel.host`
- [ ] Remover a porta `:8080` da URL
- [ ] Garantir que o protocolo seja `https://` (não `http://`)

### Teste

- [ ] Abrir o dashboard em `http://localhost:3000`
- [ ] Abrir o Console do navegador (F12)
- [ ] Verificar se as requisições estão sendo feitas para `https://...` (sem porta)
- [ ] Verificar se não há erros de CORS
- [ ] Verificar se os dados estão sendo exibidos nos cards

---

## Endpoints que o Dashboard Consome

| Endpoint | Método | Função | Status Atual | Ação Necessária |
|----------|--------|--------|--------------|-----------------|
| `/` | GET | `root()` | ✅ Público | Nenhuma |
| `/metrics/kpi` | GET | `metrics_kpi()` | ❌ Protegido | Adicionar à lista pública |
| `/metrics/queue` | GET | `metrics_queue()` | ❌ Protegido | Adicionar à lista pública |
| `/metrics/history` | GET | `metrics_history()` | ❌ Protegido | Adicionar à lista pública |
| `/v1/video/jobs` | GET | `list_jobs()` | ❌ Protegido | Adicionar à lista pública |
| `/v1/uploads` | GET | `list_uploads()` | ❌ Protegido | Adicionar à lista pública |

---

## Código Completo da Correção

### Alteração em `app.py` (linha ~92)

**ANTES:**
```python
public_endpoints = ['root', 'get_swagger_ui', 'get_apispec_json', 'metrics_health']
```

**DEPOIS:**
```python
public_endpoints = [
    'root', 
    'get_swagger_ui', 
    'get_apispec_json', 
    'metrics_health',
    'metrics_kpi',        # GET /metrics/kpi
    'metrics_queue',      # GET /metrics/queue
    'metrics_history',    # GET /metrics/history
    'list_jobs',         # GET /v1/video/jobs
    'list_uploads'       # GET /v1/uploads
]
```

---

## Teste Rápido via cURL

Após fazer as alterações, teste se os endpoints estão acessíveis:

```bash
# Teste endpoint raiz (já funciona)
curl https://apis-reframe-endpoint.mhcqvd.easypanel.host/

# Teste métricas KPI (deve funcionar após correção)
curl https://apis-reframe-endpoint.mhcqvd.easypanel.host/metrics/kpi

# Teste lista de jobs (deve funcionar após correção)
curl https://apis-reframe-endpoint.mhcqvd.easypanel.host/v1/video/jobs?limit=10

# Teste lista de uploads (deve funcionar após correção)
curl https://apis-reframe-endpoint.mhcqvd.easypanel.host/v1/uploads?limit=10
```

Se algum retornar `401 Unauthorized`, significa que ainda precisa ser adicionado à lista pública.

---

## Resumo Executivo

**O que precisa ser feito:**

1. ✅ **CORS:** Já está configurado corretamente - nenhuma ação necessária
2. ⚠️ **URL do Dashboard:** Alterar de `http://...:8080` para `https://...` (sem porta)
3. ⚠️ **Endpoints Públicos:** Adicionar 5 endpoints à lista pública em `app.py`
4. ✅ **Deploy:** Fazer commit, push e aguardar deploy automático

**Tempo estimado:** 5-10 minutos

**Impacto:** Dashboard funcionará completamente após essas alterações

