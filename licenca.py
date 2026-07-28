"""Controle de licença do CoClick (Google Sheets + Apps Script).

Fluxo: na primeira execução o usuário digita a chave, que é validada online
(GET no Web App do Apps Script) e vinculada a este PC (HWID). Um comprovante
assinado (HMAC) fica na seção ``[Licenca]`` do ``config.ini`` e permite usar
o bot por até 3 dias sem internet; depois disso é preciso revalidar online.

Nota honesta: o projeto é distribuído em código-fonte, então isto é
dissuasão e gestão (revogar/expirar/travar por PC pela planilha), não DRM —
quem editar o código consegue remover a checagem.

Stdlib-only; importa apenas :mod:`notifier` para reutilizar o contexto SSL
que tolera antivírus/proxy interceptando HTTPS.
"""

import configparser
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
import uuid

import notifier

# URL /exec do Web App publicado no Apps Script (ver servidor_licencas/LEIA-ME.md).
URL_VALIDACAO = "https://script.google.com/macros/s/AKfycbwK4DylvjdBTkelxkRattziEXuN59F0PJRlpD06I3hto9d0xF8EOQx2_sYLyR81ilnu/exec"

TOLERANCIA_OFFLINE = 3 * 24 * 3600  # 3 dias sem revalidar online
_TIMEOUT = 10  # segundos
_SEGREDO = b"coclick-2026-mQ7vXk4nR9pZ2wLh8sYcJ3fB6tGdN5aEuW"

MENSAGENS = {
    "chave_invalida": "Chave inválida. Confira se digitou exatamente como recebeu.",
    "revogada": "Esta chave foi desativada. Fale com o Andrews.",
    "expirada": "Esta chave expirou. Fale com o Andrews para renovar.",
    "outro_pc": "Esta chave já está em uso em outro computador.",
    "sem_conexao": (
        "Não foi possível conectar ao servidor de licenças.\n"
        "Verifique sua internet e tente de novo."
    ),
    "erro_interno": "Erro no servidor de licenças. Tente novamente em instantes.",
    "parametros": "Erro interno ao montar a validação.",
}


def _config_path():
    """Mesma regra de ``bot_engine.config_path()`` (sem importar o engine)."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")


def hwid():
    """Identificador estável desta máquina (MachineGuid; fallback: MAC)."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        )
        bruto, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
    except OSError:
        bruto = f"mac:{uuid.getnode():012x}"
    return hashlib.sha256(f"coclick|{bruto}".encode()).hexdigest()[:32]


def _assinar(chave, maquina, validado_em, expira_em):
    msg = f"{chave}|{maquina}|{validado_em}|{expira_em}".encode()
    return hmac.new(_SEGREDO, msg, hashlib.sha256).hexdigest()


# --------------------------------------------------------------------------- #
# Validação online
# --------------------------------------------------------------------------- #
def validar_online(chave):
    """Consulta o servidor. Retorna ``(motivo, expira_em)``; motivo ``""`` = OK."""
    params = urllib.parse.urlencode({"chave": chave, "hwid": hwid()})
    req = urllib.request.Request(
        f"{URL_VALIDACAO}?{params}", headers={"User-Agent": "CoClick"}
    )
    try:
        with urllib.request.urlopen(
            req, timeout=_TIMEOUT, context=notifier._ssl_context()
        ) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except Exception:
        # Rede fora, DNS, timeout ou resposta não-JSON (ex.: página de login).
        return "sem_conexao", ""
    if dados.get("ok"):
        return "", str(dados.get("expira_em", "") or "")
    return dados.get("motivo", "erro_interno"), str(dados.get("expira_em", "") or "")


# --------------------------------------------------------------------------- #
# Cache local assinado ([Licenca] no config.ini)
# --------------------------------------------------------------------------- #
def salvar_cache(chave, expira_em):
    arquivo = _config_path()
    config = configparser.ConfigParser()
    if os.path.exists(arquivo):
        config.read(arquivo)

    validado_em = int(time.time())
    config["Licenca"] = {
        "chave": chave,
        "validado_em": str(validado_em),
        "expira_em": expira_em,
        "assinatura": _assinar(chave, hwid(), validado_em, expira_em),
    }
    with open(arquivo, "w") as configfile:
        config.write(configfile)


def limpar_cache():
    arquivo = _config_path()
    config = configparser.ConfigParser()
    if os.path.exists(arquivo):
        config.read(arquivo)
    if config.remove_section("Licenca"):
        with open(arquivo, "w") as configfile:
            config.write(configfile)


def _expirada_localmente(expira_em, agora):
    """True se ``expira_em`` (``aaaa-mm-dd``, fim do dia) já passou."""
    if not expira_em:
        return False
    try:
        fim = time.mktime(time.strptime(expira_em, "%Y-%m-%d")) + 24 * 3600
    except ValueError:
        return True  # data ilegível no cache = cache inválido
    return agora >= fim


def verificar_cache():
    """Retorna ``(estado, chave)``: ``"valido"`` | ``"precisa_validar"`` | ``"sem_chave"``."""
    config = configparser.ConfigParser()
    arquivo = _config_path()
    if os.path.exists(arquivo):
        config.read(arquivo)
    if "Licenca" not in config:
        return "sem_chave", ""

    sec = config["Licenca"]
    chave = sec.get("chave", "").strip()
    expira_em = sec.get("expira_em", "").strip()
    assinatura = sec.get("assinatura", "").strip()
    if not chave:
        return "sem_chave", ""

    try:
        validado_em = int(sec.get("validado_em", ""))
    except ValueError:
        return "precisa_validar", chave

    esperada = _assinar(chave, hwid(), validado_em, expira_em)
    if not hmac.compare_digest(assinatura, esperada):
        return "precisa_validar", chave

    agora = time.time()
    if validado_em > agora + 300:  # relógio manipulado/atrasado à força
        return "precisa_validar", chave
    if agora > validado_em + TOLERANCIA_OFFLINE:
        return "precisa_validar", chave
    if _expirada_localmente(expira_em, agora):
        return "precisa_validar", chave
    return "valido", chave


# --------------------------------------------------------------------------- #
# API para a GUI
# --------------------------------------------------------------------------- #
def ativar(chave):
    """Valida online e, se OK, salva o cache. Retorna motivo (``""`` = sucesso)."""
    chave = chave.strip().upper()
    motivo, expira_em = validar_online(chave)
    if motivo == "":
        salvar_cache(chave, expira_em)
    return motivo


def revalidar_silenciosa():
    """Revalida a chave do cache em segundo plano (thread daemon da GUI).

    Sucesso renova a janela offline; negativa definitiva (revogada, expirada,
    outro PC, chave removida) limpa o cache — bloqueia na próxima abertura.
    Falha de rede/servidor não muda nada: a tolerância offline decide.
    """
    config = configparser.ConfigParser()
    if os.path.exists(_config_path()):
        config.read(_config_path())
    chave = config.get("Licenca", "chave", fallback="").strip()
    if not chave:
        return

    motivo, expira_em = validar_online(chave)
    if motivo == "":
        salvar_cache(chave, expira_em)
    elif motivo in ("chave_invalida", "revogada", "expirada", "outro_pc"):
        limpar_cache()
