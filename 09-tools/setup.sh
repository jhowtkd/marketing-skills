#!/bin/bash
# Vibe Marketing - Setup Script
# Instala dependências e configura ambiente

echo "🚀 Vibe Marketing - Setup"
echo "=========================="
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado!"
    echo "Por favor, instale Python 3.8 ou superior:"
    echo "  - Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  - Mac: brew install python3"
    echo "  - Windows: https://python.org/downloads"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python encontrado: $PYTHON_VERSION"

# Verificar versão mínima
REQUIRED_VERSION="3.8"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo "❌ Python 3.8 ou superior necessário!"
    exit 1
fi

# Criar ambiente virtual (opcional)
echo ""
echo "📦 Configurando ambiente..."

# Verificar se requirements.txt existe
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt não encontrado!"
    exit 1
fi

# Instalar dependências
echo ""
echo "📥 Instalando dependências..."
pip3 install -r requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo "✅ Dependências instaladas com sucesso!"
else
    echo "❌ Erro ao instalar dependências"
    exit 1
fi

# Verificar instalação
echo ""
echo "🔍 Verificando instalação..."

python3 -c "import requests; import bs4; print('✅ requests e beautifulsoup4 OK')"

# Criar diretório de output se não existir
if [ ! -d "../08-output" ]; then
    mkdir -p ../08-output
    echo "✅ Diretório 08-output criado"
fi

echo ""
echo "=========================="
echo "✅ Setup completo!"
echo ""
echo "Próximos passos:"
echo "  1. Configure sua IDE (Codex/Kimi/Antigravity)"
echo "  2. Execute: python3 research_tools.py"
echo "  3. Comece a usar: @vibe [sua solicitação]"
echo ""
echo "📖 Documentação:"
echo "  - README.md"
echo "  - QUICKSTART.md"
echo "  - ARCHITECTURE.md"
echo ""
