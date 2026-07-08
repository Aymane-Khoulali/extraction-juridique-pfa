"""
ocr/extract_text_easyocr.py

Version EasyOCR de pdf_vers_texte() - meme interface que extract_text.py,
pour permettre une comparaison directe entre les deux moteurs.
"""

import numpy as np
from pdf2image import convert_from_path
import easyocr

_reader = easyocr.Reader(["ar"], gpu=False)


def pdf_vers_texte(chemin_pdf: str) -> str:
    """
    Prend le chemin d'un PDF et retourne le texte brut extrait (arabe),
    en utilisant EasyOCR au lieu de Tesseract.
    Meme contrat que extract_text.py : retourne toujours une simple chaine.
    """
    pages = convert_from_path(chemin_pdf, dpi=200)

    texte_complet = []
    for page in pages:
        lignes = _reader.readtext(np.array(page), detail=0, paragraph=True)
        texte_complet.append("\n".join(lignes))

    return "\n".join(texte_complet)


if __name__ == "__main__":
    import sys
    chemin = sys.argv[1] if len(sys.argv) > 1 else "data/samples/doc1.pdf"
    resultat = pdf_vers_texte(chemin)
    print(resultat)