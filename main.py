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
import base64
import json

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
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY") 
SUPABASE_JWKS_URL = os.environ.get("SUPABASE_JWKS_URL")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY or not SUPABASE_JWKS_URL:
    raise ValueError("Variáveis SUPABASE_URL, SUPABASE_SECRET_KEY e SUPABASE_JWKS_URL precisam estar configuradas!")

admin_client: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

os.makedirs("temp", exist_ok=True)

# Modelo para o body da rota de relatório
class RelatorioParams(BaseModel):
    tipo_relatorio: int
    tipo_solicitacao: str | None = None
    status_solicitacao: str | None = None

# ------------------- ROTA DE RELATÓRIO -------------------
@app.post("/api/relatorio")
def gerar_relatorio(params: RelatorioParams, authorization: str = Header(...)):
    # Inicialização
    qtd_em_andamento = 0
    qtd_concluido = 0
    tipos_em_andamento = []
    tipos_concluido = []

    try:      
        tipo_relatorio = params.tipo_relatorio
        tipo_solicitacao = params.tipo_solicitacao
        status_solicitacao = params.status_solicitacao

        if tipo_relatorio == 1:
            query = admin_client.table('solicitacoes').select("*")
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
            # 1. Busca os dados no Supabase
            if not status_solicitacao or status_solicitacao == 'Em andamento':
                query_andamento = admin_client.table('solicitacoes').select("tipo_solicitacao").eq('status', 'Em andamento')
                if tipo_solicitacao:
                    query_andamento = query_andamento.eq('tipo_solicitacao', tipo_solicitacao)
                dados_em_andamento = query_andamento.execute()
                qtd_em_andamento = len(dados_em_andamento.data)
                contador_em_andamento = Counter([item.get('tipo_solicitacao') for item in dados_em_andamento.data])
                tipos_em_andamento = [[tipo, total] for tipo, total in contador_em_andamento.items()]
            
            if not status_solicitacao or status_solicitacao == 'Concluido':
                query_concluido = admin_client.table('solicitacoes').select("tipo_solicitacao").eq('status', 'Concluido')
                if tipo_solicitacao:
                    query_concluido = query_concluido.eq('tipo_solicitacao', tipo_solicitacao)
                dados_concluido = query_concluido.execute()
                qtd_concluido = len(dados_concluido.data)
                contador_concluido = Counter([item.get('tipo_solicitacao') for item in dados_concluido.data])
                tipos_concluido = [[tipo, total] for tipo, total in contador_concluido.items()]

            # 2. Configurações do PDF via fpdf2
            pdf = FPDF(orientation="P", unit="mm", format="A4")
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            # Cabeçalho Azul Escuro
            pdf.set_fill_color(30, 58, 138) # #1e3a8a
            pdf.rect(0, 0, 210, 38, "F")
            
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 18)
            pdf.text(15, 15, "Relatorio de Metricas e Volumetria")

            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 14)
            pdf.text(160, 15, "Heimdall Solutions")
            
            
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(147, 197, 253) # Azul claro
            pdf.text(15, 22, "Analise de solicitacoes agrupadas por status do sistema")
            
            # Badge do Filtro Ativo
            filtro_txt = f"Filtro Ativo: {tipo_solicitacao if tipo_solicitacao else 'Todos os tipos'}"
            pdf.set_fill_color(37, 99, 235) # #2563eb
            pdf.set_xy(15, 26)
            # Atualizado na v2.5+: new_x e new_y controlam para onde o cursor vai depois de desenhar a célula
            pdf.cell(pdf.get_string_width(filtro_txt) + 6, 6, filtro_txt, border=0, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
            
            # Pula o espaço do cabeçalho (Corrigido de set_ln para ln)
            pdf.ln(12)
            
            # Título da Seção: Resumo Operacional
            pdf.set_text_color(30, 58, 138)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Resumo Operacional", new_x="LMARGIN", new_y="NEXT")
            
            # Linha decorativa azul do título
            pdf.set_draw_color(37, 99, 235)
            pdf.set_line_width(0.8) # Corrigido de set_thickness para set_line_width
            pdf.line(15, pdf.get_y(), 45, pdf.get_y())
            pdf.ln(4)
            
            # CARDS DE MÉTRICAS (Lado a lado usando colunas)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(100, 116, 139) # Cinza
            pdf.set_draw_color(226, 232, 240) # Borda cinza clara
            pdf.set_fill_color(255, 255, 255)
            
            y_cards = pdf.get_y()
            # Card 1: Em Andamento
            pdf.set_xy(15, y_cards)
            pdf.cell(88, 22, "", border=1, fill=True)
            pdf.text(20, y_cards + 6, "EM ANDAMENTO")
            pdf.set_text_color(30, 58, 138)
            pdf.set_font("Helvetica", "B", 20)
            pdf.text(20, y_cards + 16, str(qtd_em_andamento))
            
            # Card 2: Concluído
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(100, 116, 139)
            pdf.set_xy(107, y_cards)
            pdf.cell(88, 22, "", border=1, fill=True)
            pdf.text(112, y_cards + 6, "CONCLUIDAS")
            pdf.set_text_color(30, 58, 138)
            pdf.set_font("Helvetica", "B", 20)
            pdf.text(112, y_cards + 16, str(qtd_concluido))
            
            pdf.set_xy(15, y_cards + 26)
            
            # Função auxiliar para desenhar as tabelas de forma elegante
            def gerar_tabela(titulo, lista_dados, total_geral):
                pdf.set_text_color(30, 58, 138)
                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 8, titulo, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
                
                # Cabeçalho da Tabela
                pdf.set_fill_color(51, 65, 85) # #334155
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 9.5)
                
                pdf.cell(90, 8, " Tipo de Solicitacao", border=0, fill=True)
                pdf.cell(60, 8, " Proporcao", border=0, fill=True)
                pdf.cell(30, 8, "Qtd ", border=0, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
                
                if not lista_dados:
                    pdf.set_text_color(148, 163, 184)
                    pdf.set_font("Helvetica", "", 9.5)
                    pdf.cell(180, 10, "Nenhum registro encontrado", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
                    pdf.ln(6)
                    return

                # Linhas da tabela
                zebra = False
                for item in lista_dados:
                    pdf.set_font("Helvetica", "", 9.5)
                    pdf.set_text_color(30, 41, 59)
                    
                    # Fundo zebrado
                    bg_color = (241, 245, 249) if zebra else (255, 255, 255)
                    pdf.set_fill_color(*bg_color)
                    zebra = not zebra
                    
                    current_y = pdf.get_y()
                    
                    # Coluna 1: Nome do tipo
                    pdf.cell(90, 8, f" {item[0]}", border="B", fill=True)
                    
                    # Coluna 2: Barra de Progresso/Proporção simulada
                    pdf.cell(60, 8, "", border="B", fill=True)
                    porcentagem = (item[1] / total_geral) if total_geral > 0 else 0
                    largura_barra = 50 * porcentagem
                    
                    # Desenha a barra por cima do fundo da célula
                    if largura_barra > 0:
                        pdf.set_fill_color(59, 130, 246) # Azul da barra
                        pdf.rect(107, current_y + 2.5, largura_barra, 3, "F")
                    
                    # Coluna 3: Quantidade
                    pdf.set_fill_color(*bg_color)
                    pdf.set_font("Helvetica", "B", 9.5)
                    pdf.cell(30, 8, f"{item[1]} ", border="B", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
                    
                pdf.ln(6)

            # Renderiza as duas tabelas
            gerar_tabela("Detalhamento: Em Andamento por Tipo", tipos_em_andamento, qtd_em_andamento)
            gerar_tabela("Detalhamento: Concluidas por Tipo", tipos_concluido, qtd_concluido)
            
            # Rodapé com data
            data_atual = datetime.now().strftime("%d/%m/%Y as %H:%M")
            pdf.set_y(-15)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(148, 163, 184)
            pdf.cell(0, 10, f"Relatorio Gerencial . Extraido em {data_atual} de forma automatica, HEIMDALL SOLUTIONS", align="C")

            # Salva o arquivo final
            caminho_pdf = "temp/relatorio_metricas.pdf"
            pdf.output(caminho_pdf)
            print(f"PDF Gerencial criado com sucesso em: {caminho_pdf}")
            return FileResponse("temp/relatorio_metricas.pdf", media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ------------------- ROTA DE DELETE USER -------------------
@app.delete("/api/delete-user")
def deletar_usuario(authorization: str = Header(...)):
    try:
        # 1. Pega o token puro
        token = authorization.replace("Bearer ", "").strip()

        # 2. Decodifica o payload (parte do meio) na raça com Python puro
        payload_b64 = token.split(".")[1]
        # Corrige o padding do base64 nativo caso necessário
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload_json = base64.b64decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)

        # 3. Pega o ID do usuário
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401, detail="Token sem o ID do usuário."
            )

        admin_client.auth.admin.delete_user(user_id)

        return {
            "status": "success",
            "message": f"Usuário {user_id} removido com sucesso.",
        }

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Erro ao processar: {str(e)}"
        )