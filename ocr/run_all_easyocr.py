"""
ocr/run_all_easyocr.py

Lance EasyOCR sur les PDF de data/samples/,
et sauvegarde chaque resultat dans data/ocr_output/easyOCR_output/<nom>_easyocr.txt

Usage:
    python3 ocr/run_all_easyocr.py                       -> traite tous les PDF
    python3 ocr/run_all_easyocr.py data/samples/doc1.pdf -> traite un seul PDF
"""

import os
import sys
import glob
import numpy as np
from pdf2image import convert_from_path
import easyocr

DOSSIER_SAMPLES = "data/samples"
DOSSIER_SORTIE = "data/ocr_output/easyOCR_output"

_reader = easyocr.Reader(["ar"], gpu=False)


def pdf_vers_texte_easyocr(chemin_pdf):
    pages = convert_from_path(chemin_pdf, dpi=200)

    texte_pages = []
    for i, page in enumerate(pages):
        print(f"   -> traitement page {i+1}/{len(pages)}...")
        lignes = _reader.readtext(np.array(page), detail=0, paragraph=True)
        texte_pages.append("\n".join(lignes))

    return "\n".join(texte_pages)


def traiter_un_fichier(chemin_pdf):
    nom = os.path.splitext(os.path.basename(chemin_pdf))[0]
    os.makedirs(DOSSIER_SORTIE, exist_ok=True)

    print(f"--- {nom} ---")
    texte = pdf_vers_texte_easyocr(chemin_pdf)

    chemin_sortie = os.path.join(DOSSIER_SORTIE, f"{nom}_easyocr.txt")
    with open(chemin_sortie, "w", encoding="utf-8") as f:
        f.write(texte)

    print(f"-> sauvegarde dans {chemin_sortie}")
    print(texte)


def main():
    os.makedirs(DOSSIER_SORTIE, exist_ok=True)
    pdfs = sorted(glob.glob(os.path.join(DOSSIER_SAMPLES, "*.pdf")))

    if not pdfs:
        print(f"Aucun PDF trouve dans {DOSSIER_SAMPLES}/")
        return

    print(f"{len(pdfs)} document(s) trouve(s). Traitement en cours (EasyOCR)...\n")

    for chemin_pdf in pdfs:
        try:
            traiter_un_fichier(chemin_pdf)
            print()
        except Exception as e:
            nom = os.path.splitext(os.path.basename(chemin_pdf))[0]
            print(f"[ERREUR sur {nom}: {e}]\n")

    print("Termine !")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        traiter_un_fichier(sys.argv[1])
    else:
        main()