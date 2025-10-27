# 🚀 Guia de Configuração - Easypanel

## ✅ Deploy Concluído

Repositório GitHub atualizado: **https://github.com/leandrobosaipo/reframe-endpoint.git**

---

## 📋 Passo a Passo - Easypanel

### **PASSO 1: Criar Novo App no Easypanel** (2 min)

1. Acesse https://easypanel.io e faça login
2. Clique em **"New App"** ou **"Create New App"**
3. Selecione **"From GitHub Repository"**
4. Conecte sua conta GitHub (se ainda não conectou)
5. Selecione o repositório: **`leandrobosaipo/reframe-endpoint`**

### **PASSO 2: Configuração do Build** (1 min)

O Easypanel pode usar **2 métodos**:

#### Método 1: Dockerfile (Recomendado) ✅
- ✅ `Dockerfile` - Deploy com Docker customizado
- Instala FFmpeg e dependências do OpenCV
- Mais controle sobre o ambiente

#### Método 2: Nixpacks (Automático)
- ✅ `Procfile` - Configuração do Gunicorn
- ✅ `nixpacks.toml` - Instalação do FFmpeg
- ✅ `requirements.txt` - Dependências Python

**O Easypanel detectará automaticamente o Dockerfile e o usará preferencialmente!**

### **PASSO 3: Variáveis de Ambiente** (5 min) ⚠️ **CRÍTICO**

Vá para a seção **"Environment Variables"** e adicione:

#### 🔑 Variáveis Obrigatórias

```bash
SPACES_REGION=nyc3
```

```bash
SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
```

```bash
SPACES_BUCKET=cod5
```
**Nota:** Use o nome do seu bucket DigitalOcean Spaces

```bash
SPACES_KEY=SUA_ACCESS_KEY_AQUI
```
**Como obter:**
1. Acesse https://cloud.digitalocean.com
2. Vá em **Spaces** → **Settings** → **Keys**
3. Copie a **Access Key**

```bash
SPACES_SECRET=SUA_SECRET_KEY_AQUI
```
**Como obter:**
1. Mesmo local (DigitalOcean)
2. Copie a **Secret Key**

#### ⚙️ Variáveis de Configuração (Opcionais)

```bash
MAX_WORKERS=2
```
Número de vídeos processados simultaneamente

```bash
OUTPUT_PREFIX=reframes
```
Prefixo da pasta no Spaces (onde os vídeos serão salvos)

#### 🌐 CDN (Opcional)

```bash
SPACES_CDN_BASE=https://cdn.seudominio.com
```
Para usar um domínio CDN customizado

---

### **PASSO 4: Recursos do Servidor** (1 min)

Configure os recursos recomendados:

- **CPU:** Mínimo 2 cores (recomendado 4)
- **RAM:** Mínimo 2GB (recomendado 4GB)
- **Disco:** 10GB+
- **Porta:** Auto-configurado (8080)

### **PASSO 5: Deploy** (5-10 min)

1. Clique em **"Deploy"** ou **"Create App"**
2. Aguarde o build (pode levar 5-10 minutos na primeira vez)
3. Monitore os logs em tempo real
4. Quando aparecer **"Deployed successfully"**, está pronto!

---

## 🧪 Testes Pós-Deploy

### Teste 1: Health Check

```bash
curl https://seu-app-id.easypanel.app/
```

**Resposta esperada:**
```json
{
  "service": "reframe-endpoint",
  "queue_size": 0,
  "workers": 2
}
```

### Teste 2: Upload para Spaces

```bash
curl -X POST https://seu-app-id.easypanel.app/v1/test/upload
```

**Resposta esperada:**
```json
{
  "status": "success",
  "message": "Upload funcionando!",
  "url": "https://cod5.nyc3.digitaloceanspaces.com/test/...",
  "key": "test/..."
}
```

### Teste 3: Processar um Vídeo

```bash
curl -X POST https://seu-app-id.easypanel.app/v1/video/reframe \
  -H "Content-Type: application/json" \
  -d '{
    "input_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
  }'
```

**Resposta esperada:**
```json
{
  "status": "queued",
  "message": "processamento enfileirado",
  "job_id": "job_abc123def4"
}
```

Depois verifique o status:
```bash
curl https://seu-app-id.easypanel.app/v1/video/status/job_abc123def4
```

---

## 🎯 Configurações Rápidas Easypanel

### Painel de Variáveis

```
┌─────────────────────────────┬─────────────────────────────────────────┐
│ Nome                         │ Valor                                    │
├─────────────────────────────┼─────────────────────────────────────────┤
│ SPACES_REGION                │ nyc3                                     │
│ SPACES_ENDPOINT              │ https://nyc3.digitaloceanspaces.com     │
│ SPACES_BUCKET                │ cod5                                     │
│ SPACES_KEY                   │ [SUA_ACCESS_KEY]                        │
│ SPACES_SECRET                │ [SUA_SECRET_KEY]                        │
│ MAX_WORKERS                  │ 2                                        │
│ OUTPUT_PREFIX                │ reframes                                 │
└─────────────────────────────┴─────────────────────────────────────────┘
```

