# 🚀 Como Iniciar o Projeto

## Método Mais Fácil (3 Passos)

### 1️⃣ Abra o Docker Desktop
- Clique no ícone do Docker Desktop
- Aguarde até ficar verde/pronto

### 2️⃣ Execute o script de setup
Duplo-clique em: `start-local.bat`

Isso vai:
- ✅ Iniciar o PostgreSQL no Docker
- ✅ Aplicar migrações do banco
- ✅ Mostrar os comandos para rodar backend e frontend

### 3️⃣ Abra 2 terminais e rode:

**Terminal 1 - Backend:**
- Duplo-clique em: `run-backend.bat`
- Ou execute manualmente:
  ```bash
  .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8080 --app-dir backend
  ```
- Backend estará em: http://localhost:8080

**Terminal 2 - Frontend:**
- Duplo-clique em: `run-frontend.bat`
- Ou execute manualmente:
  ```bash
  cd frontend
  npm install
  npm run dev
  ```
- Frontend estará em: http://localhost:5173

---

## ✅ Verificar se Funcionou

1. Abra http://localhost:5173
2. Você deve ver a interface moderna com gradientes azul/roxo
3. Arraste um PDF para testar
4. Faça uma pergunta sobre o documento

---

## 🐛 Problemas Comuns

### "Docker não está rodando"
- **Solução**: Abra o Docker Desktop e aguarde iniciar completamente

### "Port 8080 already in use"
- **Solução**: Mude a porta no comando backend:
  ```bash
  .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8081 --app-dir backend
  ```
  E atualize `.env`:
  ```
  VITE_API_BASE=http://localhost:8081
  ```

### "Module not found: framer-motion"
- **Solução**:
  ```bash
  cd frontend
  npm install framer-motion
  ```

### "Cannot connect to database"
- **Solução**: Verificar se o PostgreSQL está rodando:
  ```bash
  docker compose ps
  ```
  Se não estiver, rodar:
  ```bash
  docker compose up -d db
  ```

### Migrações não aplicadas
```bash
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
cd ..
```

---

## 🎯 Configuração Opcional

### Adicionar OpenAI API Key
Edite o arquivo `.env` e adicione:
```
OPENAI_API_KEY=sk-proj-sua-chave-aqui
```

### Ativar Busca Web (Tavily)
1. Obtenha uma chave em: https://tavily.com
2. Edite `.env`:
   ```
   WEB_SEARCH_PROVIDER=tavily
   WEB_SEARCH_API_KEY=tvly-sua-chave
   ```

---

## 📚 Próximos Passos

1. ✅ Rodar o projeto (você está aqui!)
2. 📤 Upload do PDF de teste: `samples/plano_negocios.pdf`
3. 💬 Fazer perguntas sobre o documento
4. 🖼️ Testar visualização de imagens (clique nas thumbnails)
5. 🎨 Explorar as animações (drag & drop, hover effects)
6. 🧪 Rodar testes: `pytest backend/tests/`

---

## 📖 Documentação Completa

- `README.md` - Visão geral completa
- `ARCHITECTURE.md` - Detalhes da arquitetura
- `CHANGELOG.md` - Features implementadas
- `QUICKSTART.md` - Guia detalhado de setup
