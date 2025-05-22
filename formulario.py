import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import re
import requests
import io
from typing import Optional, Dict
import tempfile
import os
from pathlib import Path
from fpdf import FPDF
import time
import hashlib
import smtplib
import random
import ssl
from email.message import EmailMessage
import json
import shutil
import base64
from github import Github, InputGitTreeElement
import git

# Configuração inicial
st.set_page_config(layout="wide")

# Adicione isso junto com as outras configurações iniciais
GITHUB_REPO = "https://github.com/Alliabson/sistemaimobiliario"  # Substitua pelo seu repositório
GITHUB_TOKEN = st.secrets.get("Iv23liEu3rsT2UMxPPLN", "")  # Armazene o token nos segredos do Streamlit
BACKUP_FILE_NAME = "celeste_backup.db"

# Configuração de diretório persistente
DATA_DIR = Path(__file__).parent / "persistent_data"
DATA_DIR.mkdir(exist_ok=True)
DB_NAME = str(DATA_DIR / "celeste.db")
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# Pré-carregar a logo (opcional)
LOGO_PATH = 'Logo_pdf.png'
LOGO_CACHE = None
try:
    LOGO_CACHE = open(LOGO_PATH, 'rb').read()
except Exception as e:
    st.warning(f"Não foi possível carregar a logo: {e}")

# Configurações de e-mail
EMAIL_REMETENTE = "alli@imobiliariaceleste.com.br"
SENHA_APP = "jzix jalk dnkx wreq"

# Função para criar hash de senha
def criar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# Funções de e-mail
def gerar_codigo_autenticacao():
    return str(random.randint(100000, 999999))

def enviar_email(destinatario, codigo):
    assunto = "Código de autenticação - Redefinição de senha"
    corpo = f"Seu código de autenticação é: {codigo}\n\nUse este código para redefinir sua senha."

    msg = EmailMessage()
    msg['Subject'] = assunto
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = destinatario
    msg.set_content(corpo)

    contexto = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=contexto) as smtp:
            smtp.login(EMAIL_REMETENTE, SENHA_APP)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

# Funções de backup e restauração
ddef fazer_backup_banco_dados():
    try:
        # Backup local
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = str(BACKUP_DIR / f"db_backup_{timestamp}.db")
        shutil.copy2(DB_NAME, backup_path)
        
        # Backup em CSV
        conn = sqlite3.connect(DB_NAME)
        tabelas = ['usuarios', 'clientes_pf', 'clientes_pj', 'pessoas_vinculadas_pj']
        
        for tabela in tabelas:
            try:
                df = pd.read_sql(f'SELECT * FROM {tabela}', conn)
                df.to_csv(str(BACKUP_DIR / f"{tabela}_backup_{timestamp}.csv"), index=False)
            except Exception as e:
                st.error(f"Erro ao fazer backup da tabela {tabela}: {e}")
        
        conn.close()
        
        # Backup no GitHub
        if GITHUB_TOKEN:
            fazer_backup_github()
        
        return True
    except Exception as e:
        st.error(f"Erro ao fazer backup: {e}")
        return False
def restaurar_backup(backup_path):
    try:
        # Fecha todas as conexões existentes
        if 'conn' in locals():
            conn.close()
        
        # Copia o backup para o local do banco de dados principal
        shutil.copy2(backup_path, DB_NAME)
        
        st.success("Backup restaurado com sucesso!")
        st.rerun()
        return True
    except Exception as e:
        st.error(f"Erro ao restaurar backup: {e}")
        return False

