# 🚀 Quick Start Guide

## Opção 1: Desenvolvimento Local (Recomendado)

### Pré-requisitos
- Python 3.11+ ✅ (você tem 3.13.7)
- Node.js 20+ ✅ (você tem v22.20.0)
- PostgreSQL 16 com pgvector

### Passo 1: PostgreSQL com Docker (apenas o DB)

```bash
# Iniciar apenas o PostgreSQL
docker compose up -d db

# Verificar se está rodando
docker compose ps
```

**Alternativa sem Docker**: Instale PostgreSQL localmente e adicione a extensão pgvector.

### Passo 2: Backend

```bash
# Criar e ativar ambiente virtual
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows CMD
.\.venv\Scripts\activate.bat

# Linux/macOS
source .venv/bin/activate

# Instalar dependências
pip install -r backend/requirements.txt

# Aplicar migrações
cd backend
alembic upgrade head
cd ..

# Rodar servidor (da raiz do projeto)
uvicorn app.main:app --reload --port 8080 --app-dir backend
```

O backend estará em: http://localhost:8080

### Passo 3: Frontend

Em outro terminal:

```bash
cd frontend

# Instalar dependências (inclui framer-motion)
npm install

# Rodar dev server
npm run dev
```

O frontend estará em: http://localhost:5173

### Passo 4: Configurar API Keys (Opcional)

Edite `.env` e adicione sua chave OpenAI:

```bash
OPENAI_API_KEY=sk-proj-...
```

Para web search (opcional):
```bash
WEB_SEARCH_PROVIDER=tavily
WEB_SEARCH_API_KEY=tvly-...
```

---

## Opção 2: Docker Compose (Se o erro for resolvido)

### Solução para o erro EOF

1. **Reiniciar Docker Desktop**
   - Fechar completamente o Docker Desktop
   - Abrir novamente
   - Esperar até estar 100% iniciado

2. **Limpar cache do Docker**

```bash
docker system prune -a
docker volume prune
```

3. **Aumentar recursos do Docker**
   - Docker Desktop → Settings → Resources
   - Aumentar Memory para pelo menos 4GB
   - Aumentar CPUs para 2+

4. **Tentar novamente**

```bash
docker compose up -d --build
```

### Verificar logs se der erro

```bash
# Ver logs de todos os serviços
docker compose logs -f

# Ver logs apenas do backend
docker compose logs -f backend

# Ver logs apenas do frontend
docker compose logs -f frontend
```

---

## 🧪 Testando

### 1. Upload de PDF

1. Abra http://localhost:5173
2. Arraste um PDF para a área de drop ou clique em "Upload PDFs"
3. Aguarde o processamento

### 2. Fazer uma pergunta

Digite uma pergunta sobre o documento e clique em "Send"

### 3. Ver sources com imagens

Verifique o painel lateral direito para ver:
- Páginas relevantes
- Similarity scores
- Imagens encontradas (clique para ampliar)

---

## 🐛 Troubleshooting

### Erro: "Connection refused" no backend

**Problema**: PostgreSQL não está rodando

**Solução**:
```bash
docker compose up -d db
# OU instalar PostgreSQL localmente
```

### Erro: "Module not found" no backend

**Problema**: Dependências não instaladas ou venv não ativado

**Solução**:
```bash
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

### Erro: "Cannot find module" no frontend

**Problema**: node_modules não instalado

**Solução**:
```bash
cd frontend
npm install
```

### Erro: Framer Motion não encontrado

**Solução**:
```bash
cd frontend
npm install framer-motion
```

### Migrações não aplicadas

```bash
cd backend
alembic upgrade head
cd ..
```

### Port já em uso

**Backend (8080)**:
```bash
# Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:8080 | xargs kill -9
```

**Frontend (5173)**:
```bash
# Windows
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:5173 | xargs kill -9
```

---

## 📝 Próximos Passos

1. **Adicionar sua API key** da OpenAI no `.env`
2. **Upload de PDF de teste** (use `samples/plano_negocios.pdf`)
3. **Fazer perguntas** sobre o documento
4. **Testar busca web** (configurar Tavily ou outro provider)
5. **Rodar testes**:
   ```bash
   # Unit tests
   pytest backend/tests/

   # Evaluation (precisa do backend rodando + PDF upado)
   export EVAL_DOCUMENT_ID="uuid-do-seu-doc"
   deepeval test run backend/evaluation/test_evaluate_rag.py
   ```

---

## 🎨 Features para Testar

- ✨ **Drag & Drop** de PDFs com feedback visual
- 🖼️ **Visualização de imagens** dos PDFs com modal full-screen
- 🎭 **Animações suaves** em todas as interações
- 📊 **Sources panel** com similarity scores
- 🌐 **Busca web** (quando configurada)
- 💬 **Chat streaming** com respostas token-by-token
- 🎯 **Modos**: Docs, Web, ou Auto

---

## 📚 Documentação Adicional

- `README.md` - Visão geral do projeto
- `ARCHITECTURE.md` - Arquitetura detalhada
- `CHANGELOG.md` - O que foi implementado
