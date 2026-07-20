# 🖱️ CoClick — Bot de farm para Clash of Clans

**CoClick** automatiza os ataques repetitivos de farm no **Clash of Clans**.
Ele lê os recursos da vila na tela com OCR (Tesseract), decide se vale a pena
atacar de acordo com os limites que você definir, e executa o ataque sozinho —
em loop. Tem interface gráfica para configurar, iniciar/parar e acompanhar as
estatísticas, e pode te avisar pelo **Discord** enquanto roda.

> Projeto para desenvolvedores: roda direto do código-fonte, sem instalador.

## ✅ Requisitos

1. **Windows** (o bot controla mouse/teclado com `pydirectinput`/`pyautogui`).
2. **Python 3.10+** — instalador oficial de [python.org](https://www.python.org/downloads/)
   (já inclui o tkinter, usado pela interface).
3. **Tesseract OCR** — instale o
   [Tesseract para Windows (UB Mannheim)](https://github.com/UB-Mannheim/tesseract/wiki)
   e garanta que o comando `tesseract` funcione no terminal (marque a opção de
   adicionar ao PATH no instalador, ou adicione `C:\Program Files\Tesseract-OCR`
   ao PATH manualmente).
4. Dependências Python:

   ```powershell
   pip install -r requirements.txt
   ```

## ▶️ Como rodar

```powershell
python main.py
```

Na janela do CoClick:

1. Com o jogo aberto, clique em **⚙ Configure all positions (wizard)**. Uma
   faixa no topo da tela vai pedindo cada posição em sequência, e **o jogo
   continua livre** — você pode navegar pelos menus normalmente para chegar em
   cada botão. Posicione o **mouse em cima do botão** e pressione **Espaço**
   para capturar. Para as duas áreas de OCR são dois Espaços: canto superior
   esquerdo e canto inferior direito dos números — a primeira área é o saque
   do inimigo, a segunda são **os seus próprios recursos** (usada pela parada
   automática). **Botão direito pula** um passo, `Esc` **cancela** o restante
   (o que já foi capturado fica salvo). Errou só um ponto? Escolha-o na lista
   e clique **Recapture**.
2. Ajuste **ouro / elixir / elixir negro** mínimos e a **estratégia (star)**.
3. Clique em **💾 Save settings**.
4. Clique em **▶ Start**. Acompanhe o status, as estatísticas e o log ao vivo.
   **■ Stop** para parar (ele termina o ataque atual antes).

### 🛑 Parada automática (armazéns cheios)

O maior desperdício é deixar o bot atacando com os armazéns já cheios. Na
seção **Auto-stop (storages full)**:

1. Marque **Stop when my storages are full**.
2. Defina os limites de **ouro** e **elixir** (por exemplo, a capacidade dos
   seus armazéns). Vazio/0 = ignorar aquele recurso.
3. Escolha o modo: **all limits reached** (para quando ouro E elixir
   atingirem os limites) ou **any limit reached** (para no primeiro que
   encher).

O bot lê os **seus** recursos na área "My resources" (OCR) a cada ciclo e,
para não parar por um número mal lido, só para após **duas leituras seguidas**
acusando cheio. Ao parar, avisa no Discord com o motivo.

Tudo fica salvo no `config.ini` (criado automaticamente na primeira execução,
ao lado do `main.py`). Esse arquivo **não é versionado**: contém posições da
sua tela e o seu webhook do Discord.

### Estratégia (`star`)

| Valor | Comportamento                                                        |
| ----- | ------------------------------------------------------------------- |
| `1`   | Ataca para destruir o máximo — **mantém/ganha troféus**.            |
| `2`   | Foco em recursos, com alguns ataques curtos (perde troféu às vezes). |
| `3`   | Sempre ataques curtos — **prioriza perder troféus** (baixar ranking).|

## 🔔 Notificações no Discord (opcional)

Para ser avisado no celular enquanto o bot roda sozinho:

1. No seu Discord: canal de texto → ⚙️ **Editar canal → Integrações →
   Webhooks → Novo webhook → Copiar URL**.
2. No CoClick, painel **Discord notifications**: cole a URL em **Webhook URL**
   e clique em **Test** — deve chegar "✅ CoClick conectado!" no canal.
3. **💾 Save settings**.

O bot manda **uma única mensagem, quando parar**, com o motivo — armazéns
cheios, tempo limite, parado pelo usuário ou 🛑 erro — e o resumo da sessão
(ataques, tempo, saque total).

> ⚠️ A URL do webhook é um segredo — quem tiver ela consegue postar no seu
> canal. Ela fica só no `config.ini`, que está no `.gitignore`.

## 📂 Estrutura do projeto

| Arquivo         | Função                                                              |
| --------------- | ------------------------------------------------------------------- |
| `main.py`       | Ponto de entrada (abre a interface).                                |
| `gui.py`        | Interface gráfica: dashboard + setup.                               |
| `bot_engine.py` | Motor do bot (loop de farm, OCR, ataque) + leitura/escrita do `config.ini`. |
| `wizard.py`     | Assistente de setup: captura posições/áreas com a tecla Espaço.     |
| `notifier.py`   | Envio de notificações para o webhook do Discord.                    |
| `debug_ocr.py`  | Diagnóstico do OCR (veja abaixo).                                   |
| `config.ini`    | Gerado no primeiro uso: posições da tela, limites e webhook.        |

## 🔍 O bot não está lendo os números?

Com o jogo visível na tela (de preferência na tela de procurar vila), rode:

```powershell
python debug_ocr.py
```

Ele recorta as duas áreas de OCR do seu `config.ini`, salva os recortes em
`debug_ocr\` (`inimigo.png`, `meus_recursos.png` e as versões
`*_preprocessado.png`, que é exatamente o que o Tesseract recebe) e imprime o
que foi lido de cada área. Confira os PNGs:

- O retângulo precisa pegar **os números inteiros**, um por linha (ouro em
  cima, elixir no meio, negro embaixo), sem cortar dígitos nas bordas.
- Se a área estiver errada, recapture só ela: lista do painel → **Recapturar**.
- As posições são absolutas na tela — se a janela do jogo mudar de lugar ou
  de tamanho, rode o assistente de novo.
