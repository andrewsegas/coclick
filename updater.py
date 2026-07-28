"""Atualização do CoClick direto do GitHub (sem git, sem instalador).

A "versão" é o hash do último commit da branch ``main``. O app guarda o hash
atual no ``config.ini`` (seção ``[Atualizacao]``) e compara com o do GitHub;
quando difere, baixa o ZIP da branch e copia por cima da instalação. O
``config.ini`` e demais arquivos do ``.gitignore`` não estão no ZIP, então as
configurações do usuário são preservadas naturalmente.

Stdlib-only; importa apenas :mod:`notifier` para reutilizar o contexto SSL que
tolera antivírus/proxy interceptando HTTPS.
"""

import configparser
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

import notifier

REPO = "andrewsegas/coclick"
BRANCH = "main"
URL_API = f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"
URL_ZIP = f"https://github.com/{REPO}/archive/refs/heads/{BRANCH}.zip"

# Nunca sobrescrever/copiar por cima destes (defensivo — nem deveriam estar no ZIP).
PRESERVAR = {"config.ini", "configbkp.ini", ".git", "__pycache__"}

_TIMEOUT = 15  # segundos


def _base_dir():
    """Pasta da instalação (onde este arquivo está)."""
    return os.path.dirname(os.path.abspath(__file__))


def _config_path():
    return os.path.join(_base_dir(), "config.ini")


# --------------------------------------------------------------------------- #
# Versão local (config.ini) e remota (GitHub)
# --------------------------------------------------------------------------- #
def sha_local():
    config = configparser.ConfigParser()
    if os.path.exists(_config_path()):
        config.read(_config_path())
    return config.get("Atualizacao", "commit", fallback="").strip()


def salvar_sha(sha):
    arquivo = _config_path()
    config = configparser.ConfigParser()
    if os.path.exists(arquivo):
        config.read(arquivo)
    if "Atualizacao" not in config:
        config["Atualizacao"] = {}
    config["Atualizacao"]["commit"] = sha
    with open(arquivo, "w") as f:
        config.write(f)


def sha_remoto():
    """Hash do último commit da main, ou ``""`` em qualquer falha."""
    req = urllib.request.Request(URL_API, headers={"User-Agent": "CoClick"})
    try:
        with urllib.request.urlopen(
            req, timeout=_TIMEOUT, context=notifier._ssl_context()
        ) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
        return str(dados.get("sha", "")).strip()
    except Exception:
        return ""


def ha_atualizacao():
    """Retorna ``(tem_update, sha_remoto)``.

    Na primeira checagem (sem sha local), grava o remoto como baseline e não
    avisa — quem já tem este módulo está na versão que o introduziu.
    """
    remoto = sha_remoto()
    if not remoto:
        return False, ""
    local = sha_local()
    if not local:
        salvar_sha(remoto)
        return False, remoto
    return (remoto != local), remoto


# --------------------------------------------------------------------------- #
# Baixar e aplicar
# --------------------------------------------------------------------------- #
def _copiar_por_cima(origem, destino):
    """Copia o conteúdo de ``origem`` sobre ``destino`` (mescla, não apaga)."""
    for nome in os.listdir(origem):
        if nome in PRESERVAR:
            continue
        src = os.path.join(origem, nome)
        dst = os.path.join(destino, nome)
        if os.path.isdir(src):
            os.makedirs(dst, exist_ok=True)
            _copiar_por_cima(src, dst)
        else:
            shutil.copy2(src, dst)


def baixar_e_aplicar():
    """Baixa o ZIP da main e copia por cima da instalação.

    Retorna ``(ok, msg)``. Em erro, a instalação fica intacta (a cópia só
    começa depois do download e da extração terem dado certo).
    """
    tmp = tempfile.mkdtemp(prefix="coclick_update_")
    zip_path = os.path.join(tmp, "coclick.zip")
    try:
        req = urllib.request.Request(URL_ZIP, headers={"User-Agent": "CoClick"})
        with urllib.request.urlopen(
            req, timeout=_TIMEOUT, context=notifier._ssl_context()
        ) as resp, open(zip_path, "wb") as f:
            shutil.copyfileobj(resp, f)

        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)

        # O ZIP do GitHub tem uma única pasta raiz (ex.: "coclick-main").
        raizes = [
            os.path.join(tmp, n)
            for n in os.listdir(tmp)
            if os.path.isdir(os.path.join(tmp, n))
        ]
        if not raizes:
            return False, "ZIP baixado não tem a pasta esperada."
        raiz = raizes[0]

        _copiar_por_cima(raiz, _base_dir())

        remoto = sha_remoto()
        if remoto:
            salvar_sha(remoto)
        return True, "Atualização aplicada."
    except Exception as exc:
        return False, f"Falha ao atualizar: {exc}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def reiniciar_app():
    """Sobe uma instância nova (já com o código atualizado)."""
    main_py = os.path.join(_base_dir(), "main.py")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(
        [sys.executable, main_py], cwd=_base_dir(), creationflags=flags
    )