### Configuração do Domínio (Opcional)

1. Vá em **Settings** → **Domains**
2. Adicione seu domínio: `reframe.seudominio.com`
3. Configure o DNS:
   ```
   Tipo: CNAME
   Nome: reframe
   Conteúdo: seu-app.easypanel.app
   ```
4. Aguarde propagação (5-30 minutos)

---

## 🔍 Verificação de Logs

### Durante o Build
- Monitore os logs para verificar instalação de FFmpeg
- Verifique se todas as dependências Python foram instaladas
- Procure por erros de conexão

### Durante a Execução
- Logs de jobs processados
- Erros de upload (se houver)
- Status dos workers

### Comando para Ver Logs

```bash
# Via interface Easypanel
# Clique em "Logs" no painel do app

# Ou via terminal (se configurado)
easypanel logs reframe-endpoint
```

---

## 🐛 Troubleshooting

### Erro: "Build Failed"
**Causa:** Dependências não instaladas  
**Solução:** Verifique os logs de build, especialmente:
- FFmpeg instalado? (deve aparecer no log)
- Python 3.8+ disponível?

### Erro: "Port 8080 already in use"
**Causa:** Conflito de porta  
**Solução:** Deixe o Easypanel configurar automaticamente a porta

### Erro: "ModuleNotFoundError: mediapipe"
**Causa:** Dependências não instaladas  
**Solução:** Verifique se `requirements.txt` foi detectado

### Erro: "403 Forbidden" no Upload
**Causa:** Credenciais inválidas  
**Solução:** 
1. Verifique `SPACES_KEY` e `SPACES_SECRET`
2. Confirme que o bucket existe
3. Teste o endpoint `/v1/test/upload`

### Erro: "ffmpeg: command not found"
**Causa:** FFmpeg não instalado no container  
**Solução:** 
1. Verifique `nixpacks.toml` no GitHub
2. Re-faça o deploy
3. Force rebuild no Easypanel

### Vídeos não processando
**Causa:** URL inacessível ou formato inválido  
**Solução:**
1. Teste com URL pública de exemplo primeiro
2. Verifique formato do vídeo (MP4 recomendado)
3. Confira logs do container

---

## 📊 Monitoramento

### Métricas Importantes

1. **CPU Usage** - Monitor para picos durante reframing
2. **RAM Usage** - OpenCV + MediaPipe consome ~2GB por vídeo
3. **Queue Size** - Número de jobs na fila
4. **Active Workers** - Workers processando

### Endpoints de Monitoramento

```bash
# Status do serviço
GET /

# Listar todos os jobs
GET /v1/video/jobs

# Jobs por status
GET /v1/video/jobs?status=done
GET /v1/video/jobs?status=error
```

---

## 🔒 Segurança

### ⚠️ Ações Recomendadas (Fazer após deploy bem-sucedido)

1. **Implementar CORS**
   - Adicione ao `app.py`: 
   ```python
   from flask_cors import CORS
   CORS(app, resources={r"/*": {"origins": ["https://seudominio.com"]}})
   ```

2. **Rate Limiting**
   - Implemente limite de requisições por IP
   - Use Flask-Limiter

3. **Autenticação**
   - Adicione API keys
   - Valide em todas as rotas de processamento

---

## 📝 Checklist Final

### Antes do Deploy
- [x] Push para GitHub concluído
- [ ] Variáveis de ambiente configuradas
- [ ] Credenciais do DigitalOcean Spaces prontas
- [ ] Recursos do servidor definidos

### Durante o Deploy
- [ ] Build iniciado
- [ ] Logs de build sem erros
- [ ] App deployed successfully

### Pós-Deploy
- [ ] Health check funcionando
- [ ] Teste de upload funcionando
- [ ] Processamento de vídeo funcionando
- [ ] Logs sendo gerados corretamente

---

## 🎉 Resultado Esperado

Após configurar tudo, você terá:

1. **API pública funcional** em `https://seu-app.easypanel.app`
2. **Processamento assíncrono** de vídeos
3. **Upload automático** para DigitalOcean Spaces
4. **Sistema de fila** com múltiplos workers
5. **Monitoramento** via logs

---

## 📞 Suporte

### Documentos de Referência
- `REQUISITOS.md` - Requisitos técnicos detalhados
- `README.md` - Documentação completa da API
- `CHECKLIST_DEPLOY.md` - Checklist de deploy
- `RESUMO_EXECUTIVO.md` - Resumo executivo

### Links Úteis
- Repositório: https://github.com/leandrobosaipo/reframe-endpoint
- Easypanel Docs: https://easypanel.io/docs
- DigitalOcean Spaces: https://www.digitalocean.com/products/spaces

---

## ✅ Próximos Passos

1. **Configure o Easypanel** seguindo este guia (15 min)
2. **Teste a API** com os endpoints fornecidos (5 min)
3. **Monitore o sistema** por alguns dias
4. **Implemente melhorias** de segurança (CORS, rate limiting)

**Tempo total estimado:** 20-30 minutos

---

✨ **Boa sorte com o deploy!**

