# 🖱️ CoClick - Automação para Clash of Clans

**CoClick** é uma ferramenta automatizada feita em Python que auxilia em interações repetitivas no jogo **Clash of Clans**, utilizando OCR (reconhecimento óptico de caracteres), cliques programados e detecção de áreas na tela.

---

## 🚀 Funcionalidades

- 📌 **Captura de tela com OCR** usando Tesseract para extrair textos da tela do jogo.
- 🎯 **Clique automático** em posições pré-definidas do mapa

O CoClick permite que você mapeie áreas específicas do jogo Clash of Clans para realizar ações automáticas com base nas **posições do mouse**. Durante a execução, você pode registrar essas posições pressionando uma tecla numérica de `0` a `9`. Cada tecla representa uma ação específica.

#### 📌 Teclas de mapeamento:

| Tecla | Ação                                                                                                         |
| ----- | ------------------------------------------------------------------------------------------------------------ |
| `0`   | Seleciona **área de leitura** dos recursos: **Elixir**, **Gold** e **Elixir Negro**                          |
| `9`   | Define a posição do **botão de pesquisa** da próxima vila para atacar                                        |
| `8`   | Define o local onde o ataque será **iniciado** *(com o layout totalmente para cima e para a esquerda)* |
| `7`   | Define o local onde o ataque será **finalizado** *(Precisa ser em linha horizontal com o início)*            |
| `6`   | Define a posição do botão **"Terminar ataque"**                                                              |
| `5`   | Define o botão **"OK"** (após o término do ataque)                                                           |
| `4`   | Define o botão **"Voltar"**                                                                                  |
| `3`   | Define o botão **"Atacar"**                                                                                  |
| `2`   | Define o botão **"Procurar vila"**                                                                           |
| `1`   | Define o botão **"Atacar (selecionar tropas)"**                                                              |

Essas posições são salvas em um arquivo `config.ini`, e reutilizadas em execuções futuras, permitindo total automação das batalhas.

- 🎲 **Delays aleatórios** para simular interações humanas.
- 📝 **Armazenamento e leitura de posições** do mouse via `config.ini`.
- 🔊 **Emissão de alertas sonoros** em ao encontrar vila para atacar.
---

## 🧰 Instalação
  Antes de qualquer coisa instale o python 
    - na insntalação escolha adicionar Path
    - Instale o **Tesseract-OCR**:
    - Baixe: https://github.com/UB-Mannheim/tesseract/wiki
    - adicione manualmente na variavel de ambiente path o endereço da pasta tesseract
ex: C:\Program Files\Tesseract-OCR

1. abra o prompt de comanndo repositório:
   ```bash
   cd [pasta do Coclick]
   pip install -r requirements.txt
   python coclick.py

Claro! Aqui está a seção atualizada **🧰 Instalação e Execução**, incluindo instruções sobre como rodar o programa e configurar o arquivo `.ini` para personalizar o comportamento do CoClick:

---

## 🧰 Instalação

1. **Clone o repositório:**

   ```bash
   git clone https://github.com/seuusuario/coclick.git
   cd coclick
   ```

2. **Instale as dependências:**

   Crie um ambiente virtual (opcional, mas recomendado):

   ```bash
   python -m venv venv
   venv\Scripts\activate   # No Windows
   source venv/bin/activate  # No Linux/Mac
   ```

   E instale os requisitos:

   ```bash
   pip install -r requirements.txt
   ```

---

## ▶️ Como executar

Execute o programa principal com:

```bash
python ANCR.py
```

---

## ⚙️ Arquivo de Configuração `.ini`

Você pode personalizar o comportamento dos ataques editando o arquivo `config.ini`, que será gerado após o mapeamento inicial das posições. Na seção `[Ataque]`, os seguintes parâmetros podem ser ajustados:

```ini
[Ataque]
gold = 500000
elixir = 500000
blackelixir = 0
star = 2
```

### Explicação dos parâmetros:

| Parâmetro     | Função                                                          |
| ------------- | --------------------------------------------------------------- |
| `gold`        | Valor mínimo de ouro necessário para iniciar um ataque.         |
| `elixir`      | Valor mínimo de elixir necessário para iniciar um ataque.       |
| `blackelixir` | Valor mínimo de elixir negro necessário para iniciar um ataque. |
| `star`        | Estratégia de ataque (detalhada abaixo).                        |

### Valores possíveis para `star`:

* `1` – Ataca **pra destruir o máximo** para obter recursos e **ganhar troféus**.
* `2` – Ataca focando em recursos, **mas faz alguns ataques curtos para perder troféu ocasionalmente**.
* `3` – Ataca **sempre com ataques curtos**, **priorizando perder troféus** (ideal para queda de ranking).
