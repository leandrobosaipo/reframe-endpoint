# 🧪 Comandos curl para Teste do Reframe Endpoint

## Configuração Base
```bash
# URL do servidor (ajuste conforme ambiente)
# Local:
BASE_URL="http://localhost:8080"

# Produção (Easypanel):
# BASE_URL="https://codigo5-reframe-endpoint.ujhifl.easypanel.host"

# Token de autenticação (ajuste conforme necessário)
API_TOKEN="seu_token_aqui"
```

**Nota:** O Swagger agora detecta automaticamente o domínio correto. Se estiver acessando via domínio público, o Swagger UI usará automaticamente a URL pública nos exemplos de curl.

---

## 1. Health Check
```bash
curl -s "${BASE_URL}/" | python3 -m json.tool
```

**Resposta esperada:**
```json
{
    "status": "success",
    "message": "Service is running",
    "data": {
        "service": "reframe-endpoint",
        "queue_size": 0,
        "workers": 2
    }
}
```

---

## 2. Métricas de Saúde Detalhadas
```bash
curl -s "${BASE_URL}/metrics/health" | python3 -m json.tool
```

---

## 3. Enfileirar Reframe (com vídeo remoto)
```bash
curl -X POST "${BASE_URL}/v1/video/reframe" \
  -H "Content-Type: application/json" \
  -H "X-Api-Token: ${API_TOKEN}" \
  -d '{
    "input_url": "https://exemplo.com/video.mp4"
  }' | python3 -m json.tool
```

**Resposta esperada:**
```json
{
    "status": "queued",
    "message": "processamento enfileirado",
    "job_id": "job_abc123def4"
}
```

---

## 4. Enfileirar Reframe (com vídeo local - file://)
```bash
curl -X POST "${BASE_URL}/v1/video/reframe" \
  -H "Content-Type: application/json" \
  -H "X-Api-Token: ${API_TOKEN}" \
  -d '{
    "input_url": "file:///caminho/completo/para/video.mp4"
  }' | python3 -m json.tool
```

---

## 5. Enfileirar Reframe (com input_path)
```bash
curl -X POST "${BASE_URL}/v1/video/reframe" \
  -H "Content-Type: application/json" \
  -H "X-Api-Token: ${API_TOKEN}" \
  -d '{
    "input_path": "/caminho/completo/para/video.mp4"
  }' | python3 -m json.tool
```

---

## 6. Verificar Status do Job
```bash
# Substitua JOB_ID pelo ID retornado no passo anterior
JOB_ID="job_abc123def4"

curl -s "${BASE_URL}/v1/video/status/${JOB_ID}" \
  -H "X-Api-Token: ${API_TOKEN}" | python3 -m json.tool
```

**Resposta esperada (com metadados):**
```json
{
    "status": "success",
    "data": {
        "job_id": "job_abc123def4",
        "status": "done",
        "stage": "done",
        "progress": 100.0,
        "metrics": {
            "frames_processed": 300,
            "fps": 30.0,
            "faces_detected_sum": 150,
            "status": "success",
            "input_metadata": {
                "has_audio": true,
                "has_video": true,
                "duration": 10.0,
                "video_codec": "h264",
                "audio_codec": "aac",
                "width": 1920,
                "height": 1080,
                "fps": 30.0
            },
            "output_metadata": {
                "has_audio": true,
                "has_video": true,
                "duration": 10.0,
                "video_codec": "h264",
                "audio_codec": "aac",
                "width": 608,
                "height": 1080,
                "fps": 30.0
            },
            "mux_info": {
                "has_source_audio": true,
                "audio_source": "original"
            }
        }
    }
}
```

---

## 7. Verificar Status de Job com Erro (exemplo)
```bash
# Se houver erro, a resposta incluirá:
# {
#   "status": "error",
#   "error": "mensagem de erro",
#   "error_type": "RuntimeError",
#   "error_category": "mux_error",
#   "stage": "muxing"
# }
```

---

## 8. Listar Todos os Jobs
```bash
curl -s "${BASE_URL}/v1/video/jobs" \
  -H "X-Api-Token: ${API_TOKEN}" | python3 -m json.tool
```

---

## 9. Listar Jobs por Status
```bash
# Apenas jobs com erro
curl -s "${BASE_URL}/v1/video/jobs?status=error" \
  -H "X-Api-Token: ${API_TOKEN}" | python3 -m json.tool

# Apenas jobs concluídos
curl -s "${BASE_URL}/v1/video/jobs?status=done" \
  -H "X-Api-Token: ${API_TOKEN}" | python3 -m json.tool
```

---

## 10. Download do Vídeo Processado
```bash
JOB_ID="job_abc123def4"

curl -s "${BASE_URL}/v1/video/download/${JOB_ID}" \
  -H "X-Api-Token: ${API_TOKEN}" \
  -o "reframe_output.mp4"
```

---

## 11. Métricas KPIs
```bash
curl -s "${BASE_URL}/metrics/kpi" | python3 -m json.tool
```

