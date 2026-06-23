#!/bin/zsh

echo "======================================================================"
echo "VERIFICAR MONGODB E BIGQUERY - Brasil Higher Education Disability ETL"
echo "======================================================================"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Verificar MongoDB
echo "1. Verificando MongoDB..."
echo "-----"

if command -v docker &> /dev/null; then
    status=$(docker-compose ps mongodb 2>&1 | grep -c "Up")
    if [ $status -gt 0 ]; then
        echo -e "${GREEN}OK${NC} MongoDB container está rodando"
    else
        echo -e "${RED}ERRO${NC} MongoDB container não está rodando"
        echo "   Inicie com: ./scripts/docker-start.sh"
    fi
else
    echo -e "${YELLOW}AVISO${NC} Docker não está instalado"
fi

# Testar conexão Python
python3 scripts/verify_mongodb.py 2>&1 | grep -q "OK"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}OK${NC} Conexão Python com MongoDB funcionando"
else
    echo -e "${RED}ERRO${NC} Conexão Python com MongoDB falhou"
fi

echo ""

# 2. Verificar BigQuery
echo "2. Verificando BigQuery..."
echo "-----"

if [ -f "credentials.json" ]; then
    echo -e "${GREEN}OK${NC} Arquivo credentials.json encontrado"
else
    echo -e "${RED}ERRO${NC} Arquivo credentials.json não encontrado"
    echo "   Coloque seu arquivo credentials.json na raiz do projeto"
fi

if [ -f ".env" ]; then
    echo -e "${GREEN}OK${NC} Arquivo .env encontrado"
else
    echo -e "${YELLOW}AVISO${NC} Arquivo .env não encontrado"
    echo "   Criando .env.example..."
fi

# Testar conexão BigQuery
python3 << 'EOF' 2>&1 | grep -q "OK"
from src.clients.bigquery_client import BigQueryClient
try:
    client = BigQueryClient()
    print("BigQuery: OK")
except:
    print("BigQuery: ERROR")
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}OK${NC} Conexão com BigQuery funcionando"
else
    echo -e "${RED}ERRO${NC} Conexão com BigQuery falhou"
fi

echo ""

# 3. Verificar arquivos de implementação
echo "3. Verificando arquivos de implementação..."
echo "-----"

python3 scripts/verify_implementation.py 2>&1 | grep -q "All implementation files"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}OK${NC} Todos os arquivos de implementação estão em lugar"
else
    echo -e "${RED}ERRO${NC} Alguns arquivos faltam"
fi

echo ""

# 4. Resumo
echo "======================================================================"
echo "RESUMO"
echo "======================================================================"
echo ""
echo "Para rodar o pipeline:"
echo ""
echo "  1. Iniciar MongoDB:"
echo "     ./scripts/docker-start.sh"
echo ""
echo "  2. Rodar pipeline (teste rápido com 100 registros):"
echo "     export ETL_LIMIT=100"
echo "     export ETL_START_YEAR=2022"
echo "     export ETL_END_YEAR=2022"
echo "     python3 main.py"
echo ""
echo "  3. Ver dados em tempo real:"
echo "     open http://localhost:8081"
echo ""
echo "  4. Ver documentação completa:"
echo "     cat COMO_RODAR.md"
echo ""
echo "======================================================================"
