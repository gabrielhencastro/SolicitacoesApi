import os
import pandas as pd
from datetime import datetime
from collections import Counter
from supabase import create_client, Client
from dotenv import load_dotenv
from fpdf import FPDF

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Inicializa FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carrega variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("As variáveis SUPABASE_URL e SUPABASE_PUBLISHABLE_KEY precisam estar configuradas!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

os.makedirs("temp", exist_ok=True)

# Modelo para o body da rota de relatório
class RelatorioParams(BaseModel):
    tipo_relatorio: int
    tipo_solicitacao: str | None = None
    status_solicitacao: str | None = None

# ------------------- ROTA DE RELATÓRIO -------------------
@app.post("/api/relatorio")
def gerar_relatorio(params: RelatorioParams, authorization: str = Header(...)):
    qtd_em_andamento = 0
    qtd_concluido = 0
    tipos_em_andamento = []
    tipos_concluido = []

    try:
        tipo_relatorio = params.tipo_relatorio
        tipo_solicitacao = params.tipo_solicitacao
        status_solicitacao = params.status_solicitacao

        if tipo_relatorio == 1:
            query = supabase.table('solicitacoes').select("*")
            if tipo_solicitacao:
                query = query.eq('tipo_solicitacao', tipo_solicitacao)
            if status_solicitacao:
                query = query.eq('status', status_solicitacao)
            response = query.execute()
            if response.data:
                df = pd.DataFrame(response.data)
                caminho_excel = "temp/relatorio_solicitacoes.xlsx"
                df.to_excel(caminho_excel, index=False)
                return FileResponse(caminho_excel, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        elif tipo_relatorio == 2:
            # Busca dados
            if not status_solicitacao or status_solicitacao == 'Em andamento':
                query_andamento = supabase.table('solicitacoes').select("tipo_solicitacao").eq('status', 'Em andamento')
                if tipo_solicitacao:
                    query_andamento = query_andamento.eq('tipo_solicitacao', tipo_solicitacao)
                dados_em_andamento = query_andamento.execute()
                qtd_em_andamento = len(dados_em_andamento.data)
                contador_em_andamento = Counter([item.get('tipo_solicitacao') for item in dados_em_andamento.data])
                tipos_em_andamento = [[tipo, total] for tipo, total in contador_em_andamento.items()]

            if not status_solicitacao or status_solicitacao == 'Concluido':
                query_concluido = supabase.table('solicitacoes').select("tipo_solicitacao").eq('status', 'Concluido')
                if tipo_solicitacao:
                    query_concluido = query_concluido.eq('tipo_solicitacao', tipo_solicitacao)
                dados_concluido = query_concluido.execute()
                qtd_concluido = len(dados_concluido.data)
                contador_concluido = Counter([item.get('tipo_solicitacao') for item in dados_concluido.data])
                tipos_concluido = [[tipo, total] for tipo, total in contador_concluido.items()]

            # Gera PDF
            pdf = FPDF(orientation="P", unit="mm", format="A4")
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 18)
            pdf.text(15, 15, "Relatorio de Metricas e Volumetria")

            # Cards
            pdf.set_font("Helvetica", "B", 20)
            pdf.text(20, 40, f"Em andamento: {qtd_em_andamento}")
            pdf.text(20, 50, f"Concluidas: {qtd_concluido}")

            caminho_pdf = "temp/relatorio_metricas.pdf"
            pdf.output(caminho_pdf)
            return FileResponse(caminho_pdf, media_type="application/pdf")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ------------------- ROTA DE DELETE USER -------------------
@app.delete("/api/delete-user")
def deletar_usuario(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Token inválido ou sessão expirada.")

        user_id = user_response.user.id
        supabase.auth.admin.delete_user(user_id)
        return {"status": "success", "message": f"Usuário {user_id} removido."}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