**Resposta esperada:**
```json
{
    "status": "success",
    "data": {
        "total_jobs": 10,
        "jobs_by_status": {
            "done": 8,
            "error": 1,
            "queued": 1
        },
        "success_rate_percent": 88.89,
        "average_processing_time_seconds": 45.2
    }
}
```

---

## 12. Histórico de Jobs
```bash
curl -s "${BASE_URL}/metrics/history?limit=10" | python3 -m json.tool
```

---

## 13. Upload de Arquivo
```bash
curl -X POST "${BASE_URL}/v1/uploads" \
  -H "X-Api-Token: ${API_TOKEN}" \
  -F "file=@/caminho/para/video.mp4" \
  -F "folder=upload/reframe" \
  -F "ttl_days=7" | python3 -m json.tool
```

---

## 14. Reframe usando Upload ID
```bash
UPLOAD_ID="upl_abc123def4"

curl -X POST "${BASE_URL}/v1/video/reframe" \
  -H "Content-Type: application/json" \
  -H "X-Api-Token: ${API_TOKEN}" \
  -d "{
    \"input_upload_id\": \"${UPLOAD_ID}\"
  }" | python3 -m json.tool
```

---

## 15. Teste com Modo Debug
```bash
curl -X POST "${BASE_URL}/v1/video/reframe" \
  -H "Content-Type: application/json" \
  -H "X-Api-Token: ${API_TOKEN}" \
  -d '{
    "input_url": "file:///caminho/para/video.mp4",
    "debug": true
  }' | python3 -m json.tool
```

---

## 16. Verificar Swagger UI
```bash
# Abra no navegador:
open "${BASE_URL}/docs"
# ou
echo "Acesse: ${BASE_URL}/docs"
```

---

## 🧪 Testes Específicos para Nova Funcionalidade

### Teste 1: Vídeo SEM áudio (deve gerar áudio silencioso)
```bash
# Primeiro, crie um vídeo sem áudio para teste:
# ffmpeg -i video_com_audio.mp4 -c:v copy -an video_sem_audio.mp4

curl -X POST "${BASE_URL}/v1/video/reframe" \
  -H "Content-Type: application/json" \
  -H "X-Api-Token: ${API_TOKEN}" \
  -d '{
    "input_url": "file:///caminho/para/video_sem_audio.mp4"
  }' | python3 -m json.tool

# Verifique o status e confirme que mux_info.audio_source = "generated_silent"
```

### Teste 2: Verificar Metadados Completos
```bash
JOB_ID="job_abc123def4"

curl -s "${BASE_URL}/v1/video/status/${JOB_ID}" \
  -H "X-Api-Token: ${API_TOKEN}" | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d['data']['metrics'], indent=2))"
```

---

## 📝 Script de Teste Completo

```bash
#!/bin/bash
BASE_URL="http://localhost:8080"
API_TOKEN="seu_token_aqui"

echo "🧪 Testando Reframe Endpoint"
echo "============================"

# 1. Health Check
echo -e "\n1. Health Check:"
curl -s "${BASE_URL}/" | python3 -m json.tool

# 2. Enfileirar job
echo -e "\n2. Enfileirar Reframe:"
RESPONSE=$(curl -s -X POST "${BASE_URL}/v1/video/reframe" \
  -H "Content-Type: application/json" \
  -H "X-Api-Token: ${API_TOKEN}" \
  -d '{"input_url": "file:///caminho/para/video.mp4"}')

echo "$RESPONSE" | python3 -m json.tool

# Extrair job_id
JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['job_id'])")

echo -e "\n3. Aguardando processamento..."
sleep 5

# 3. Verificar status
echo -e "\n4. Status do Job (${JOB_ID}):"
curl -s "${BASE_URL}/v1/video/status/${JOB_ID}" \
  -H "X-Api-Token: ${API_TOKEN}" | python3 -m json.tool

# 4. Métricas
echo -e "\n5. Métricas KPIs:"
curl -s "${BASE_URL}/metrics/kpi" | python3 -m json.tool
```

---

## 🔍 Verificar Logs do Servidor

Os logs do servidor mostrarão:
- Detecção de áudio (`has_source_audio: true/false`)
- Fonte do áudio usado (`audio_source: original/generated_silent`)
- Metadados extraídos do input e output
- Erros detalhados com categoria e tipo

---

## ⚠️ Notas Importantes

1. **Token de Autenticação**: Se `API_TOKEN` não estiver configurado no `.env`, os endpoints públicos funcionarão sem autenticação.

2. **Vídeos Locais**: Use `file://` ou `input_path` para vídeos locais. Certifique-se de que o caminho é absoluto.

3. **Metadados**: Os metadados completos estarão disponíveis apenas após o processamento concluir (`status: done`).

4. **Erros**: Erros agora incluem `error_category` e `error_type` para facilitar diagnóstico.

5. **Áudio Silencioso**: Quando um vídeo sem áudio é processado, o sistema gera automaticamente uma trilha silenciosa (stereo, 44.1kHz, AAC).