# Função para criar tabelas do banco de dados
def criar_tabelas():
    # Garante que o diretório existe
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        nome_completo TEXT NOT NULL,
        cpf TEXT,
        email TEXT,
        telefone TEXT,
        imobiliaria TEXT,
        is_admin INTEGER DEFAULT 0,
        data_criacao TEXT,
        token_recuperacao TEXT,
        token_validade TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes_pf (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        genero TEXT,
        data_nascimento TEXT,
        celular TEXT NOT NULL,
        cpf TEXT NOT NULL,
        email TEXT,  
        nacionalidade TEXT,
        profissao TEXT,
        estado_civil TEXT,
        regime_casamento TEXT,
        uniao_estavel TEXT,
        cep TEXT,
        endereco TEXT,
        numero TEXT,
        bairro TEXT,
        cidade TEXT,
        estado TEXT,
        nome_conjuge TEXT,
        genero_conjuge TEXT,
        data_nascimento_conjuge TEXT,
        cpf_conjuge TEXT,
        email_conjuge TEXT,  
        celular_conjuge TEXT,
        nacionalidade_conjuge TEXT,
        profissao_conjuge TEXT,
        estado_civil_conjuge TEXT,
        regime_casamento_conjuge TEXT,
        uniao_estavel_conjuge TEXT,
        cep_conjuge TEXT,
        endereco_conjuge TEXT,
        numero_conjuge TEXT,
        bairro_conjuge TEXT,
        cidade_conjuge TEXT,
        estado_conjuge TEXT,
        data_cadastro TEXT,
        corretor TEXT,
        imobiliaria TEXT,
        numero_negocio TEXT,
        usuario_id INTEGER,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes_pj (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        razao_social TEXT NOT NULL,
        cnpj TEXT NOT NULL,
        email TEXT,
        telefone_empresa TEXT,
        cep_empresa TEXT,
        endereco_empresa TEXT,
        numero_empresa TEXT,
        bairro_empresa TEXT,
        cidade_empresa TEXT,
        estado_empresa TEXT,
        genero_administrador TEXT,
        nome_administrador TEXT NOT NULL,
        data_nascimento_administrador TEXT,
        cpf_administrador TEXT NOT NULL,
        celular_administrador TEXT NOT NULL,
        email_administrador TEXT,
        nacionalidade_administrador TEXT,
        profissao_administrador TEXT,
        estado_civil_administrador TEXT,
        regime_casamento_administrador TEXT,
        uniao_estavel_administrador TEXT,
        cep_administrador TEXT,
        endereco_administrador TEXT,
        numero_administrador TEXT,
        bairro_administrador TEXT,
        cidade_administrador TEXT,
        estado_administrador TEXT,
        data_cadastro TEXT,
        corretor TEXT,
        imobiliaria TEXT,
        numero_negocio TEXT,
        usuario_id INTEGER,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pessoas_vinculadas_pj (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        dados_pessoa TEXT NOT NULL,  -- JSON com todos os dados da pessoa
        FOREIGN KEY(empresa_id) REFERENCES clientes_pj(id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Criar tabelas se não existirem
criar_tabelas()

# Tentar restaurar backup do GitHub ao iniciar
if 'backup_restaurado' not in st.session_state and GITHUB_TOKEN:
    if restaurar_backup_github():
        st.session_state['backup_restaurado'] = True
        st.toast("Backup do GitHub restaurado com sucesso!", icon="✅")
    else:
        st.toast("Usando banco de dados local", icon="ℹ️")
        
# Funções para pessoas vinculadas PJ
def adicionar_pessoa_vinculada(empresa_id, dados_pessoa):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    dados_json = json.dumps(dados_pessoa, ensure_ascii=False)
    cursor.execute('''
    INSERT INTO pessoas_vinculadas_pj (empresa_id, dados_pessoa)
    VALUES (?, ?)
    ''', (empresa_id, dados_json))
    
    conn.commit()
    conn.close()

def obter_pessoas_vinculadas(empresa_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, dados_pessoa FROM pessoas_vinculadas_pj
    WHERE empresa_id = ?
    ''', (empresa_id,))
    
    pessoas = []
    for row in cursor.fetchall():
        pessoa = json.loads(row[1])
        pessoa['id'] = row[0]  # Adiciona o ID do registro
        pessoas.append(pessoa)
    
    conn.close()
    return pessoas

def remover_pessoa_vinculada(pessoa_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    DELETE FROM pessoas_vinculadas_pj
    WHERE id = ?
    ''', (pessoa_id,))
    
    conn.commit()
    conn.close()

def atualizar_pessoa_vinculada(pessoa_id, dados_pessoa):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    dados_json = json.dumps(dados_pessoa, ensure_ascii=False)
    cursor.execute('''
    UPDATE pessoas_vinculadas_pj
    SET dados_pessoa = ?
    WHERE id = ?
    ''', (dados_json, pessoa_id))
    
    conn.commit()
    conn.close()

# Funções de autenticação
def verificar_login(username, senha):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, username, senha_hash, nome_completo, is_admin, email 
    FROM usuarios 
    WHERE username = ?
    ''', (username,))
    
    usuario = cursor.fetchone()
    conn.close()
    
    if usuario:
        senha_hash = criar_hash(senha)
        if usuario[2] == senha_hash:
            return {
                'id': usuario[0],
                'username': usuario[1],
                'nome_completo': usuario[3],
                'is_admin': usuario[4],
                'email': usuario[5]
            }
    return None
    
if 'logado' in st.session_state and st.session_state['logado']:
    # Fazer backup a cada 24 horas
    if 'ultimo_backup' not in st.session_state or \
       (datetime.now() - st.session_state['ultimo_backup']).days >= 1:
        if fazer_backup_banco_dados():
            st.session_state['ultimo_backup'] = datetime.now()
            st.toast("Backup automático realizado com sucesso!", icon="💾")
            
def cadastrar_usuario(username, senha, nome_completo, cpf, email, telefone, imobiliaria, is_admin=False):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        senha_hash = criar_hash(senha)
        cursor.execute('''
        INSERT INTO usuarios (username, senha_hash, nome_completo, cpf, email, telefone, imobiliaria, is_admin, data_criacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, senha_hash, nome_completo, cpf, email, telefone, imobiliaria, 1 if is_admin else 0, 
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        gerar_backup_credenciais()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
def fazer_backup_github():
    """Faz backup do banco de dados para o GitHub"""
    try:
        # Conectar ao GitHub
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        
        # Ler o conteúdo do banco de dados
        with open(DB_NAME, 'rb') as f:
            content = f.read()
        
        # Codificar em base64
        content_b64 = base64.b64encode(content).decode('utf-8')
        
        # Verificar se o arquivo já existe
        try:
            file = repo.get_contents(BACKUP_FILE_NAME)
            # Atualizar arquivo existente
            repo.update_file(BACKUP_FILE_NAME, 
                           f"Backup automático {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                           content_b64, 
                           file.sha)
        except:
            # Criar novo arquivo
            repo.create_file(BACKUP_FILE_NAME, 
                           f"Backup automático {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                           content_b64)
        
        return True
    except Exception as e:
        st.error(f"Erro ao fazer backup no GitHub: {e}")
        return False

def restaurar_backup_github():
    """Restaura o backup do GitHub"""
    try:
        # Conectar ao GitHub
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        
        # Obter o arquivo de backup
        file = repo.get_contents(BACKUP_FILE_NAME)
        content = base64.b64decode(file.content)
        
        # Salvar localmente
        with open(DB_NAME, 'wb') as f:
            f.write(content)
        
        # Recarregar dados
        if 'clientes_pf' in st.session_state:
            st.session_state.clientes_pf = carregar_clientes_pf(
                st.session_state['usuario']['id'] if not st.session_state['usuario']['is_admin'] else None
            )
        
        if 'clientes_pj' in st.session_state:
            st.session_state.clientes_pj = carregar_clientes_pj(
                st.session_state['usuario']['id'] if not st.session_state['usuario']['is_admin'] else None
            )
        
        return True
    except Exception as e:
        st.warning(f"Não foi possível restaurar backup do GitHub: {e}")
        return False

def gerar_backup_credenciais():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql('SELECT username, nome_completo, cpf, email, telefone, imobiliaria FROM usuarios', conn)
    conn.close()
    
    os.makedirs('backups', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'backups/credenciais_{timestamp}.csv'
    df.to_csv(backup_path, index=False)

def listar_usuarios():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, nome_completo, is_admin FROM usuarios')
    usuarios = cursor.fetchall()
    conn.close()
    return usuarios

def gerar_token_recuperacao(username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT email FROM usuarios WHERE username = ?', (username,))
    usuario = cursor.fetchone()
    
    if not usuario:
        return None
    
    token = gerar_codigo_autenticacao()
    validade = (datetime.now() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('UPDATE usuarios SET token_recuperacao = ?, token_validade = ? WHERE username = ?',
                  (token, validade, username))
    conn.commit()
    conn.close()
    
    # Enviar e-mail com o token
    if enviar_email(usuario[0], token):
        return token, usuario[0]
    return None

def validar_token(username, token):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT token_recuperacao, token_validade FROM usuarios WHERE username = ?', (username,))
    dados = cursor.fetchone()
    conn.close()
    
    if not dados or not dados[0] or not dados[1]:
        return False
    
    if dados[0] == token and datetime.now() < datetime.strptime(dados[1], '%Y-%m-%d %H:%M:%S'):
        return True
    
    return False

def alterar_senha(username, nova_senha):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    senha_hash = criar_hash(nova_senha)
    cursor.execute('UPDATE usuarios SET senha_hash = ?, token_recuperacao = NULL, token_validade = NULL WHERE username = ?',
                  (senha_hash, username))
    conn.commit()
    conn.close()
    gerar_backup_credenciais()

def verificar_admin_padrao():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM usuarios WHERE is_admin = 1')
    admin = cursor.fetchone()
    
    if not admin:
        cadastrar_usuario('admin', 'admin', 'Administrador Padrão', 
                         '000.000.000-00', 'admin@example.com', '(00) 00000-0000', 
                         'Admin Imobiliária', True)
        st.toast("Usuário admin padrão criado (login: admin, senha: admin)", icon="🔑")
    conn.close()

verificar_admin_padrao()

# Funções auxiliares
def formatar_data_ptbr(data):
    if pd.isna(data) or data == "" or data is None:
        return ""
    if isinstance(data, str):
        try:
            if re.match(r'\d{2}/\d{2}/\d{4}', data):
                return data
            return datetime.strptime(data, '%Y-%m-%d').strftime('%d/%m/%Y')
        except:
            return data
    return data.strftime('%d/%m/%Y')

def formatar_cpf(cpf: str) -> str:
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf

def validar_cpf(cpf: str) -> bool:
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10) % 11
    if digito1 == 10:
        digito1 = 0
    
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10) % 11
    if digito2 == 10:
        digito2 = 0
    
    return cpf[-2:] == f"{digito1}{digito2}"

def formatar_cnpj(cnpj: str) -> str:
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj

def formatar_telefone(telefone: str) -> str:
    telefone = re.sub(r'[^0-9]', '', telefone)
    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    return telefone

def buscar_cep_viacep(cep: str) -> Optional[Dict[str, str]]:
    try:
        cep = re.sub(r'[^0-9]', '', cep)
        if len(cep) != 8:
            return None
        
        url = f"https://viacep.com.br/ws/{cep}/json/"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            dados = response.json()
            if 'erro' not in dados:
                return {
                    'logradouro': dados.get('logradouro', ''),
                    'bairro': dados.get('bairro', ''),
                    'cidade': dados.get('localidade', ''),
                    'estado': dados.get('uf', '')
                }
        return None
    except Exception as e:
        st.warning(f"Erro ao buscar CEP na ViaCEP: {str(e)}")
        return None

def buscar_cep(cep: str) -> Optional[Dict[str, str]]:
    return buscar_cep_viacep(cep)

def preencher_endereco(tipo: str) -> None:
    cep_key = f"cep_{tipo}"
    if cep_key in st.session_state and st.session_state[cep_key]:
        cep_limpo = re.sub(r'[^0-9]', '', st.session_state[cep_key])
        if len(cep_limpo) == 8:
            try:
                endereco_info = buscar_cep(cep_limpo)
                if endereco_info:
                    campos = {
                        'logradouro': f"endereco_{tipo}",
                        'bairro': f"bairro_{tipo}",
                        'cidade': f"cidade_{tipo}",
                        'estado': f"estado_{tipo}"
                    }
                    
                    for campo_origem, campo_destino in campos.items():
                        if campo_destino not in st.session_state or not st.session_state[campo_destino]:
                            st.session_state[campo_destino] = endereco_info.get(campo_origem, '')
                    st.rerun()
            except Exception as e:
                st.warning(f"Erro ao buscar CEP: {str(e)}")

@st.cache_data
def gerar_pdf_formatado(tipo, dados):
    pdf = FPDF('P', 'mm', 'A4')
    pdf.add_page()
    
    pdf.set_margins(20, 15, 20)
    pdf.set_auto_page_break(True, margin=15)
    
    try:
        pdf.image('Logo_pdf.png', x=160, y=10, w=30, h=15, type='PNG', link='')
    except Exception as e:
        st.warning(f"Não foi possível carregar a logo: {e}")
    
    try:
        pdf.add_font('Arial', '', 'arial.ttf', uni=True)
        pdf.add_font('Arial', 'B', 'arialbd.ttf', uni=True)
        use_arial = True
    except:
        st.warning("Fontes Arial não encontradas, usando fontes padrão")
        use_arial = False
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'FICHA CADASTRAL', 0, 1, 'C')
    pdf.ln(5)
    # colar aqui
    if tipo == 'pf':
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'PESSOA FÍSICA', 0, 1)
        pdf.ln(3)
        
        pdf.set_font('Arial', '', 10)
        pdf.cell(30, 6, 'CORRETOR(A):', 0, 0)
        pdf.cell(0, 6, dados.get('corretor', ''), 0, 1)
        pdf.cell(30, 6, 'IMOBILIÁRIA:', 0, 0)
        pdf.cell(0, 6, dados.get('imobiliaria', ''), 0, 1)
        pdf.cell(30, 6, 'Nº NEGÓCIO:', 0, 0)
        pdf.cell(0, 6, dados.get('numero_negocio', ''), 0, 1)
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 7, 'DADOS DO CLIENTE', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        pdf.cell(60, 6, 'NOME COMPLETO SEM ABREVIAR: ', 0, 0)
        pdf.cell(0, 6, dados.get('nome', ''), 0, 1)
        
        pdf.cell(25, 6, 'GÊNERO:', 0, 0)
        pdf.cell(25, 6, dados.get('genero', ''), 0, 0)
        pdf.cell(40, 6, 'DATA NASCIMENTO:', 0, 0)
        pdf.cell(0, 6, dados.get('data_nascimento', ''), 0, 1)
        
        pdf.cell(20, 6, 'CPF:', 0, 0)
        pdf.cell(40, 6, dados.get('cpf', ''), 0, 0)
        pdf.cell(25, 6, 'CELULAR:', 0, 0)
        pdf.cell(0, 6, dados.get('celular', ''), 0, 1)
        pdf.cell(20, 6, 'E-MAIL:', 0, 0)
        pdf.cell(0, 6, dados.get('email', ''), 0, 1)
        
        pdf.cell(35, 6, 'NACIONALIDADE:', 0, 0)
        pdf.cell(40, 6, dados.get('nacionalidade', ''), 0, 0)
        pdf.cell(25, 6, 'PROFISSÃO:', 0, 0)
        pdf.cell(0, 6, dados.get('profissao', ''), 0, 1)
        
        pdf.cell(30, 6, 'ESTADO CIVIL:', 0, 0)
        pdf.cell(0, 6, dados.get('estado_civil', ''), 0, 1)
        
        pdf.cell(30, 6, 'UNIÃO ESTÁVEL:', 0, 0)
        pdf.cell(0, 6, dados.get('uniao_estavel', 'NÃO'), 0, 1)
        
        pdf.cell(45, 6, 'REGIME CASAMENTO:', 0, 0)
        pdf.cell(0, 6, dados.get('regime_casamento', ''), 0, 1)
        pdf.ln(2)
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 7, 'ENDEREÇO ', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        pdf.cell(15, 6, 'CEP:', 0, 0)
        pdf.cell(25, 6, dados.get('cep', ''), 0, 0)
        pdf.cell(25, 6, 'ENDEREÇO:   ', '0', 0)
        pdf.cell(0, 6, dados.get('endereco', ''), 0, 1)
        
        pdf.cell(20, 6, 'NÚMERO:', 0, 0)
        pdf.cell(20, 6, dados.get('numero', ''), 0, 0)
        pdf.cell(20, 6, 'BAIRRO:', 0, 0)
        pdf.cell(0, 6, dados.get('bairro', ''), 0, 1)
        
        pdf.cell(20, 6, 'CIDADE:', 0, 0)
        pdf.cell(50, 6, dados.get('cidade', ''), 0, 0)
        pdf.cell(25, 6, 'ESTADO:   ', 0, 0)
        pdf.cell(0, 6, dados.get('estado', ''), 0, 1)
        pdf.ln(2)
        
        if dados.get('nome_conjuge', ''):
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 7, 'DADOS DO CÔNJUGE/ 2º PROPONENTE', 0, 1)
            pdf.set_font('Arial', '', 10)
            
            pdf.cell(60, 6, 'NOME COMPLETO SEM ABREVIAR: ', 0, 0)
            pdf.cell(0, 6, dados.get('nome_conjuge', ''), 0, 1)
            
            pdf.cell(25, 6, 'GÊNERO:', 0, 0)
            pdf.cell(25, 6, dados.get('genero_conjuge', ''), 0, 0)
            pdf.cell(40, 6, 'DATA NASCIMENTO:', 0, 0)
            pdf.cell(0, 6, dados.get('data_nascimento_conjuge', ''), 0, 1)
            
            pdf.cell(20, 6, 'CPF:', 0, 0)
            pdf.cell(40, 6, dados.get('cpf_conjuge', ''), 0, 0)
            pdf.cell(25, 6, 'CELULAR:', 0, 0)
            pdf.cell(0, 6, dados.get('celular_conjuge', ''), 0, 1)
            pdf.cell(20, 6, 'E-MAIL:', 0, 0)
            pdf.cell(0, 6, dados.get('email_conjuge', ''), 0, 1)
            
            pdf.cell(35, 6, 'NACIONALIDADE:', 0, 0)
            pdf.cell(40, 6, dados.get('nacionalidade_conjuge', ''), 0, 0)
            pdf.cell(25, 6, 'PROFISSÃO:', 0, 0)
            pdf.cell(0, 6, dados.get('profissao_conjuge', ''), 0, 1)
            
            pdf.cell(30, 6, 'ESTADO CIVIL:', 0, 0)
            pdf.cell(0, 6, dados.get('estado_civil_conjuge', ''), 0, 1)
            
            pdf.cell(30, 6, 'UNIÃO ESTÁVEL:', 0, 0)
            pdf.cell(0, 6, dados.get('uniao_estavel_conjuge', 'NÃO'), 0, 1)
            
            pdf.cell(45, 6, 'REGIME CASAMENTO:', 0, 0)
            pdf.cell(0, 6, dados.get('regime_casamento_conjuge', ''), 0, 1)
            pdf.ln(2)
            
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 7, 'ENDEREÇO DO CÔNJUGE ', 0, 1)
            pdf.set_font('Arial', '', 10)
            
            pdf.cell(15, 6, 'CEP:', 0, 0)
            pdf.cell(25, 6, dados.get('cep_conjuge', ''), 0, 0)
            pdf.cell(25, 6, 'ENDEREÇO:   ', '0', 0)
            pdf.cell(0, 6, dados.get('endereco_conjuge', ''), 0, 1)
            
            pdf.cell(20, 6, 'NÚMERO:', 0, 0)
            pdf.cell(20, 6, dados.get('numero_conjuge', ''), 0, 0)
            pdf.cell(20, 6, 'BAIRRO:', 0, 0)
            pdf.cell(0, 6, dados.get('bairro_conjuge', ''), 0, 1)
            
            pdf.cell(20, 6, 'CIDADE:', 0, 0)
            pdf.cell(50, 6, dados.get('cidade_conjuge', ''), 0, 0)
            pdf.cell(25, 6, 'ESTADO:   ', 0, 0)
            pdf.cell(0, 6, dados.get('estado_conjuge', ''), 0, 1)
            pdf.ln(2)
        
        pdf.set_font('Arial', '', 8)
        pdf.multi_cell(0, 4, 'Para os fins da Lei 13.709/18, o titular concorda com: (i) o tratamento de seus dados pessoais e de seu cônjuge, quando for o caso, para os fins relacionados ao cumprimento das obrigações previstas na Lei, nesta ficha cadastral ou dela decorrente; e (ii) o envio de seus dados pessoais e da documentação respectiva a órgãos e entidades tais como a Secretaria da Fazenda Municipal, administração do condomínio, Cartórios, ao credor fiduciário, à companhia securitizadora e a outras pessoas, nos limites permitidos em Lei.')
          
        pdf.ln(2)
        pdf.cell(0, 5, f"UBERLÂNDIA/MG, {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
               
        pdf.ln(2)

        pdf.ln(8)
        pdf.set_font('Arial', '', 10)
        col_width = pdf.w / 2 - 15
        
        pdf.cell(col_width, 6, '_______________________________', 0, 0, 'C')
        pdf.cell(col_width, 6, '_______________________________', 0, 1, 'C')
        pdf.cell(col_width, 6, 'ASSINATURA DO 1° PROPONENTE', 0, 0, 'C')
        pdf.cell(col_width, 6, 'ASSINATURA DO 2° PROPONENTE', 0, 1, 'C')
    else:  # Pessoa Jurídica
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'PESSOA JURÍDICA', 0, 1, 'C')
        pdf.ln(2)
        
        # Dados da Imobiliária
        pdf.set_font('Arial', '', 10)
        pdf.cell(30, 6, 'CORRETOR(A):', 0, 0)
        pdf.cell(0, 6, dados.get('corretor', ''), 0, 1)
        pdf.cell(30, 6, 'IMOBILIÁRIA:', 0, 0)
        pdf.cell(0, 6, dados.get('imobiliaria', ''), 0, 1)
        pdf.cell(30, 6, 'Nº NEGÓCIO:', 0, 0)
        pdf.cell(0, 6, dados.get('numero_negocio', ''), 0, 1)
        pdf.ln(2)
        
        # Dados da Empresa
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 7, 'DADOS DA EMPRESA', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        pdf.cell(60, 6, 'RAZÃO SOCIAL:', 0, 0)
        pdf.cell(0, 6, dados.get('razao_social', ''), 0, 1)
        
        pdf.cell(20, 6, 'CNPJ:', 0, 0)
        pdf.cell(40, 6, dados.get('cnpj', ''), 0, 0)
        pdf.cell(25, 6, 'TELEFONE:', 0, 0)
        pdf.cell(0, 6, dados.get('telefone_empresa', ''), 0, 1)
        
        pdf.cell(20, 6, 'E-MAIL:', 0, 0)
        pdf.cell(0, 6, dados.get('email', ''), 0, 1)
        pdf.ln(2)
        
        # Endereço da Empresa
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 7, 'ENDEREÇO DA EMPRESA', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        pdf.cell(15, 6, 'CEP:', 0, 0)
        pdf.cell(20, 6, dados.get('cep_empresa', ''), 0, 0)
        pdf.cell(25, 6, 'ENDEREÇO:', 0, 0)
        pdf.cell(0, 6, dados.get('endereco_empresa', ''), 0, 1)
        
        pdf.cell(20, 6, 'NÚMERO:', 0, 0)
        pdf.cell(20, 6, dados.get('numero_empresa', ''), 0, 0)
        pdf.cell(20, 6, 'BAIRRO:', 0, 0)
        pdf.cell(0, 6, dados.get('bairro_empresa', ''), 0, 1)
        
        pdf.cell(20, 6, 'CIDADE:', 0, 0)
        pdf.cell(40, 6, dados.get('cidade_empresa', ''), 0, 0)
        pdf.cell(25, 6, 'ESTADO:', 0, 0)
        pdf.cell(0, 6, dados.get('estado_empresa', ''), 0, 1)
        pdf.ln(2)
        
        # Dados do Administrador
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 7, 'DADOS DO ADMINISTRADOR', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        pdf.cell(60, 6, 'NOME COMPLETO SEM ABREVIAR:', 0, 0)
        pdf.cell(0, 6, dados.get('nome_administrador', ''), 0, 1)
        
        pdf.cell(25, 6, 'GÊNERO:', 0, 0)
        pdf.cell(25, 6, dados.get('genero_administrador', ''), 0, 0)
        pdf.cell(40, 6, 'DATA NASCIMENTO:', 0, 0)
        pdf.cell(0, 6, dados.get('data_nascimento_administrador', ''), 0, 1)
        
        pdf.cell(20, 6, 'CPF:', 0, 0)
        pdf.cell(40, 6, dados.get('cpf_administrador', ''), 0, 0)
        pdf.cell(25, 6, 'CELULAR:', 0, 0)
        pdf.cell(0, 6, dados.get('celular_administrador', ''), 0, 1)
        
        pdf.cell(20, 6, 'E-MAIL:', 0, 0)
        pdf.cell(0, 6, dados.get('email_administrador', ''), 0, 1)
        
        pdf.cell(35, 6, 'NACIONALIDADE:', 0, 0)
        pdf.cell(40, 6, dados.get('nacionalidade_administrador', ''), 0, 0)
        pdf.cell(25, 6, 'PROFISSÃO:', 0, 0)
        pdf.cell(0, 6, dados.get('profissao_administrador', ''), 0, 1)
        
        pdf.cell(30, 6, 'ESTADO CIVIL:', 0, 0)
        pdf.cell(0, 6, dados.get('estado_civil_administrador', ''), 0, 1)
        
        pdf.cell(30, 6, 'UNIÃO ESTÁVEL:', 0, 0)
        pdf.cell(0, 6, dados.get('uniao_estavel_administrador', 'NÃO'), 0, 1)
        
        pdf.cell(45, 6, 'REGIME CASAMENTO:', 0, 0)
        pdf.cell(0, 6, dados.get('regime_casamento_administrador', ''), 0, 1)
        pdf.ln(2)
        
        # Endereço do Administrador
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 7, 'ENDEREÇO DO ADMINISTRADOR', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        pdf.cell(15, 6, 'CEP:', 0, 0)
        pdf.cell(20, 6, dados.get('cep_administrador', ''), 0, 0)
        pdf.cell(25, 6, 'ENDEREÇO:', 0, 0)
        pdf.cell(0, 6, dados.get('endereco_administrador', ''), 0, 1)
        
        pdf.cell(20, 6, 'NÚMERO:', 0, 0)
        pdf.cell(20, 6, dados.get('numero_administrador', ''), 0, 0)
        pdf.cell(20, 6, 'BAIRRO:', 0, 0)
        pdf.cell(0, 6, dados.get('bairro_administrador', ''), 0, 1)
        
        pdf.cell(20, 6, 'CIDADE:', 0, 0)
        pdf.cell(40, 6, dados.get('cidade_administrador', ''), 0, 0)
        pdf.cell(25, 6, 'ESTADO:', 0, 0)
        pdf.cell(0, 6, dados.get('estado_administrador', ''), 0, 1)
        pdf.ln(2)
        
        # Pessoas Vinculadas
        if 'pessoas_vinculadas' in dados and dados['pessoas_vinculadas']:
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 7, 'PESSOAS VINCULADAS', 0, 1)
            
            for idx, pessoa in enumerate(dados['pessoas_vinculadas']):
                # Garantir que todos os campos existam
                pessoa = {
                    'tipo': pessoa.get('tipo', ''),
                    'nome': pessoa.get('nome', ''),
                    'genero': pessoa.get('genero', ''),
                    'cpf': pessoa.get('cpf', ''),
                    'data_nascimento': pessoa.get('data_nascimento', ''),
                    'estado_civil': pessoa.get('estado_civil', ''),
                    'regime_casamento': pessoa.get('regime_casamento', ''),
                    'uniao_estavel': pessoa.get('uniao_estavel', 'NÃO'),
                    'cargo': pessoa.get('cargo', ''),
                    'celular': pessoa.get('celular', ''),
                    'email': pessoa.get('email', ''),
                    'cep': pessoa.get('cep', ''),
                    'endereco': pessoa.get('endereco', ''),
                    'numero': pessoa.get('numero', ''),
                    'bairro': pessoa.get('bairro', ''),
                    'cidade': pessoa.get('cidade', ''),
                    'estado': pessoa.get('estado', '')
                }
                
                # Título com número da pessoa
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 6, f'PESSOA VINCULADA {idx + 1} - {pessoa["tipo"].upper()}', 0, 1)
                pdf.set_font('Arial', '', 10)
                
                # Dados Pessoais
                pdf.cell(60, 6, 'NOME COMPLETO SEM ABREVIAR:', 0, 0)
                pdf.cell(0, 6, pessoa['nome'], 0, 1)
                
                pdf.cell(25, 6, 'GÊNERO:', 0, 0)
                pdf.cell(25, 6, pessoa['genero'], 0, 0)
                pdf.cell(40, 6, 'DATA NASCIMENTO:', 0, 0)
                pdf.cell(0, 6, pessoa['data_nascimento'], 0, 1)
                
                pdf.cell(20, 6, 'CPF:', 0, 0)
                pdf.cell(40, 6, formatar_cpf(pessoa['cpf']), 0, 0)
                pdf.cell(25, 6, 'CELULAR:', 0, 0)
                pdf.cell(0, 6, formatar_telefone(pessoa['celular']), 0, 1)
                
                pdf.cell(20, 6, 'E-MAIL:', 0, 0)
                pdf.cell(0, 6, pessoa['email'], 0, 1)
                
                pdf.cell(35, 6, 'CARGO/FUNÇÃO:', 0, 0)
                pdf.cell(40, 6, pessoa['cargo'], 0, 0)
                
                pdf.cell(30, 6, 'ESTADO CIVIL:   ', 0, 0)
                pdf.cell(0, 6, pessoa['estado_civil'], 0, 1)
                
                pdf.cell(30, 6, 'UNIÃO ESTÁVEL:', 0, 0)
                pdf.cell(0, 6, pessoa['uniao_estavel'], 0, 1)
                
                pdf.cell(45, 6, 'REGIME CASAMENTO:   ', 0, 0)
                pdf.cell(0, 6, pessoa['regime_casamento'], 0, 1)
                pdf.ln(2)
                
                # Endereço
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(0, 7, 'ENDEREÇO', 0, 1)
                pdf.set_font('Arial', '', 10)
                
                pdf.cell(15, 6, 'CEP:', 0, 0)
                pdf.cell(20, 6, pessoa['cep'], 0, 0)
                pdf.cell(25, 6, 'ENDEREÇO:', 0, 0)
                pdf.cell(0, 6, pessoa['endereco'], 0, 1)
                
                pdf.cell(20, 6, 'NÚMERO:', 0, 0)
                pdf.cell(20, 6, pessoa['numero'], 0, 0)
                pdf.cell(20, 6, 'BAIRRO:', 0, 0)
                pdf.cell(0, 6, pessoa['bairro'], 0, 1)
                
                pdf.cell(20, 6, 'CIDADE:', 0, 0)
                pdf.cell(40, 6, pessoa['cidade'], 0, 0)
                pdf.cell(25, 6, 'ESTADO:', 0, 0)
                pdf.cell(0, 6, pessoa['estado'], 0, 1)
                
                # Espaço entre pessoas vinculadas
                pdf.ln(4)
        
        # Termo de consentimento
        pdf.set_font('Arial', '', 8)
        pdf.multi_cell(0, 4, 'Para os fins da Lei 13.709/18, o titular concorda com: (i) o tratamento de seus dados pessoais e de seu cônjuge, quando for o caso, para os fins relacionados ao cumprimento das obrigações previstas na Lei, nesta ficha cadastral ou dela decorrente; e (ii) o envio de seus dados pessoais e da documentação respectiva a órgãos e entidades tais como a Secretaria da Fazenda Municipal, administração do condomínio, Cartórios, ao credor fiduciário, à companhia securitizadora e a outras pessoas, nos limites permitidos em Lei.')
        
        pdf.ln(5)
        pdf.cell(0, 5, f"UBERLÂNDIA/MG, {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
        
        
        pdf.ln(8)
        pdf.set_font('Arial', '', 10)
        col_width = pdf.w / 2 - 15
        
        pdf.cell(col_width, 6, '_______________________________', 0, 0, 'C')
        pdf.cell(col_width, 6, '_______________________________', 0, 1, 'C')
        pdf.cell(col_width, 6, 'ASSINATURA DO ADMINISTRADOR', 0, 0, 'C')
        pdf.cell(col_width, 6, '2º PROPONENTE/CÔNJUGE/SÓCIO', 0, 1, 'C')
        pdf.ln(10)

    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, f"ficha_{tipo}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
    pdf.output(pdf_path)
    
    return pdf_path

def carregar_clientes_pf(usuario_id=None):
    conn = sqlite3.connect(DB_NAME)
    if usuario_id:
        df = pd.read_sql('SELECT * FROM clientes_pf WHERE usuario_id = ?', conn, params=(usuario_id,))
    else:
        df = pd.read_sql('SELECT * FROM clientes_pf', conn)
    conn.close()
    return df

def carregar_clientes_pj(usuario_id=None):
    conn = sqlite3.connect(DB_NAME)
    if usuario_id:
        df = pd.read_sql('SELECT * FROM clientes_pj WHERE usuario_id = ?', conn, params=(usuario_id,))
    else:
        df = pd.read_sql('SELECT * FROM clientes_pj', conn)
    conn.close()
    return df

def salvar_cliente_pf(cliente, usuario_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if 'id' in cliente:
        # Atualização de registro existente
        cursor.execute('''
        UPDATE clientes_pf SET
            nome = ?, genero = ?, data_nascimento = ?, celular = ?, cpf = ?, email = ?,
            nacionalidade = ?, profissao = ?, estado_civil = ?, regime_casamento = ?, uniao_estavel = ?,
            cep = ?, endereco = ?, numero = ?, bairro = ?, cidade = ?, estado = ?,
            nome_conjuge = ?, genero_conjuge = ?, data_nascimento_conjuge = ?, cpf_conjuge = ?,
            celular_conjuge = ?, email_conjuge = ?, nacionalidade_conjuge = ?, profissao_conjuge = ?,
            estado_civil_conjuge = ?, regime_casamento_conjuge = ?, uniao_estavel_conjuge = ?,
            cep_conjuge = ?, endereco_conjuge = ?, numero_conjuge = ?, bairro_conjuge = ?,
            cidade_conjuge = ?, estado_conjuge = ?, data_cadastro = ?,
            corretor = ?, imobiliaria = ?, numero_negocio = ?, usuario_id = ?
        WHERE id = ?
        ''', (
            cliente['nome'], cliente['genero'], cliente['data_nascimento'],
            cliente['celular'], cliente['cpf'], cliente.get('email', ''),
            cliente['nacionalidade'], cliente['profissao'], cliente['estado_civil'],
            cliente['regime_casamento'], cliente['uniao_estavel'],
            cliente['cep'], cliente['endereco'], cliente['numero'],
            cliente['bairro'], cliente['cidade'], cliente['estado'],
            cliente.get('nome_conjuge', ''), cliente.get('genero_conjuge', ''), 
            cliente.get('data_nascimento_conjuge', ''), cliente.get('cpf_conjuge', ''),
            cliente.get('celular_conjuge', ''), cliente.get('email_conjuge', ''), 
            cliente.get('nacionalidade_conjuge', ''), cliente.get('profissao_conjuge', ''),
            cliente.get('estado_civil_conjuge', ''), cliente.get('regime_casamento_conjuge', ''),
            cliente.get('uniao_estavel_conjuge', ''), cliente.get('cep_conjuge', ''),
            cliente.get('endereco_conjuge', ''), cliente.get('numero_conjuge', ''),
            cliente.get('bairro_conjuge', ''), cliente.get('cidade_conjuge', ''),
            cliente.get('estado_conjuge', ''), cliente['data_cadastro'], 
            cliente['corretor'], cliente['imobiliaria'], cliente['numero_negocio'],
            usuario_id, cliente['id']
        ))
    else:
        # Inserção de novo registro
        cursor.execute('''
        INSERT INTO clientes_pf (
            nome, genero, data_nascimento, celular, cpf, email,
            nacionalidade, profissao, estado_civil, regime_casamento, uniao_estavel,
            cep, endereco, numero, bairro, cidade, estado,
            nome_conjuge, genero_conjuge, data_nascimento_conjuge, cpf_conjuge,
            celular_conjuge, email_conjuge, nacionalidade_conjuge, profissao_conjuge,
            estado_civil_conjuge, regime_casamento_conjuge, uniao_estavel_conjuge,
            cep_conjuge, endereco_conjuge, numero_conjuge, bairro_conjuge,
            cidade_conjuge, estado_conjuge, data_cadastro,
            corretor, imobiliaria, numero_negocio, usuario_id
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            cliente['nome'], cliente['genero'], cliente['data_nascimento'],
            cliente['celular'], cliente['cpf'], cliente.get('email', ''),
            cliente['nacionalidade'], cliente['profissao'], cliente['estado_civil'],
            cliente['regime_casamento'], cliente['uniao_estavel'],
            cliente['cep'], cliente['endereco'], cliente['numero'],
            cliente['bairro'], cliente['cidade'], cliente['estado'],
            cliente.get('nome_conjuge', ''), cliente.get('genero_conjuge', ''), 
            cliente.get('data_nascimento_conjuge', ''), cliente.get('cpf_conjuge', ''),
            cliente.get('celular_conjuge', ''), cliente.get('email_conjuge', ''), 
            cliente.get('nacionalidade_conjuge', ''), cliente.get('profissao_conjuge', ''),
            cliente.get('estado_civil_conjuge', ''), cliente.get('regime_casamento_conjuge', ''),
            cliente.get('uniao_estavel_conjuge', ''), cliente.get('cep_conjuge', ''),
            cliente.get('endereco_conjuge', ''), cliente.get('numero_conjuge', ''),
            cliente.get('bairro_conjuge', ''), cliente.get('cidade_conjuge', ''),
            cliente.get('estado_conjuge', ''), cliente['data_cadastro'], 
            cliente['corretor'], cliente['imobiliaria'], cliente['numero_negocio'],
            usuario_id
        ))
    
    conn.commit()
    conn.close()

def salvar_cliente_pj(cliente, usuario_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if 'id' in cliente:
        # Código de update permanece o mesmo
        cursor.execute('''
        UPDATE clientes_pj SET
            razao_social = ?, cnpj = ?, email = ?, telefone_empresa = ?,
            cep_empresa = ?, endereco_empresa = ?, numero_empresa = ?,
            bairro_empresa = ?, cidade_empresa = ?, estado_empresa = ?,
            genero_administrador = ?, nome_administrador = ?, data_nascimento_administrador = ?,
            cpf_administrador = ?, celular_administrador = ?, email_administrador = ?,
            nacionalidade_administrador = ?, profissao_administrador = ?,
            estado_civil_administrador = ?, regime_casamento_administrador = ?,
            uniao_estavel_administrador = ?, cep_administrador = ?,
            endereco_administrador = ?, numero_administrador = ?,
            bairro_administrador = ?, cidade_administrador = ?,
            estado_administrador = ?, corretor = ?, imobiliaria = ?,
            numero_negocio = ?
        WHERE id = ?
        ''', (
            cliente['razao_social'], cliente['cnpj'], cliente.get('email', ''),
            cliente.get('telefone_empresa', ''), cliente.get('cep_empresa', ''),
            cliente.get('endereco_empresa', ''), cliente.get('numero_empresa', ''),
            cliente.get('bairro_empresa', ''), cliente.get('cidade_empresa', ''),
            cliente.get('estado_empresa', ''), cliente['genero_administrador'],
            cliente['nome_administrador'], cliente.get('data_nascimento_administrador', ''),
            cliente['cpf_administrador'], cliente['celular_administrador'],
            cliente.get('email_administrador', ''),
            cliente.get('nacionalidade_administrador', 'BRASILEIRA'),
            cliente.get('profissao_administrador', ''),
            cliente.get('estado_civil_administrador', ''),
            cliente.get('regime_casamento_administrador', ''),
            cliente.get('uniao_estavel_administrador', 'NÃO'),
            cliente.get('cep_administrador', ''), cliente.get('endereco_administrador', ''),
            cliente.get('numero_administrador', ''), cliente.get('bairro_administrador', ''),
            cliente.get('cidade_administrador', ''), cliente.get('estado_administrador', ''),
            cliente.get('corretor', ''), cliente.get('imobiliaria', ''),
            cliente.get('numero_negocio', ''), cliente['id']
        ))
        empresa_id = cliente['id']
    else:
        cursor.execute('''
        INSERT INTO clientes_pj (
            razao_social, cnpj, email, telefone_empresa, cep_empresa, endereco_empresa,
            numero_empresa, bairro_empresa, cidade_empresa, estado_empresa,
            genero_administrador, nome_administrador, data_nascimento_administrador,
            cpf_administrador, celular_administrador, email_administrador, nacionalidade_administrador,
            profissao_administrador, estado_civil_administrador, regime_casamento_administrador,
            uniao_estavel_administrador, cep_administrador, endereco_administrador,
            numero_administrador, bairro_administrador, cidade_administrador,
            estado_administrador, data_cadastro, corretor, imobiliaria, numero_negocio, usuario_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cliente['razao_social'], cliente['cnpj'], cliente.get('email', ''),
            cliente.get('telefone_empresa', ''), cliente.get('cep_empresa', ''),
            cliente.get('endereco_empresa', ''), cliente.get('numero_empresa', ''),
            cliente.get('bairro_empresa', ''), cliente.get('cidade_empresa', ''),
            cliente.get('estado_empresa', ''), cliente['genero_administrador'],
            cliente['nome_administrador'], cliente.get('data_nascimento_administrador', ''),
            cliente['cpf_administrador'], cliente['celular_administrador'],
            cliente.get('email_administrador', ''),
            cliente.get('nacionalidade_administrador', 'BRASILEIRA'),
            cliente.get('profissao_administrador', ''),
            cliente.get('estado_civil_administrador', ''),
            cliente.get('regime_casamento_administrador', ''),
            cliente.get('uniao_estavel_administrador', 'NÃO'),
            cliente.get('cep_administrador', ''), cliente.get('endereco_administrador', ''),
            cliente.get('numero_administrador', ''), cliente.get('bairro_administrador', ''),
            cliente.get('cidade_administrador', ''), cliente.get('estado_administrador', ''),
            cliente['data_cadastro'], cliente.get('corretor', ''),
            cliente.get('imobiliaria', ''), cliente.get('numero_negocio', ''),
            usuario_id
        ))
        empresa_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return empresa_id

def obter_cliente_pf_por_id(cliente_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes_pf WHERE id = ?', (cliente_id,))
    cliente = cursor.fetchone()
    if cliente:
        cols = [column[0] for column in cursor.description]
        cliente_dict = dict(zip(cols, cliente))
    else:
        cliente_dict = None
    conn.close()
    return cliente_dict

def obter_cliente_pj_por_id(cliente_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes_pj WHERE id = ?', (cliente_id,))
    cliente = cursor.fetchone()
    conn.close()
    
    if cliente:
        cols = [column[0] for column in cursor.description]
        return dict(zip(cols, cliente))
    return None

# Na parte de edição:
if 'editar_pj_id' in st.session_state:
    cliente_editando = obter_cliente_pj_por_id(st.session_state['editar_pj_id'])
    
    if not cliente_editando:
        st.error("Registro não encontrado no banco de dados!")
        del st.session_state['editar_pj_id']
        st.rerun()
    
    st.warning(f"Editando registro ID: {st.session_state['editar_pj_id']}")
    if st.button("Cancelar Edição"):
        del st.session_state['editar_pj_id']
        st.rerun()

def excluir_cliente_pf(cliente_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM clientes_pf WHERE id = ?', (cliente_id,))
    conn.commit()
    conn.close()

def excluir_cliente_pj(cliente_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM clientes_pj WHERE id = ?', (cliente_id,))
    # Remove também as pessoas vinculadas
    cursor.execute('DELETE FROM pessoas_vinculadas_pj WHERE empresa_id = ?', (cliente_id,))
    conn.commit()
    conn.close()

# Tela de login unificada
def login_page():
    # Força o layout padrão (não-wide) apenas para a tela de login
    st.markdown(
        """
        <style>
            .main > div {
                max-width: 500px;
                padding-top: 2rem;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.title("🔒 Login - Sistema Imobiliário")
    
    # Container principal para o formulário de login
    with st.container():
        with st.form(key="form_login"):
            st.markdown("<h3 style='text-align: center;'>Acesse sua conta</h3>", unsafe_allow_html=True)
            
            username = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            
            # Botão centralizado
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.form_submit_button("Entrar", use_container_width=True):
                    usuario = verificar_login(username, senha)
                    if usuario:
                        st.session_state['usuario'] = usuario
                        st.session_state['logado'] = True
                        st.success("Login realizado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos")
    
    # Links abaixo do botão de login
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cadastrar Usuário", use_container_width=True):
            st.session_state['mostrar_cadastro'] = True
    with col2:
        if st.button("Recuperar Senha", use_container_width=True):
            st.session_state['mostrar_recuperacao'] = True
    
    # Formulário de cadastro (aparece apenas quando solicitado)
    if st.session_state.get('mostrar_cadastro', False):
        st.subheader("Cadastro de Usuário")
        novo_username = st.text_input("Nome de usuário *", key="novo_username")
        nova_senha = st.text_input("Senha *", type="password", key="nova_senha")
        confirmar_senha = st.text_input("Confirmar senha *", type="password", key="confirmar_senha")
        nome_completo = st.text_input("Nome completo *", key="nome_completo")
        cpf = st.text_input("CPF *", help="Formato: 000.000.000-00", key="cpf")
        email = st.text_input("E-mail *", key="email")
        telefone = st.text_input("Telefone *", help="Formato: (00) 00000-0000", key="telefone")
        imobiliaria = st.text_input("Imobiliária *", key="imobiliaria")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Cadastrar", use_container_width=True):
                if nova_senha != confirmar_senha:
                    st.error("As senhas não coincidem")
                elif not novo_username or not nova_senha or not nome_completo or not cpf or not email or not telefone or not imobiliaria:
                    st.error("Preencha todos os campos obrigatórios (*)")
                elif not validar_cpf(cpf):
                    st.error("CPF inválido. Por favor, verifique o número.")
                else:
                    sucesso = cadastrar_usuario(novo_username, nova_senha, nome_completo, 
                                             formatar_cpf(cpf), email, formatar_telefone(telefone), 
                                             imobiliaria)
                    if sucesso:
                        st.success("Usuário cadastrado com sucesso!")
                        st.session_state['mostrar_cadastro'] = False
                    else:
                        st.error("Nome de usuário já existe")
        with col2:
            if st.button("Cancelar", use_container_width=True):
                st.session_state['mostrar_cadastro'] = False
    
    # Formulário de recuperação de senha (aparece apenas quando solicitado)
    if st.session_state.get('mostrar_recuperacao', False):
        st.subheader("Recuperação de Senha")
        
        if 'token_enviado' not in st.session_state:
            username_rec = st.text_input("Nome de usuário", key="username_rec")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Enviar Código", use_container_width=True):
                    if not username_rec:
                        st.error("Informe o nome de usuário")
                    else:
                        resultado = gerar_token_recuperacao(username_rec)
                        if resultado:
                            st.session_state['username_rec'] = username_rec
                            st.session_state['token_enviado'] = True
                            st.success("Um código de recuperação foi enviado para o e-mail cadastrado")
                        else:
                            st.error("Usuário não encontrado ou erro ao enviar e-mail")
            with col2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state['mostrar_recuperacao'] = False
        
        if 'token_enviado' in st.session_state:
            token_digitado = st.text_input("Código de Verificação (6 dígitos)", key="token_recuperacao")
            nova_senha_rec = st.text_input("Nova Senha", type="password", key="nova_senha_rec")
            confirmar_senha_rec = st.text_input("Confirmar Nova Senha", type="password", key="confirmar_senha_rec")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Alterar Senha", use_container_width=True):
                    if not validar_token(st.session_state['username_rec'], token_digitado):
                        st.error("Código inválido ou expirado")
                    elif nova_senha_rec != confirmar_senha_rec:
                        st.error("As senhas não coincidem")
                    else:
                        alterar_senha(st.session_state['username_rec'], nova_senha_rec)
                        st.success("Senha alterada com sucesso!")
                        del st.session_state['mostrar_recuperacao']
                        del st.session_state['token_enviado']
                        del st.session_state['username_rec']
                        time.sleep(2)
                        st.rerun()
            with col2:
                if st.button("Cancelar", use_container_width=True):
                    del st.session_state['mostrar_recuperacao']
                    del st.session_state['token_enviado']
                    del st.session_state['username_rec']

# Verificação de login - Fluxo principal
if 'logado' not in st.session_state or not st.session_state['logado']:
    login_page()
else:
    # Carregar dados apenas se o usuário estiver logado
    if 'clientes_pf' not in st.session_state:
        st.session_state.clientes_pf = carregar_clientes_pf(
            st.session_state['usuario']['id'] if not st.session_state['usuario']['is_admin'] else None
        )

    if 'clientes_pj' not in st.session_state:
        st.session_state.clientes_pj = carregar_clientes_pj(
            st.session_state['usuario']['id'] if not st.session_state['usuario']['is_admin'] else None
        )

    # Interface principal
    st.title(f"Sistema de Cadastro Imobiliário - {st.session_state['usuario']['nome_completo']}")

    # Botão de logout
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # Abas principais
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Ficha Cadastral PF", 
        "Ficha Cadastral PJ", 
        "Consulta de Registros",
        "Simulador Financeiro",
        "Backup/Restauração"
    ])
    # Variáveis para controle dos downloads
    pdf_path_pf = None
    pdf_path_pj = None

    with tab1:
        st.header("Ficha Cadastral - Pessoa Física")
        
        submitted_pf = False
        imprimir_pf = False
        
        # Verificar se estamos editando um registro existente
        if 'editar_pf_id' in st.session_state:
            cliente_editando = obter_cliente_pf_por_id(st.session_state['editar_pf_id'])
            if cliente_editando:
                st.warning(f"Editando registro ID: {st.session_state['editar_pf_id']}")
                if st.button("Cancelar Edição", key="cancelar_edicao_pf"):
                    del st.session_state['editar_pf_id']
                    st.rerun()
        with st.form(key="form_pf"):
            # Dados da Imobiliária
            st.subheader("Dados da Imobiliária")
            col1, col2 = st.columns(2)
            with col1:
                corretor = st.text_input("Corretor(a)", 
                                        value=cliente_editando.get('corretor', '') if 'editar_pj_id' in st.session_state else "")
                imobiliaria = st.text_input("Imobiliária", value=cliente_editando['imobiliaria'] if 'editar_pf_id' in st.session_state else " ")
            with col2:
                numero_negocio = st.text_input("Nº do Negócio", value=cliente_editando['numero_negocio'] if 'editar_pf_id' in st.session_state else "")
            
            # Dados do Cliente - Layout Compacto
            st.subheader("Dados do Cliente")
            
            # Linha 1: Gênero
            genero = st.radio("Gênero", ["MASCULINO", "FEMININO"], 
                             index=0 if 'editar_pf_id' not in st.session_state or cliente_editando['genero'] == "MASCULINO" else 1,
                             horizontal=True)
            
            # Linha 2: Nome e Data Nascimento
            linha1 = st.columns([2, 1])
            with linha1[0]:
                nome = st.text_input("Nome Completo *", 
                                    value=cliente_editando['nome'] if 'editar_pf_id' in st.session_state else "")
            with linha1[1]:
                data_nascimento = st.date_input("Data de Nascimento", 
                                              value=datetime.strptime(cliente_editando['data_nascimento'], '%d/%m/%Y') if 'editar_pf_id' in st.session_state and cliente_editando['data_nascimento'] else None,
                                              format="DD/MM/YYYY",
                                              key="data_nascimento_pf")
            
            # Linha 3: CPF e Celular
            linha2 = st.columns(2)
            with linha2[0]:
                cpf = st.text_input("CPF *", help="Formato: 000.000.000-00", 
                                  value=cliente_editando['cpf'] if 'editar_pf_id' in st.session_state else "",
                                  key="cpf_pf")
            with linha2[1]:
                celular = st.text_input("Celular *", help="Formato: (00) 00000-0000", 
                                      value=cliente_editando['celular'] if 'editar_pf_id' in st.session_state else "",
                                      key="celular_pf")
            
            # Dados Complementares
            st.markdown("**Dados Complementares**")
            
            # Linha 4: Nacionalidade e Profissão
            linha3 = st.columns(2)
            with linha3[0]:
                nacionalidade = st.text_input("Nacionalidade", 
                                            value=cliente_editando['nacionalidade'] if 'editar_pf_id' in st.session_state else "BRASILEIRA")
            with linha3[1]:
                profissao = st.text_input("Profissão", 
                                        value=cliente_editando['profissao'] if 'editar_pf_id' in st.session_state else "")
            
            # Linha 5: E-mail
            email = st.text_input("E-mail", 
                                value=cliente_editando['email'] if 'editar_pf_id' in st.session_state else "")
            
            # Linha 6: Estado Civil e Regime de Casamento
            linha4 = st.columns(2)
            with linha4[0]:
                estado_civil_opcoes = ["", "CASADO(A)", "SOLTEIRO(A)", "VIÚVO(A)", "DIVORCIADO(A)"]
                estado_civil_index = estado_civil_opcoes.index(cliente_editando['estado_civil']) if 'editar_pf_id' in st.session_state and cliente_editando['estado_civil'] in estado_civil_opcoes else 0
                estado_civil = st.selectbox("Estado Civil", estado_civil_opcoes, index=estado_civil_index)
            with linha4[1]:
                regime_opcoes = ["", "COMUNHÃO UNIVERSAL DE BENS", "SEPARAÇÃO DE BENS", 
                                "COMUNHÃO PARCIAL DE BENS", "COMUNHÃO DE BENS (REGIME ÚNICO ANTES DE 1977)"]
                regime_index = regime_opcoes.index(cliente_editando['regime_casamento']) if 'editar_pf_id' in st.session_state and cliente_editando['regime_casamento'] in regime_opcoes else 0
                regime_casamento = st.selectbox("Regime de Casamento", regime_opcoes, index=regime_index)
            
            # Linha 7: União Estável
            uniao_estavel = st.checkbox("União Estável", 
                                      value=True if 'editar_pf_id' in st.session_state and cliente_editando['uniao_estavel'] == "SIM" else False)

            # Endereço
            st.subheader("Endereço")
            col1, col2 = st.columns(2)
            with col1:
                cep = st.text_input("CEP", help="Formato: 00000-000", 
                                  value=cliente_editando['cep'] if 'editar_pf_id' in st.session_state else "",
                                  key="cep_pf")
                
                buscar_cep_pf = st.form_submit_button("Buscar CEP")
                if buscar_cep_pf:
                    preencher_endereco('pf')
               
                endereco = st.text_input("Endereço", 
                                       value=cliente_editando['endereco'] if 'editar_pf_id' in st.session_state else "",
                                       key="endereco_pf")
                numero = st.text_input("Número", 
                                     value=cliente_editando['numero'] if 'editar_pf_id' in st.session_state else "",
                                     key="numero_pf")
            with col2:
                bairro = st.text_input("Bairro", 
                                     value=cliente_editando['bairro'] if 'editar_pf_id' in st.session_state else "",
                                     key="bairro_pf")
                cidade = st.text_input("Cidade", 
                                     value=cliente_editando['cidade'] if 'editar_pf_id' in st.session_state else "",
                                     key="cidade_pf")
                estado = st.text_input("Estado", 
                                     value=cliente_editando['estado'] if 'editar_pf_id' in st.session_state else "",
                                     key="estado_pf")
            
            # Dados do 2° Proponente/Cônjuge
            st.subheader("Dados do 2° Proponente")

            # Radio button apenas para indicar se é cônjuge ou não
            tem_conjuge = st.radio("Relação com o 1° proponente:", 
                                ["Cônjuge/Convivente", "Outro Proponente"], 
                                index=0 if 'editar_pf_id' in st.session_state and cliente_editando['nome_conjuge'] else 1,
                                horizontal=True,
                                key="tem_conjuge")

            # Campos do 2° proponente (sempre visíveis)
            genero_conjuge = st.radio("Gênero", ["MASCULINO", "FEMININO"], 
                                    index=0 if 'editar_pf_id' not in st.session_state or cliente_editando.get('genero_conjuge', '') == "MASCULINO" else 1,
                                    key="genero_conjuge_pf", horizontal=True)

            # Linha 1: Nome e Data Nascimento
            linha_conjuge1 = st.columns([2, 1])
            with linha_conjuge1[0]:
                nome_conjuge = st.text_input("Nome Completo",
                                        value=cliente_editando.get('nome_conjuge', '') if 'editar_pf_id' in st.session_state else "")
            with linha_conjuge1[1]:
                data_nascimento_conjuge = st.date_input("Data de Nascimento", 
                                                    value=datetime.strptime(cliente_editando['data_nascimento_conjuge'], '%d/%m/%Y') if 'editar_pf_id' in st.session_state and cliente_editando.get('data_nascimento_conjuge', '') else None,
                                                    format="DD/MM/YYYY",
                                                    key="data_nascimento_conjuge_pf")

            # Linha 2: CPF e Celular
            linha_conjuge2 = st.columns(2)
            with linha_conjuge2[0]:
                cpf_conjuge = st.text_input("CPF", help="Formato: 000.000.000-00", 
                                        value=cliente_editando.get('cpf_conjuge', '') if 'editar_pf_id' in st.session_state else "",
                                        key="cpf_conjuge_pf")
            with linha_conjuge2[1]:
                celular_conjuge = st.text_input("Celular", help="Formato: (00) 00000-0000", 
                                            value=cliente_editando.get('celular_conjuge', '') if 'editar_pf_id' in st.session_state else "",
                                            key="celular_conjuge_pf")

            # Linha 3: Nacionalidade e Profissão
            linha_conjuge3 = st.columns(2)
            with linha_conjuge3[0]:
                nacionalidade_conjuge = st.text_input("Nacionalidade", 
                                                    value=cliente_editando.get('nacionalidade_conjuge', 'BRASILEIRA') if 'editar_pf_id' in st.session_state else "BRASILEIRA", 
                                                    key="nacionalidade_conjuge_pf")
            with linha_conjuge3[1]:
                profissao_conjuge = st.text_input("Profissão", 
                                                value=cliente_editando.get('profissao_conjuge', '') if 'editar_pf_id' in st.session_state else "",
                                                key="profissao_conjuge_pf")

            # Linha 4: E-mail
            email_conjuge = st.text_input("E-mail do Cônjuge", 
                                        value=cliente_editando.get('email_conjuge', '') if 'editar_pf_id' in st.session_state else "",
                                        key="email_conjuge_pf")

            # Linha 5: Estado Civil e Regime de Casamento
            linha_conjuge4 = st.columns(2)
            with linha_conjuge4[0]:
                estado_civil_conjuge_opcoes = ["", "CASADO(A)", "SOLTEIRO(A)", "VIÚVO(A)", "DIVORCIADO(A)"]
                estado_civil_conjuge_index = estado_civil_conjuge_opcoes.index(cliente_editando['estado_civil_conjuge']) if 'editar_pf_id' in st.session_state and cliente_editando.get('estado_civil_conjuge', '') in estado_civil_conjuge_opcoes else 0
                estado_civil_conjuge = st.selectbox("Estado Civil", 
                                                estado_civil_conjuge_opcoes,
                                                index=estado_civil_conjuge_index,
                                                key="estado_civil_conjuge_pf")
            with linha_conjuge4[1]:
                regime_conjuge_opcoes = ["", "COMUNHÃO UNIVERSAL DE BENS", "SEPARAÇÃO DE BENS", 
                                        "COMUNHÃO PARCIAL DE BENS", "COMUNHÃO DE BENS (REGIME ÚNICO ANTES DE 1977)"]
                regime_conjuge_index = regime_conjuge_opcoes.index(cliente_editando['regime_casamento_conjuge']) if 'editar_pf_id' in st.session_state and cliente_editando.get('regime_casamento_conjuge', '') in regime_conjuge_opcoes else 0
                regime_casamento_conjuge = st.selectbox("Regime de Casamento", 
                                                    regime_conjuge_opcoes,
                                                    index=regime_conjuge_index,
                                                    key="regime_casamento_conjuge_pf")

            # Linha 6: União Estável
            uniao_estavel_conjuge = st.checkbox("União Estável", 
                                            value=True if 'editar_pf_id' in st.session_state and cliente_editando.get('uniao_estavel_conjuge', '') == "SIM" else False,
                                            key="uniao_estavel_conjuge_pf")

            # Endereço do Cônjuge - Mesmo layout do primeiro proponente
            st.subheader("Endereço do Cônjuge")
            col_conjuge1, col_conjuge2 = st.columns(2)
            with col_conjuge1:
                cep_conjuge = st.text_input("CEP", help="Formato: 00000-000", 
                                        value=cliente_editando.get('cep_conjuge', '') if 'editar_pf_id' in st.session_state else "",
                                        key="cep_conjuge_pf")
                
                buscar_cep_conjuge = st.form_submit_button("Buscar CEP do Cônjuge")
                if buscar_cep_conjuge and st.session_state.get("cep_conjuge_pf", ""):
                    preencher_endereco('conjuge_pf')

                endereco_conjuge = st.text_input("Endereço", 
                                            value=cliente_editando.get('endereco_conjuge', '') if 'editar_pf_id' in st.session_state else "",
                                            key="endereco_conjuge_pf")
                numero_conjuge = st.text_input("Número", 
                                            value=cliente_editando.get('numero_conjuge', '') if 'editar_pf_id' in st.session_state else "",
                                            key="numero_conjuge_pf")
            with col_conjuge2:
                bairro_conjuge = st.text_input("Bairro", 
                                            value=cliente_editando.get('bairro_conjuge', '') if 'editar_pf_id' in st.session_state else "",
                                            key="bairro_conjuge_pf")
                cidade_conjuge = st.text_input("Cidade", 
                                            value=cliente_editando.get('cidade_conjuge', '') if 'editar_pf_id' in st.session_state else "",
                                            key="cidade_conjuge_pf")
                estado_conjuge = st.text_input("Estado", 
                                            value=cliente_editando.get('estado_conjuge', '') if 'editar_pf_id' in st.session_state else "",
                                            key="estado_conjuge_pf")
            # Termo de consentimento e botões
            st.markdown("""
            **Para os fins da Lei 13.709/18, o titular concorda com:**  
            (i) o tratamento de seus dados pessoais e de seu cônjuge, quando for o caso, para os fins relacionados ao cumprimento das obrigações
            previstas na Lei, nesta ficha cadastral ou dela decorrente; e  
            (ii) o envio de seus dados pessoais e da documentação respectiva a órgãos e entidades tais como a Secretaria da Fazenda Municipal,
            administração do condomínio, Cartórios, ao credor fiduciário, à companhia securitizadora e a outras pessoas, nos limites permitidos em Lei.
            """)
            
            # Botões de ação
            col1, col2 = st.columns(2)
            with col1:
                submitted_pf = st.form_submit_button("Salvar Cadastro")
            with col2:
                imprimir_pf = st.form_submit_button("Imprimir Formulário")
        
        # Processar após o formulário
        if submitted_pf:
            # Formatar os campos antes de salvar
            celular_formatado = formatar_telefone(st.session_state.get("celular_pf", ""))
            cpf_formatado = formatar_cpf(st.session_state.get("cpf_pf", ""))
            cep_formatado = re.sub(r'[^0-9]', '', st.session_state.get("cep_pf", ""))
            data_nascimento_formatada = data_nascimento.strftime('%d/%m/%Y') if data_nascimento else ""
            
            # Sempre processar campos do cônjuge/2° proponente (a decisão de usar ou não é feita depois)
            cpf_conjuge_formatado = formatar_cpf(st.session_state.get("cpf_conjuge_pf", ""))
            celular_conjuge_formatado = formatar_telefone(st.session_state.get("celular_conjuge_pf", ""))
            cep_conjuge_formatado = re.sub(r'[^0-9]', '', st.session_state.get("cep_conjuge_pf", ""))
            data_nascimento_conjuge_formatada = data_nascimento_conjuge.strftime('%d/%m/%Y') if data_nascimento_conjuge else ""

            if not nome or not cpf_formatado or not celular_formatado:
                st.error("Por favor, preencha os campos obrigatórios (*)")
            elif not validar_cpf(cpf_formatado):
                st.error("CPF inválido. Por favor, verifique o número.")
            else:
                novo_cliente = {
                    'nome': nome,
                    'genero': genero,
                    'data_nascimento': data_nascimento_formatada,
                    'celular': celular_formatado,
                    'cpf': cpf_formatado,
                    'email': email,
                    'nacionalidade': nacionalidade,
                    'profissao': profissao,
                    'estado_civil': estado_civil,
                    'uniao_estavel': "SIM" if uniao_estavel else "NÃO",
                    'regime_casamento': regime_casamento,
                    'cep': cep_formatado,
                    'endereco': st.session_state.get("endereco_pf", ""),
                    'numero': st.session_state.get("numero_pf", ""),
                    'bairro': st.session_state.get("bairro_pf", ""),
                    'cidade': st.session_state.get("cidade_pf", ""),
                    'estado': st.session_state.get("estado_pf", ""),
                    # Campos do cônjuge/2° proponente - sempre incluídos, mas podem ser vazios
                    'nome_conjuge': nome_conjuge,
                    'genero_conjuge': genero_conjuge,
                    'data_nascimento_conjuge': data_nascimento_conjuge_formatada,
                    'cpf_conjuge': cpf_conjuge_formatado,
                    'celular_conjuge': celular_conjuge_formatado,
                    'email_conjuge': email_conjuge,
                    'nacionalidade_conjuge': nacionalidade_conjuge,
                    'profissao_conjuge': profissao_conjuge,
                    'estado_civil_conjuge': estado_civil_conjuge,
                    'uniao_estavel_conjuge': "SIM" if uniao_estavel_conjuge else "NÃO",
                    'regime_casamento_conjuge': regime_casamento_conjuge,
                    'cep_conjuge': cep_conjuge_formatado,
                    'endereco_conjuge': st.session_state.get("endereco_conjuge_pf", ""),
                    'numero_conjuge': st.session_state.get("numero_conjuge_pf", ""),
                    'bairro_conjuge': st.session_state.get("bairro_conjuge_pf", ""),
                    'cidade_conjuge': st.session_state.get("cidade_conjuge_pf", ""),
                    'estado_conjuge': st.session_state.get("estado_conjuge_pf", ""),
                    'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                    'corretor': corretor,
                    'imobiliaria': imobiliaria,
                    'numero_negocio': numero_negocio
                }
                
                if 'editar_pf_id' in st.session_state:
                    novo_cliente['id'] = st.session_state['editar_pf_id']
                
                try:
                    salvar_cliente_pf(novo_cliente, st.session_state['usuario']['id'])
                    st.session_state.clientes_pf = carregar_clientes_pf(st.session_state['usuario']['id'])
                    st.success("Cliente cadastrado com sucesso!")
                    
                    if 'editar_pf_id' in st.session_state:
                        del st.session_state['editar_pf_id']
                        st.rerun()
                    
                    # Gera o PDF após salvar
                    pdf_path_pf = gerar_pdf_formatado('pf', novo_cliente)
                except Exception as e:
                    st.error(f"Erro ao salvar cliente: {e}")
        
        if imprimir_pf:
            # Formata os dados para impressão
            dados_impressao = {
                'nome': nome,
                'genero': genero,
                'data_nascimento': data_nascimento.strftime('%d/%m/%Y') if data_nascimento else "",
                'celular': formatar_telefone(st.session_state.get("celular_pf", "")),
                'cpf': formatar_cpf(st.session_state.get("cpf_pf", "")),
                'email': email,
                'nacionalidade': nacionalidade,
                'profissao': profissao,
                'estado_civil': estado_civil,
                'uniao_estavel': "SIM" if uniao_estavel else "NÃO",
                'regime_casamento': regime_casamento,
                'cep': st.session_state.get("cep_pf", ""),
                'endereco': st.session_state.get("endereco_pf", ""),
                'numero': st.session_state.get("numero_pf", ""),
                'bairro': st.session_state.get("bairro_pf", ""),
                'cidade': st.session_state.get("cidade_pf", ""),
                'estado': st.session_state.get("estado_pf", ""),
                'corretor': corretor,
                'imobiliaria': imobiliaria,
                'numero_negocio': numero_negocio,
                'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
            
            if tem_conjuge == "SIM":
                dados_impressao.update({
                    'nome_conjuge': nome_conjuge,
                    'genero_conjuge': genero_conjuge,
                    'data_nascimento_conjuge': data_nascimento_conjuge.strftime('%d/%m/%Y') if data_nascimento_conjuge else "",
                    'cpf_conjuge': formatar_cpf(st.session_state.get("cpf_conjuge_pf", "")),
                    'celular_conjuge': formatar_telefone(st.session_state.get("celular_conjuge_pf", "")),
                    'email_conjuge': email_conjuge,
                    'nacionalidade_conjuge': nacionalidade_conjuge,
                    'profissao_conjuge': profissao_conjuge,
                    'estado_civil_conjuge': estado_civil_conjuge,
                    'uniao_estavel_conjuge': "SIM" if uniao_estavel_conjuge else "NÃO",
                    'regime_casamento_conjuge': regime_casamento_conjuge,
                    'cep_conjuge': st.session_state.get("cep_conjuge_pf", ""),
                    'endereco_conjuge': st.session_state.get("endereco_conjuge_pf", ""),
                    'numero_conjuge': st.session_state.get("numero_conjuge_pf", ""),
                    'bairro_conjuge': st.session_state.get("bairro_conjuge_pf", ""),
                    'cidade_conjuge': st.session_state.get("cidade_conjuge_pf", ""),
                    'estado_conjuge': st.session_state.get("estado_conjuge_pf", "")
                })
            
            # Gera o PDF
            pdf_path_pf = gerar_pdf_formatado('pf', dados_impressao)
        
        # Botão de download fora do formulário
        if pdf_path_pf:
            with open(pdf_path_pf, "rb") as f:
                st.download_button(
                    "Baixar Ficha em PDF",
                    f,
                    file_name=f"ficha_pf_{nome if nome else 'sem_nome'}.pdf",
                    mime="application/pdf"
                )

    with tab2:
        st.header("Ficha Cadastral - Pessoa Jurídica")
        
        submitted_pj = False
        imprimir_pj = False
        
        # Verificar se estamos editando um registro existente
        if 'editar_pj_id' in st.session_state:
            cliente_editando = obter_cliente_pj_por_id(st.session_state['editar_pj_id'])
            if cliente_editando:
                st.warning(f"Editando registro ID: {st.session_state['editar_pj_id']}")
                if st.button("Cancelar Edição", key="cancelar_edicao_pj"):
                    del st.session_state['editar_pj_id']
                    st.rerun()
        
        with st.form(key="form_pj"):
            # Dados da Imobiliária
            st.subheader("Dados da Imobiliária")
            col1, col2 = st.columns(2)
            with col1:
                corretor = st.text_input("Corretor(a)", 
                                       value=cliente_editando['corretor'] if 'editar_pj_id' in st.session_state else "",
                                       key="corretor_pj")
                imobiliaria = st.text_input("Imobiliária", 
                                          value=cliente_editando['imobiliaria'] if 'editar_pj_id' in st.session_state else " ",
                                          key="imobiliaria_pj")
            with col2:
                numero_negocio = st.text_input("Nº do Negócio", 
                                             value=cliente_editando['numero_negocio'] if 'editar_pj_id' in st.session_state else "",
                                             key="numero_negocio_pj")
            
            # Dados da Pessoa Jurídica
            st.subheader("Dados da Pessoa Jurídica")
            razao_social = st.text_input("Razão Social (conforme o cartão de CNPJ) *", 
                                       value=cliente_editando['razao_social'] if 'editar_pj_id' in st.session_state else "",
                                       key="razao_social_pj")
            cnpj = st.text_input("CNPJ *", 
                               value=cliente_editando['cnpj'] if 'editar_pj_id' in st.session_state else "",
                               key="cnpj_pj", 
                               help="Formato: 00.000.000/0000-00")
            email = st.text_input("E-mail", 
                                value=cliente_editando['email'] if 'editar_pj_id' in st.session_state else "",
                                key="email_pj")
            
            # Endereço da Empresa
            st.subheader("Endereço da Empresa")
            col1, col2 = st.columns(2)
            with col1:
                telefone_empresa = st.text_input("Telefone", 
                                               value=cliente_editando['telefone_empresa'] if 'editar_pj_id' in st.session_state else "",
                                               key="telefone_empresa_pj", 
                                               help="Formato: (00) 0000-0000")
                cep_empresa = st.text_input("CEP", 
                                          value=cliente_editando['cep_empresa'] if 'editar_pj_id' in st.session_state else "",
                                          key="cep_empresa_pj", 
                                          help="Formato: 00000-000")
                
                buscar_cep_empresa = st.form_submit_button("Buscar CEP Empresa")
                if buscar_cep_empresa:
                    preencher_endereco('empresa_pj')
                
                endereco_empresa = st.text_input("Endereço", 
                                               value=cliente_editando['endereco_empresa'] if 'editar_pj_id' in st.session_state else "",
                                               key="endereco_empresa_pj")
                numero_empresa = st.text_input("Número", 
                                             value=cliente_editando['numero_empresa'] if 'editar_pj_id' in st.session_state else "",
                                             key="numero_empresa_pj")
            with col2:
                bairro_empresa = st.text_input("Bairro", 
                                             value=cliente_editando['bairro_empresa'] if 'editar_pj_id' in st.session_state else "",
                                             key="bairro_empresa_pj")
                cidade_empresa = st.text_input("Cidade", 
                                             value=cliente_editando['cidade_empresa'] if 'editar_pj_id' in st.session_state else "",
                                             key="cidade_empresa_pj")
                estado_empresa = st.text_input("Estado", 
                                             value=cliente_editando['estado_empresa'] if 'editar_pj_id' in st.session_state else "",
                                             key="estado_empresa_pj")
            

            # Dados do Administrador
            st.subheader("Dados do Administrador")

            # Container principal com 2 colunas
            col1, col2 = st.columns(2)

            with col1:
                # Primeira coluna (esquerda)
                genero_administrador = st.radio("Gênero", ["MASCULINO", "FEMININO"], 
                                              index=0 if 'editar_pj_id' not in st.session_state or cliente_editando['genero_administrador'] == "MASCULINO" else 1,
                                              key="genero_administrador_pj",
                                              horizontal=True)
                
                nome_administrador = st.text_input("Nome Completo *", 
                                                 value=cliente_editando['nome_administrador'] if 'editar_pj_id' in st.session_state else "",
                                                 key="nome_administrador_pj")
                
                data_nascimento_administrador = st.date_input("Data de Nascimento", 
                                                            value=datetime.strptime(cliente_editando['data_nascimento_administrador'], '%d/%m/%Y') if 'editar_pj_id' in st.session_state and cliente_editando['data_nascimento_administrador'] else None,
                                                            format="DD/MM/YYYY",
                                                            key="data_nascimento_administrador_pj")
                
                st.markdown("**Dados Complementares**")
                
                # Sub-colunas para CPF e Celular
                cpf_celular = st.columns(2)
                with cpf_celular[0]:
                    cpf_administrador = st.text_input("CPF *", 
                                                    value=cliente_editando['cpf_administrador'] if 'editar_pj_id' in st.session_state else "",
                                                    key="cpf_administrador_pj",
                                                    help="Formato: 000.000.000-00")
                with cpf_celular[1]:
                    celular_administrador = st.text_input("Celular *", 
                                                        value=cliente_editando['celular_administrador'] if 'editar_pj_id' in st.session_state else "",
                                                        key="celular_administrador_pj",
                                                        help="Formato: (00) 00000-0000")

            with col2:
                # Segunda coluna (direita)
                nacionalidade_administrador = st.text_input("Nacionalidade", 
                                                          value=cliente_editando.get('nacionalidade_administrador', 'BRASILEIRA') if 'editar_pj_id' in st.session_state else "BRASILEIRA", 
                                                          key="nacionalidade_administrador_pj")
                
                profissao_administrador = st.text_input("Profissão", 
                                                      value=cliente_editando.get('profissao_administrador', '') if 'editar_pj_id' in st.session_state else "",
                                                      key="profissao_administrador_pj")
                
                email_administrador = st.text_input("E-mail", 
                                                 value=cliente_editando.get('email_administrador', '') if 'editar_pj_id' in st.session_state else "",
                                                 key="email_administrador_pj")
                
                # Sub-colunas para Estado Civil e Regime
                civil_regime = st.columns(2)
                with civil_regime[0]:
                    estado_civil_opcoes = ["", "CASADO(A)", "SOLTEIRO(A)", "VIÚVO(A)", "DIVORCIADO(A)"]
                    estado_civil_index = estado_civil_opcoes.index(cliente_editando['estado_civil_administrador']) if 'editar_pj_id' in st.session_state and cliente_editando.get('estado_civil_administrador', '') in estado_civil_opcoes else 0
                    estado_civil_administrador = st.selectbox("Estado Civil", 
                                                            estado_civil_opcoes,
                                                            index=estado_civil_index,
                                                            key="estado_civil_administrador_pj")
                with civil_regime[1]:
                    regime_opcoes = ["", "COMUNHÃO UNIVERSAL DE BENS", "SEPARAÇÃO DE BENS", 
                                    "COMUNHÃO PARCIAL DE BENS", "COMUNHÃO DE BENS (REGIME ÚNICO ANTES DE 1977)"]
                    regime_index = regime_opcoes.index(cliente_editando['regime_casamento_administrador']) if 'editar_pj_id' in st.session_state and cliente_editando.get('regime_casamento_administrador', '') in regime_opcoes else 0
                    regime_casamento_administrador = st.selectbox("Regime de Casamento", 
                                                                regime_opcoes,
                                                                index=regime_index,
                                                                key="regime_casamento_administrador_pj")
                
                # União Estável alinhada à direita
                uniao_estavel_administrador = st.checkbox("União Estável", 
                                                        value=True if 'editar_pj_id' in st.session_state and cliente_editando.get('uniao_estavel_administrador', '') == "SIM" else False,
                                                        key="uniao_estavel_administrador_pj")
            
            # Endereço do Administrador
            st.subheader("Endereço do Administrador")
            col1, col2 = st.columns(2)
            with col1:
                cep_administrador = st.text_input("CEP", 
                                                value=cliente_editando.get('cep_administrador', '') if 'editar_pj_id' in st.session_state else "",
                                                key="cep_administrador_pj", 
                                                help="Formato: 00000-000")
                
                buscar_cep_administrador = st.form_submit_button("Buscar CEP Administrador")
                if buscar_cep_administrador:
                    preencher_endereco('administrador_pj')
                
                endereco_administrador = st.text_input("Endereço", 
                                                     value=cliente_editando.get('endereco_administrador', '') if 'editar_pj_id' in st.session_state else "",
                                                     key="endereco_administrador_pj")
                numero_administrador = st.text_input("Número", 
                                                   value=cliente_editando.get('numero_administrador', '') if 'editar_pj_id' in st.session_state else "",
                                                   key="numero_administrador_pj")
            with col2:
                bairro_administrador = st.text_input("Bairro", 
                                                   value=cliente_editando.get('bairro_administrador', '') if 'editar_pj_id' in st.session_state else "",
                                                   key="bairro_administrador_pj")
                cidade_administrador = st.text_input("Cidade", 
                                                   value=cliente_editando.get('cidade_administrador', '') if 'editar_pj_id' in st.session_state else "",
                                                   key="cidade_administrador_pj")
                estado_administrador = st.text_input("Estado", 
                                                   value=cliente_editando.get('estado_administrador', '') if 'editar_pj_id' in st.session_state else "",
                                                   key="estado_administrador_pj")
            
            # Nova seção para Pessoas Vinculadas
            st.subheader("Pessoas Vinculadas à Empresa")
            
            # Se estiver editando, carregar pessoas vinculadas existentes
            pessoas_vinculadas = []
            if 'editar_pj_id' in st.session_state:
                pessoas_vinculadas = obter_pessoas_vinculadas(st.session_state['editar_pj_id'])
            
            # Container para adicionar nova pessoa
            # No formulário de adição de pessoa vinculada (dentro do with tab2:)
            with st.expander("Adicionar Nova Pessoa Vinculada"):
                col1, col2 = st.columns(2)
                with col1:
                    tipo_pessoa = st.radio("Tipo de Pessoa", ["Sócio", "Diretor", "Administrador", "Outro"], horizontal=True, key="tipo_pessoa_pj")
                    nome_pessoa = st.text_input("Nome Completo *", key="nome_pessoa_pj")
                    genero_pessoa = st.radio("Gênero", ["MASCULINO", "FEMININO"], key="genero_pessoa_pj", horizontal=True)
                    cpf_pessoa = st.text_input("CPF *", help="Formato: 000.000.000-00", key="cpf_pessoa_pj")
                    data_nascimento_pessoa = st.date_input("Data de Nascimento", format="DD/MM/YYYY", key="data_nascimento_pessoa_pj")
                    
                    # Campos novos para estado civil
                    estado_civil_pessoa = st.selectbox("Estado Civil", 
                                                    ["", "CASADO(A)", "SOLTEIRO(A)", "VIÚVO(A)", "DIVORCIADO(A)"],
                                                    key="estado_civil_pessoa_pj")
                    
                    regime_casamento_pessoa = st.selectbox("Regime de Casamento", 
                                                        ["", "COMUNHÃO UNIVERSAL DE BENS", "SEPARAÇÃO DE BENS", 
                                                        "COMUNHÃO PARCIAL DE BENS", "COMUNHÃO DE BENS (REGIME ÚNICO ANTES DE 1977)"],
                                                        key="regime_casamento_pessoa_pj")
                    
                    uniao_estavel_pessoa = st.checkbox("União Estável", key="uniao_estavel_pessoa_pj")
                    
                with col2:
                    cargo_pessoa = st.text_input("Cargo/Função", key="cargo_pessoa_pj")
                    celular_pessoa = st.text_input("Celular", help="Formato: (00) 00000-0000", key="celular_pessoa_pj")
                    email_pessoa = st.text_input("E-mail", key="email_pessoa_pj")
                    
                    # Campos de endereço
                    st.markdown("**Endereço**")
                    cep_pessoa = st.text_input("CEP", help="Formato: 00000-000", key="cep_pessoa_pj")
                    
                    buscar_cep_pessoa = st.form_submit_button("Buscar CEP")
                    if buscar_cep_pessoa and st.session_state.get("cep_pessoa_pj", ""):
                        cep_limpo = re.sub(r'[^0-9]', '', st.session_state.cep_pessoa_pj)
                        if len(cep_limpo) == 8:
                            endereco_info = buscar_cep(cep_limpo)
                            if endereco_info:
                                st.session_state.endereco_pessoa_pj = endereco_info.get('logradouro', '')
                                st.session_state.bairro_pessoa_pj = endereco_info.get('bairro', '')
                                st.session_state.cidade_pessoa_pj = endereco_info.get('cidade', '')
                                st.session_state.estado_pessoa_pj = endereco_info.get('estado', '')
                                st.rerun()
                    
                    endereco_pessoa = st.text_input("Endereço", key="endereco_pessoa_pj")
                    numero_pessoa = st.text_input("Número", key="numero_pessoa_pj")
                    bairro_pessoa = st.text_input("Bairro", key="bairro_pessoa_pj")
                    cidade_pessoa = st.text_input("Cidade", key="cidade_pessoa_pj")
                    estado_pessoa = st.text_input("Estado", key="estado_pessoa_pj")
                
                # Botão para adicionar a pessoa
                if st.form_submit_button("Adicionar Pessoa"):
                    if nome_pessoa and cpf_pessoa:
                        nova_pessoa = {
                            'tipo': tipo_pessoa,
                            'nome': nome_pessoa,
                            'genero': genero_pessoa,
                            'cpf': cpf_pessoa,
                            'data_nascimento': data_nascimento_pessoa.strftime('%d/%m/%Y') if data_nascimento_pessoa else "",
                            'estado_civil': estado_civil_pessoa,
                            'regime_casamento': regime_casamento_pessoa,
                            'uniao_estavel': "SIM" if uniao_estavel_pessoa else "NÃO",
                            'cargo': cargo_pessoa,
                            'celular': celular_pessoa,
                            'email': email_pessoa,
                            'cep': re.sub(r'[^0-9]', '', st.session_state.get("cep_pessoa_pj", "")),
                            'endereco': st.session_state.get("endereco_pessoa_pj", ""),
                            'numero': st.session_state.get("numero_pessoa_pj", ""),
                            'bairro': st.session_state.get("bairro_pessoa_pj", ""),
                            'cidade': st.session_state.get("cidade_pessoa_pj", ""),
                            'estado': st.session_state.get("estado_pessoa_pj", ""),
                            'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                        }
                        
                        if 'editar_pj_id' in st.session_state:
                            adicionar_pessoa_vinculada(st.session_state['editar_pj_id'], nova_pessoa)
                            st.success("Pessoa adicionada com sucesso!")
                            st.rerun()
                        else:
                            if 'pessoas_temp' not in st.session_state:
                                st.session_state.pessoas_temp = []
                            st.session_state.pessoas_temp.append(nova_pessoa)
                            st.success("Pessoa adicionada (será salva com a empresa)")
            
            # Lista de pessoas vinculadas (para visualização e remoção)
            if pessoas_vinculadas or ('pessoas_temp' in st.session_state and st.session_state.pessoas_temp):
                st.markdown("**Pessoas Vinculadas Cadastradas**")
                
                # Combine pessoas temporárias e do banco de dados
                todas_pessoas = []
                if 'pessoas_temp' in st.session_state:
                    todas_pessoas.extend(st.session_state.pessoas_temp)
                if pessoas_vinculadas:
                    todas_pessoas.extend(pessoas_vinculadas)
                
                for idx, pessoa in enumerate(todas_pessoas):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"""
                        **{pessoa.get('tipo', 'Pessoa')}**: {pessoa['nome']}  
                        CPF: {formatar_cpf(pessoa['cpf'])} | Cargo: {pessoa.get('cargo', '')}  
                        Celular: {formatar_telefone(pessoa.get('celular', ''))} | E-mail: {pessoa.get('email', '')}
                        """)
                    with col2:
                        if st.form_submit_button(f"Remover {idx+1}"):
                            if 'id' in pessoa:  # Pessoa já está no banco
                                remover_pessoa_vinculada(pessoa['id'])
                                st.success("Pessoa removida!")
                                st.rerun()
                            else:  # Pessoa temporária
                                st.session_state.pessoas_temp.remove(pessoa)
                                st.success("Pessoa removida!")
                                st.rerun()
            
            # Termo de consentimento
            st.markdown("""
            **Para os fins da Lei 13.709/18, o titular concorda com:**  
            (i) o tratamento de seus dados pessoais e de seu cônjuge, quando for o caso, para os fins relacionados ao cumprimento das obrigações
            previstas na Lei, nesta ficha cadastral ou dela decorrente; e  
            (ii) o envio de seus dados pessoais e da documentação respectiva a órgãos e entidades tais como a Secretaria da Fazenda Municipal,
            administração do condomínio, Cartórios, ao credor fiduciário, à companhia securitizadora e a outras pessoas, nos limites permitidos em Lei.
            """)
        
            # Botões de ação
            col1, col2 = st.columns(2)
            with col1:
                submitted_pj = st.form_submit_button("Salvar Cadastro")
            with col2:
                imprimir_pj = st.form_submit_button("Imprimir Formulário")
        
        # Processar após o formulário
        if submitted_pj:
            # Formatar os campos antes de salvar
            cnpj_formatado = formatar_cnpj(st.session_state.get("cnpj_pj", ""))
            cpf_administrador_formatado = formatar_cpf(st.session_state.get("cpf_administrador_pj", ""))
            celular_administrador_formatado = formatar_telefone(st.session_state.get("celular_administrador_pj", ""))
            telefone_empresa_formatado = formatar_telefone(st.session_state.get("telefone_empresa_pj", ""))
            cep_empresa_formatado = re.sub(r'[^0-9]', '', st.session_state.get("cep_empresa_pj", ""))
            cep_administrador_formatado = re.sub(r'[^0-9]', '', st.session_state.get("cep_administrador_pj", ""))
            data_nascimento_administrador_formatada = data_nascimento_administrador.strftime('%d/%m/%Y') if data_nascimento_administrador else ""
            
            if not razao_social or not cnpj_formatado or not nome_administrador or not cpf_administrador_formatado or not celular_administrador_formatado:
                st.error("Por favor, preencha os campos obrigatórios (*)")
            elif not validar_cpf(cpf_administrador_formatado):
                st.error("CPF do administrador inválido. Por favor, verifique o número.")
            else:
                novo_cliente = {
                    'razao_social': razao_social,
                    'cnpj': cnpj_formatado,
                    'email': email,
                    'telefone_empresa': telefone_empresa_formatado,
                    'cep_empresa': cep_empresa_formatado,
                    'endereco_empresa': st.session_state.get("endereco_empresa_pj", ""),
                    'numero_empresa': st.session_state.get("numero_empresa_pj", ""),
                    'bairro_empresa': st.session_state.get("bairro_empresa_pj", ""),
                    'cidade_empresa': st.session_state.get("cidade_empresa_pj", ""),
                    'estado_empresa': st.session_state.get("estado_empresa_pj", ""),
                    'genero_administrador': genero_administrador,
                    'nome_administrador': nome_administrador,
                    'data_nascimento_administrador': data_nascimento_administrador_formatada,
                    'cpf_administrador': cpf_administrador_formatado,
                    'celular_administrador': celular_administrador_formatado,
                    'nacionalidade_administrador': nacionalidade_administrador,
                    'profissao_administrador': profissao_administrador,
                    'estado_civil_administrador': estado_civil_administrador,
                    'uniao_estavel_administrador': "SIM" if uniao_estavel_administrador else "NÃO",
                    'regime_casamento_administrador': regime_casamento_administrador,
                    'cep_administrador': cep_administrador_formatado,
                    'endereco_administrador': st.session_state.get("endereco_administrador_pj", ""),
                    'numero_administrador': st.session_state.get("numero_administrador_pj", ""),
                    'bairro_administrador': st.session_state.get("bairro_administrador_pj", ""),
                    'cidade_administrador': st.session_state.get("cidade_administrador_pj", ""),
                    'estado_administrador': st.session_state.get("estado_administrador_pj", ""),
                    'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                    'corretor': corretor,
                    'imobiliaria': imobiliaria,
                    'numero_negocio': numero_negocio
                }
                
                if 'editar_pj_id' in st.session_state:
                    novo_cliente['id'] = st.session_state['editar_pj_id']
                
                try:
                    empresa_id = salvar_cliente_pj(novo_cliente, st.session_state['usuario']['id'])
                    
                    # Salvar pessoas temporárias no banco de dados
                    if 'pessoas_temp' in st.session_state and st.session_state.pessoas_temp:
                        for pessoa in st.session_state.pessoas_temp:
                            adicionar_pessoa_vinculada(empresa_id, pessoa)
                        del st.session_state.pessoas_temp
                    
                    st.session_state.clientes_pj = carregar_clientes_pj(st.session_state['usuario']['id'])
                    st.success("Cliente cadastrado com sucesso!")
                    
                    if 'editar_pj_id' in st.session_state:
                        del st.session_state['editar_pj_id']
                        st.rerun()
                    
                    # Gera o PDF após salvar incluindo pessoas vinculadas
                    dados_pdf = novo_cliente.copy()
                    if 'pessoas_temp' in st.session_state:
                        dados_pdf['pessoas_vinculadas'] = st.session_state.pessoas_temp
                    elif 'editar_pj_id' not in st.session_state:  # Novo registro sem pessoas
                        dados_pdf['pessoas_vinculadas'] = []
                    else:  # Edição de registro existente
                        dados_pdf['pessoas_vinculadas'] = obter_pessoas_vinculadas(empresa_id)
                    
                    pdf_path_pj = gerar_pdf_formatado('pj', dados_pdf)
                except Exception as e:
                    st.error(f"Erro ao salvar cliente: {e}")

        if imprimir_pj:
            # Formata os dados para impressão
            dados_impressao = {
                'razao_social': razao_social,
                'cnpj': formatar_cnpj(st.session_state.get("cnpj_pj", "")),
                'email': email,
                'telefone_empresa': formatar_telefone(st.session_state.get("telefone_empresa_pj", "")),
                'cep_empresa': st.session_state.get("cep_empresa_pj", ""),
                'endereco_empresa': st.session_state.get("endereco_empresa_pj", ""),
                'numero_empresa': st.session_state.get("numero_empresa_pj", ""),
                'bairro_empresa': st.session_state.get("bairro_empresa_pj", ""),
                'cidade_empresa': st.session_state.get("cidade_empresa_pj", ""),
                'estado_empresa': st.session_state.get("estado_empresa_pj", ""),
                'genero_administrador': genero_administrador,
                'nome_administrador': nome_administrador,
                'data_nascimento_administrador': data_nascimento_administrador.strftime('%d/%m/%Y') if data_nascimento_administrador else "",
                'cpf_administrador': formatar_cpf(st.session_state.get("cpf_administrador_pj", "")),
                'celular_administrador': formatar_telefone(st.session_state.get("celular_administrador_pj", "")),
                'nacionalidade_administrador': nacionalidade_administrador,
                'profissao_administrador': profissao_administrador,
                'estado_civil_administrador': estado_civil_administrador,
                'uniao_estavel_administrador': "SIM" if uniao_estavel_administrador else "NÃO",
                'regime_casamento_administrador': regime_casamento_administrador,
                'cep_administrador': st.session_state.get("cep_administrador_pj", ""),
                'endereco_administrador': st.session_state.get("endereco_administrador_pj", ""),
                'numero_administrador': st.session_state.get("numero_administrador_pj", ""),
                'bairro_administrador': st.session_state.get("bairro_administrador_pj", ""),
                'cidade_administrador': st.session_state.get("cidade_administrador_pj", ""),
                'estado_administrador': st.session_state.get("estado_administrador_pj", ""),
                'corretor': corretor,
                'imobiliaria': imobiliaria,
                'numero_negocio': numero_negocio,
                'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
            
            # Incluir pessoas vinculadas no PDF
            if 'pessoas_temp' in st.session_state:
                dados_impressao['pessoas_vinculadas'] = st.session_state.pessoas_temp
            elif 'editar_pj_id' in st.session_state:
                dados_impressao['pessoas_vinculadas'] = obter_pessoas_vinculadas(st.session_state['editar_pj_id'])
            else:
                dados_impressao['pessoas_vinculadas'] = []
            
            # Gera o PDF
            pdf_path_pj = gerar_pdf_formatado('pj', dados_impressao)
        
        # Botão de download fora do formulário
        if pdf_path_pj:
            with open(pdf_path_pj, "rb") as f:
                st.download_button(
                    "Baixar Ficha em PDF",
                    f,
                    file_name=f"ficha_pj_{razao_social if razao_social else 'sem_razao_social'}.pdf",
                    mime="application/pdf"
                )

    with tab3:
        st.header("Consulta de Registros")
        
        tipo_consulta = st.radio("Tipo de Consulta", 
                                ["Pessoa Física", "Pessoa Jurídica"], 
                                horizontal=True)
        
        if tipo_consulta == "Pessoa Física":
            df = st.session_state.clientes_pf.copy()
            id_col = 'id'
            nome_col = 'nome'
            doc_col = 'cpf'
            tabela = 'clientes_pf'
        else:
            df = st.session_state.clientes_pj.copy()
            id_col = 'id'
            nome_col = 'razao_social'
            doc_col = 'cnpj'
            tabela = 'clientes_pj'
        
        if not df.empty:
            # Filtros
            col1, col2 = st.columns(2)
            
            with col1:
                filtro_nome = st.text_input(f"Filtrar por {'nome' if tipo_consulta == 'Pessoa Física' else 'razão social'}")
            
            with col2:
                filtro_doc = st.text_input(f"Filtrar por {'CPF' if tipo_consulta == 'Pessoa Física' else 'CNPJ'}")
            
            # Aplicar filtros
            if filtro_nome:
                df = df[df[nome_col].str.contains(filtro_nome, case=False, na=False)]
            
            if filtro_doc:
                df = df[df[doc_col].str.contains(filtro_doc, case=False, na=False)]
            
            # Formatar dados para exibição
            df_formatado = df.copy()
            for col in df_formatado.columns:
                if 'data' in col.lower():
                    df_formatado[col] = df_formatado[col].apply(lambda x: formatar_data_ptbr(x) if pd.notna(x) else '')
                if doc_col in col or 'cpf' in col.lower() or 'cnpj' in col.lower():
                    if tipo_consulta == "Pessoa Física":
                        df_formatado[col] = df_formatado[col].apply(lambda x: formatar_cpf(x) if pd.notna(x) else '')
                    else:
                        df_formatado[col] = df_formatado[col].apply(lambda x: formatar_cnpj(x) if pd.notna(x) else '')
                if 'celular' in col.lower() or 'telefone' in col.lower():
                    df_formatado[col] = df_formatado[col].apply(lambda x: formatar_telefone(x) if pd.notna(x) else '')
            
            # Mostrar tabela com opção de seleção
            st.dataframe(df_formatado)
            
            # Selecionar registro para ações
            if not df_formatado.empty:
                registros = df_formatado[[id_col, nome_col, doc_col]].to_dict('records')
                opcoes = {f"{r[id_col]} - {r[nome_col]} - {r[doc_col]}": r[id_col] for r in registros}
                
                selected = st.selectbox("Selecione um registro para ações:", options=list(opcoes.keys()))
                registro_id = opcoes[selected]
                
                # Verificar permissões
                if tipo_consulta == "Pessoa Física":
                    cliente = obter_cliente_pf_por_id(registro_id)
                else:
                    cliente = obter_cliente_pj_por_id(registro_id)
                
                # Verifica permissão - mais robusta
                bloqueio = False
                if not st.session_state['usuario']['is_admin']:
                    if 'usuario_id' not in cliente or cliente['usuario_id'] != st.session_state['usuario']['id']:
                        st.error("Você não tem permissão para editar/excluir este registro")
                        bloqueio = True
                
                # Botões de ação
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("Reimprimir Ficha", disabled=bloqueio):            
                        # Buscar dados completos no banco
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute(f"SELECT * FROM {tabela} WHERE id = ?", (registro_id,))
                        dados = cursor.fetchone()
                        conn.close()
                        
                        if dados:
                            # Converter para dicionário com nomes de colunas
                            cols = [column[0] for column in cursor.description]
                            dados_dict = dict(zip(cols, dados))
                            
                            # Aplicar formatação para garantir que seja igual ao PDF original
                            dados_formatados = {}
                            for key, value in dados_dict.items():
                                if value is None:
                                    value = ''
                                
                                # Formatar datas
                                if 'data' in key.lower() and value:
                                    try:
                                        if re.match(r'\d{2}/\d{2}/\d{4}', str(value)):
                                            dados_formatados[key] = value
                                        else:
                                            dados_formatados[key] = datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
                                    except:
                                        dados_formatados[key] = value
                                
                                # Formatar CPF/CNPJ
                                elif ('cpf' in key.lower() or 'cnpj' in key.lower()) and value:
                                    if 'cpf' in key.lower():
                                        dados_formatados[key] = formatar_cpf(value)
                                    else:
                                        dados_formatados[key] = formatar_cnpj(value)
                                
                                # Formatar telefones
                                elif ('celular' in key.lower() or 'telefone' in key.lower()) and value:
                                    dados_formatados[key] = formatar_telefone(value)
                                
                                # Manter outros valores como estão
                                else:
                                    dados_formatados[key] = value
                            
                            # Garantir que campos booleanos estejam corretos
                            if tipo_consulta == "Pessoa Física":
                                for campo in ['uniao_estavel', 'uniao_estavel_conjuge']:
                                    if campo in dados_formatados:
                                        dados_formatados[campo] = 'SIM' if dados_formatados[campo] == 'SIM' else 'NÃO'
                            else:
                                if 'uniao_estavel_administrador' in dados_formatados:
                                    dados_formatados['uniao_estavel_administrador'] = 'SIM' if dados_formatados['uniao_estavel_administrador'] == 'SIM' else 'NÃO'
                            
                            # Para PJ, adicionar pessoas vinculadas
                            if tipo_consulta == "Pessoa Jurídica":
                                dados_formatados['pessoas_vinculadas'] = obter_pessoas_vinculadas(registro_id)
                            
                            # Gerar PDF
                            pdf_path = gerar_pdf_formatado('pf' if tipo_consulta == "Pessoa Física" else 'pj', dados_formatados)
                            
                            # Botão de download
                            with open(pdf_path, "rb") as f:
                                nome_arquivo = f"ficha_{'pf' if tipo_consulta == 'Pessoa Física' else 'pj'}_reimpressao_{dados_formatados.get(nome_col, 'sem_nome')}.pdf"
                                st.download_button(
                                    "Baixar Ficha em PDF",
                                    f,
                                    file_name=nome_arquivo,
                                    mime="application/pdf"
                                )
                
                with col2:
                    if st.button("Editar Registro", disabled=bloqueio):
                        if tipo_consulta == "Pessoa Física":
                            st.session_state['editar_pf_id'] = registro_id
                        else:
                            st.session_state['editar_pj_id'] = registro_id
                        st.rerun()               


                with col3:
                    if st.button("Excluir Registro", disabled=bloqueio):
                        if tipo_consulta == "Pessoa Física":
                            excluir_cliente_pf(registro_id)
                            st.session_state.clientes_pf = carregar_clientes_pf(
                                st.session_state['usuario']['id'] if not st.session_state['usuario']['is_admin'] else None
                            )
                        else:
                            excluir_cliente_pj(registro_id)
                            st.session_state.clientes_pj = carregar_clientes_pj(
                                st.session_state['usuario']['id'] if not st.session_state['usuario']['is_admin'] else None
                            )
                        
                        st.success("Registro excluído com sucesso!")
                        time.sleep(1)
                        st.rerun()
        with tab4:
            st.header("Simulador Financeiro")
            try:
                from simulador import main as simulador_main
                simulador_main()
            except Exception as e:
                st.error(f"Erro ao carregar o simulador: {e}")
                time.sleep(1)
                st.rerun()
        #  Aqui       
        with tab5:
            st.header("Backup e Restauração de Dados")
            
            if st.session_state['usuario']['is_admin']:
                st.subheader("Fazer Backup Agora")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Backup Local"):
                        if fazer_backup_banco_dados():
                            st.success("Backup local realizado com sucesso!")
                        else:
                            st.error("Falha ao realizar backup local")
                
                with col2:
                    if GITHUB_TOKEN and st.button("Backup no GitHub"):
                        if fazer_backup_github():
                            st.success("Backup no GitHub realizado com sucesso!")
                        else:
                            st.error("Falha ao realizar backup no GitHub")
                
                st.subheader("Restaurar Backup")
                
                # Restaurar do GitHub
                if GITHUB_TOKEN and st.button("Restaurar do GitHub"):
                    st.warning("Esta ação irá substituir todos os dados atuais. Continuar?")
                    if st.button("Confirmar Restauração do GitHub"):
                        if restaurar_backup_github():
                            st.success("Backup do GitHub restaurado com sucesso! A página será recarregada.")
                            time.sleep(2)
                            st.rerun()
                
                # Restaurar backup local (mantenha o código existente)
                backups = []
                if os.path.exists(BACKUP_DIR):
                    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith('db_backup_')], reverse=True)
                
                if backups:
                    backup_selecionado = st.selectbox("Selecione um backup local para restaurar", backups)
                    
                    if st.button("Restaurar Backup Local Selecionado"):
                        st.warning("Esta ação irá substituir todos os dados atuais. Continuar?")
                        if st.button("Confirmar Restauração Local"):
                            if restaurar_backup(str(BACKUP_DIR / backup_selecionado)):
                                st.success("Backup local restaurado com sucesso! A página será recarregada.")
                                time.sleep(2)
                                st.rerun()
                else:
                    st.info("Nenhum backup local encontrado")
            else:
                st.warning("Apenas administradores podem acessar esta funcionalidade")
