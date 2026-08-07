#  API do Projeto Solicitações

Essa API é responsável por **inativar usuários com segurança** e **gerar relatórios complexos** para o aplicativo Solicitações.
[Portifólio do APP](https://github.com/gabrielhencastro/SolicitacoesApp)

---

##  Tecnologias Utilizadas
- Python / FastAPI
- Supabase / PyJWT
- Git & GitHub

---

##  Funcionalidades
- Inativação de Usuários: Utiliza JWT nativo do Supabase para garantir criptografia robusta e segurança avançada.
- Relatórios Complexos: Processa e valida requisições para geração de relatórios em PDF e Excel com o Pandas e FDPF, com controle de acesso por usuário e tratamento de erros.

---

##  requirements.txt

O arquivo requirements.txt deve conter as dependências principais:

fastapi
uvicorn
supabase
PyJWT
pandas
fpdf
python-dotenv

---

## Como Executar

### Executar Localmente
1. Clone o repositório:
   git clone https://github.com/seuusuario/solicitacoes_api.git
   cd solicitacoes_api

2. Crie e ative um ambiente virtual:
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows

3. Instale as dependências:
   pip install -r requirements.txt

4. Configure as variáveis de ambiente:
   - SUPABASE_URL
   - SUPABASE_SECRET_KEY
   - SUPABASE_JWKS_URL

5. Rode a API:
   uvicorn main:app --reload

A API estará disponível em: http://127.0.0.1:8000

---

### Deploy no Render
1. Crie um novo serviço Web Service no Render.
2. Aponte para este repositório.
3. Configure o Build Command:
   pip install -r requirements.txt
4. Configure o Start Command:
   uvicorn main:app --host 0.0.0.0 --port 10000
5. Defina as variáveis de ambiente (SUPABASE_URL, SUPABASE_KEY, JWT_SECRET) no painel do Render.
6. Após o deploy, a API estará acessível pela URL gerada pelo Render.

---

## Objetivo
Facilitar a gestão das informações, oferecendo uma API segura e escalável para controle de usuários e emissão de relatórios gerenciais.
