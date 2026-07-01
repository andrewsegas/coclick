# 🖱️ CoClick — Bot de farm para Clash of Clans

**CoClick** automatiza os ataques repetitivos de farm no **Clash of Clans**.
Ele lê os recursos da vila na tela com OCR (Tesseract), decide se vale a pena
atacar de acordo com os limites que você definir, e executa o ataque sozinho —
em loop.

Agora com **interface gráfica** (painel para iniciar/parar e acompanhar as
estatísticas) e distribuído como um **programa pronto**: seus amigos só baixam,
extraem e abrem. Sem instalar Python, sem instalar Tesseract, sem mexer no PATH.

---

## ▶️ Para usar (quem recebeu o CoClick.zip)

1. Baixe o **CoClick.zip**.
2. Clique com o botão direito → **Extrair tudo**.
3. Abra a pasta `CoClick` e dê dois cliques em **`CoClick.exe`**.
   - Se o Windows mostrar um aviso azul do SmartScreen: clique em
     **Mais informações → Executar assim mesmo** (o programa não tem assinatura
     digital, é normal).
4. Na janela do CoClick:
   - No painel **Setup**, clique em **Capture** de cada posição. Para as
     posições de mouse, passe o cursor em cima do botão do jogo e espere a
     contagem (`3… 2… 1…`). Para a **área de leitura (OCR)**, arraste um
     retângulo por cima dos números de recursos.
   - Ajuste **ouro / elixir / elixir negro** mínimos e a **estratégia (star)**.
   - Clique em **Salvar**.
5. Clique em **▶ Start**. Acompanhe o status, as estatísticas e o log ao vivo.
   Clique em **■ Stop** para parar (ele termina o ataque atual antes de parar).

As configurações ficam salvas no `config.ini`, ao lado do `CoClick.exe`.

### Estratégia (`star`)

| Valor | Comportamento                                                        |
| ----- | ------------------------------------------------------------------- |
| `1`   | Ataca para destruir o máximo — **mantém/ganha troféus**.            |
| `2`   | Foco em recursos, com alguns ataques curtos (perde troféu às vezes). |
| `3`   | Sempre ataques curtos — **prioriza perder troféus** (baixar ranking).|

---

## 🛠️ Para gerar o executável (quem desenvolve)

Requisitos: **Python** instalado (com PATH) e **Windows**.

```powershell
# rodar direto do código-fonte
pip install -r requirements.txt
python main.py
```

Para gerar o `CoClick.zip` que você distribui:

1. **(Opcional, mas recomendado) empacotar o Tesseract junto** — assim quem
   receber não precisa instalar nada. Veja `vendor\tesseract\README.txt` e
   copie o Tesseract para essa pasta. Se você pular esta etapa, o `.exe`
   precisará de um Tesseract instalado no sistema.

2. Rode o build:

   ```powershell
   .\build.ps1
   ```

   Isso instala o PyInstaller, empacota tudo (onedir) usando o `build.spec` e
   gera **`dist\CoClick.zip`** — é esse arquivo que você envia para os amigos.

---

## 📂 Estrutura do projeto

| Arquivo             | Função                                                        |
| ------------------- | ------------------------------------------------------------- |
| `main.py`           | Ponto de entrada (abre a interface).                          |
| `gui.py`            | Interface gráfica: painel + setup.                            |
| `bot_engine.py`     | Motor do bot (loop de farm, OCR, ataque) + leitura/escrita do `config.ini`. |
| `square.py`         | Overlay para selecionar a área de leitura (OCR).              |
| `config.ini`        | Posições da tela e configurações de ataque.                  |
| `build.spec` / `build.ps1` | Empacotamento com PyInstaller.                        |
| `vendor/tesseract/` | Onde o Tesseract é colocado para ser empacotado.             |
