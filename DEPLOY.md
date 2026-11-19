# Deploy em produção (Docker gerenciado)

Imagem de produção: `Dockerfile` na raiz do repositório.

## O que a imagem faz

- Python 3.11 com o executável `git` (o `formulario.py` faz `import git`).
- Instala `requirements.txt` + `streamlit==1.45.0`, `gitpython` e `pillow`.
- Sobe o Streamlit em `0.0.0.0:$PORT` (padrão `8501`).
- Grava o banco SQLite em `/app/persistent_data` — monte um volume/disco nesse caminho.

## Railway

1. New Project → Deploy from GitHub repo (branch `main`).
2. O Railway detecta o `Dockerfile` automaticamente.
3. Service → Settings → Volumes → novo volume montado em `/app/persistent_data`.
4. Deploy. O Railway injeta `PORT` e a imagem já respeita essa variável.
5. Settings → Networking → Generate Domain para ter a URL pública.

## Render

1. New → Web Service → Docker (branch `main`).
2. Health Check Path: `/_stcore/health`.
3. Disk: mount path `/app/persistent_data`, 1 GB.
4. Deploy. O Render injeta `PORT` (10000 por padrão) e a imagem já respeita.
5. Disco persistente só existe em plano pago; no plano free o banco é perdido a
   cada deploy ou reinício.

## Depois do primeiro deploy

- Login inicial: `admin` / `admin`, criado automaticamente na primeira execução.
  Troque a senha em seguida.
- A recuperação de senha por e-mail usa credenciais SMTP escritas no
  `formulario.py`; em produção elas devem sair do código.
- `.github/workflows/aws.yml` continua sendo o template vazio da AWS e não faz
  parte deste fluxo.
