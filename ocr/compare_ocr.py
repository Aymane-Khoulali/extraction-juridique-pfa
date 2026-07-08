"""
ocr/compare_ocr.py

Compare Tesseract, PaddleOCR et EasyOCR sur les memes PDF.
Sauvegarde les resultats de chaque moteur separement dans data/ocr_output/
pour permettre une comparaison manuelle facile.
"""

import os
import sys
from pdf2image import convert_from_path
import pytesseract


def ocr_tesseract(image):
    return pytesseract.image_to_string(image, lang="ara")


def ocr_paddle(image):
    from paddleocr import PaddleOCR
    import numpy as np

    if not hasattr(ocr_paddle, "_engine"):
        ocr_paddle._engine = PaddleOCR(use_textline_orientation=True, lang="ar")

    result = ocr_paddle._engine.predict(input=np.array(image))
    lignes = []
    for res in result:
        lignes.extend(res["rec_texts"])
    return "\n".join(lignes)


def ocr_easyocr(image):
    import easyocr
    import numpy as np

    if not hasattr(ocr_easyocr, "_engine"):
        ocr_easyocr._engine = easyocr.Reader(["ar"], gpu=False)

    result = ocr_easyocr._engine.readtext(np.array(image), detail=0, paragraph=True)
    return "\n".join(result)


def comparer_pdf(chemin_pdf):
    nom = os.path.splitext(os.path.basename(chemin_pdf))[0]
    pages = convert_from_path(chemin_pdf, dpi=300)

    moteurs = {
        "tesseract": ocr_tesseract,
        "paddleocr": ocr_paddle,
        "easyocr": ocr_easyocr,
    }

    for nom_moteur, fonction in moteurs.items():
        print(f"--- {nom_moteur} sur {nom} ---")
        texte_pages = []
        for i, page in enumerate(pages):
            try:
                texte = fonction(page)
            except Exception as e:
                texte = f"[ERREUR {nom_moteur} page {i+1}: {e}]"
            texte_pages.append(texte)

        texte_final = "\n".join(texte_pages)

        os.makedirs("data/ocr_output", exist_ok=True)
        chemin_sortie = f"data/ocr_output/{nom}_{nom_moteur}.txt"
        with open(chemin_sortie, "w", encoding="utf-8") as f:
            f.write(texte_final)

        print(f"-> sauvegarde dans {chemin_sortie}")
        print(texte_final[:300])
        print()


if __name__ == "__main__":
    chemin = sys.argv[1] if len(sys.argv) > 1 else "data/samples/cas1.pdf"
    comparer_pdf(chemin)