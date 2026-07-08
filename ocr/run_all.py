"""
ocr/run_all.py

Lance pdf_vers_texte() sur TOUS les PDF de data/samples/,
et sauvegarde chaque resultat dans data/ocr_output/<nom>.txt
"""

import os
import glob
from extract_text import pdf_vers_texte

DOSSIER_SAMPLES = "data/samples"
DOSSIER_SORTIE = "data/ocr_output"


def main():
    os.makedirs(DOSSIER_SORTIE, exist_ok=True)

    pdfs = sorted(glob.glob(os.path.join(DOSSIER_SAMPLES, "*.pdf")))

    if not pdfs:
        print(f"Aucun PDF trouve dans {DOSSIER_SAMPLES}/")
        return

    print(f"{len(pdfs)} document(s) trouve(s). Traitement en cours...\n")

    for chemin_pdf in pdfs:
        nom = os.path.splitext(os.path.basename(chemin_pdf))[0]
        print(f"--- {nom} ---")

        try:
            texte = pdf_vers_texte(chemin_pdf)
        except Exception as e:
            print(f"[ERREUR sur {nom}: {e}]")
            continue

        chemin_sortie = os.path.join(DOSSIER_SORTIE, f"{nom}_tesseract.txt")
        with open(chemin_sortie, "w", encoding="utf-8") as f:
            f.write(texte)

        print(f"-> sauvegarde dans {chemin_sortie}")
        apercu = texte[:150].replace("\n", " ")
        print(f"   apercu : {apercu}...\n")

    print("Termine !")


if __name__ == "__main__":
    main()