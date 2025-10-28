#!/bin/bash
# 🧪 Script de Teste Automatizado - Reframe Endpoint
# Uso: ./test_server.sh [API_TOKEN]

# Configurações
SERVER_URL="https://codigo5-reframe-endpoint.ujhifl.easypanel.host"
API_TOKEN="${1:-}"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Testando Servidor Reframe-Endpoint${NC}"
echo -e "${BLUE}URL: ${SERVER_URL}${NC}"
echo "=================================="

# Função para testar endpoint
test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local headers="$3"
    local data="$4"
    local expected_status="$5"
    local description="$6"
    
    echo -e "\n${YELLOW}🔍 Testando: ${description}${NC}"
    echo "Endpoint: ${method} ${endpoint}"
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            $headers \
            -d "$data" \
            "${SERVER_URL}${endpoint}")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            $headers \
            "${SERVER_URL}${endpoint}")
    fi
    
    # Separar body e status code
    body=$(echo "$response" | head -n -1)
    status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✅ Status: ${status_code} (esperado: ${expected_status})${NC}"
        if [ -n "$body" ]; then
            echo -e "${GREEN}Response:${NC}"
            echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        fi
    else
        echo -e "${RED}❌ Status: ${status_code} (esperado: ${expected_status})${NC}"
        if [ -n "$body" ]; then
            echo -e "${RED}Response:${NC}"
            echo "$body"
        fi
    fi
}

# Teste 1: Health Check
test_endpoint "GET" "/" "" "" "200" "Health Check"

# Teste 2: Listar Jobs (sem token)
test_endpoint "GET" "/v1/video/jobs" "" "" "401" "Listar Jobs (sem token)"

# Teste 3: Listar Jobs (com token)
if [ -n "$API_TOKEN" ]; then
    test_endpoint "GET" "/v1/video/jobs" "-H 'X-Api-Token: $API_TOKEN'" "" "200" "Listar Jobs (com token)"
else
    echo -e "\n${YELLOW}⚠️  Token não fornecido - pulando testes que requerem autenticação${NC}"
    echo "Uso: $0 SEU_TOKEN_AQUI"
fi

# Teste 4: Enfileirar Reframe (sem token)
test_endpoint "POST" "/v1/video/reframe" "" '{"input_url": "https://exemplo.com/video.mp4"}' "401" "Enfileirar Reframe (sem token)"

# Teste 5: Enfileirar Reframe (com token)
if [ -n "$API_TOKEN" ]; then
    test_endpoint "POST" "/v1/video/reframe" "-H 'X-Api-Token: $API_TOKEN'" '{"input_url": "https://exemplo.com/video.mp4"}' "202" "Enfileirar Reframe (com token)"
fi

# Teste 6: Status de Job Inexistente
if [ -n "$API_TOKEN" ]; then
    test_endpoint "GET" "/v1/video/status/job_inexistente" "-H 'X-Api-Token: $API_TOKEN'" "" "404" "Status de Job Inexistente"
fi

# Teste 7: Download de Job Inexistente
if [ -n "$API_TOKEN" ]; then
    test_endpoint "GET" "/v1/video/download/job_inexistente" "-H 'X-Api-Token: $API_TOKEN'" "" "404" "Download de Job Inexistente"
fi

echo -e "\n${BLUE}=================================="
echo -e "🏁 Testes Concluídos${NC}"

# Resumo
echo -e "\n${BLUE}📋 Resumo dos Testes:${NC}"
echo "1. Health Check - deve retornar 200"
echo "2. Endpoints protegidos sem token - devem retornar 401"
echo "3. Endpoints protegidos com token - devem retornar códigos apropriados"
echo "4. Jobs inexistentes - devem retornar 404"

echo -e "\n${YELLOW}💡 Dicas:${NC}"
echo "- Se todos os testes passarem, o servidor está funcionando corretamente"
echo "- Se houver erros 502/503, verifique se o serviço está rodando no Easypanel"
echo "- Se houver erros 401, verifique se o API_TOKEN está configurado corretamente"
echo "- Se houver erros 500, verifique os logs da aplicação"

echo -e "\n${BLUE}🔗 URLs para teste manual:${NC}"
echo "Health Check: curl ${SERVER_URL}/"
echo "Com Token: curl -H 'X-Api-Token: SEU_TOKEN' ${SERVER_URL}/v1/video/jobs"
