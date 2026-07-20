"""Diagnóstico do OCR: mostra exatamente o que o bot enxerga e lê.

Com o jogo visível na tela, rode:  python debug_ocr.py

Ele recorta as duas áreas do config.ini do screenshot atual, salva os
recortes em debug_ocr/ (abra os PNGs para conferir se a área está certa)
e imprime o texto cru do Tesseract + os números que o bot entenderia.
"""

import os

import pytesseract
from PIL import Image, ImageGrab, ImageOps

import bot_engine

AREAS = [
    ("inimigo", "square1", "square2"),
    ("meus_recursos", "square3", "square4"),
]

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_ocr")


def main():
    try:
        print("Tesseract:", pytesseract.get_tesseract_version())
    except Exception as exc:
        print("ERRO: Tesseract não encontrado:", exc)
        return

    cfg = bot_engine.carregar_ini()
    pos = cfg.get("Posicoes", {})
    os.makedirs(OUT_DIR, exist_ok=True)

    image = ImageGrab.grab()
    image.save(os.path.join(OUT_DIR, "tela_inteira.png"))

    for nome, k1, k2 in AREAS:
        p1, p2 = pos.get(k1), pos.get(k2)
        print(f"\n=== Área '{nome}'  ({k1}={p1}  {k2}={p2}) ===")
        if not (isinstance(p1, tuple) and isinstance(p2, tuple)):
            print("  NÃO CONFIGURADA no config.ini — capture-a no assistente.")
            continue

        crop = image.crop((p1[0], p1[1], p2[0], p2[1]))
        png = os.path.join(OUT_DIR, f"{nome}.png")
        crop.save(png)
        print(f"  recorte salvo em: {png}  ({crop.width}x{crop.height} px)")

        # Same preprocessing the bot uses (see BotEngine._read_numbers).
        prepared = ImageOps.grayscale(crop).resize(
            (crop.width * 3, crop.height * 3), Image.LANCZOS
        ).point(lambda px: 255 if px > 170 else 0)
        prepared.save(os.path.join(OUT_DIR, f"{nome}_preprocessado.png"))
        raw = pytesseract.image_to_string(
            prepared, config="--psm 6 -c tessedit_char_whitelist=0123456789 "
        )
        print("  texto cru do Tesseract (pré-processado):")
        for line in raw.strip().split("\n"):
            print(f"    | {line!r}")

        valores = bot_engine.BotEngine._read_numbers(image, p1, p2)
        print(f"  o bot entenderia: ouro={valores[0]:,}  elixir={valores[1]:,}  negro={valores[2]:,}")

    print(f"\nConfira os PNGs em {OUT_DIR} — a área precisa pegar só os números,")
    print("um por linha (ouro em cima, elixir no meio, negro embaixo).")


if __name__ == "__main__":
    main()
