"""
Pipeline complet : PDF -> texte (EasyOCR) -> extraction (LLM)

Usage :
    python3 pipeline/main.py chemin/vers/document.pdf
"""

import sys
import os

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "ocr"))
sys.path.insert(0, os.path.join(RACINE, "llm"))

from run_all_easyocr import pdf_vers_texte_easyocr
from llm_extract import extraire_numero_dossier, extraire_haia, extraire_mantouk


def traiter_document(chemin_pdf: str) -> dict:
    print(f"[1/2] OCR (EasyOCR) : {chemin_pdf}")
    texte = pdf_vers_texte_easyocr(chemin_pdf)

    print("[2/2] Extraction LLM...")
    numero = extraire_numero_dossier(texte)
    haia = extraire_haia(texte)
    mantouk = extraire_mantouk(texte)

    return {
        "fichier": os.path.basename(chemin_pdf),
        "numero_dossier": numero,
        "haia": haia,
        "mantouk": mantouk,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python3 pipeline/main.py chemin/vers/document.pdf")
        sys.exit(1)

    chemin_pdf = sys.argv[1]
    resultat = traiter_document(chemin_pdf)

    print("\n=== RESULTAT ===")
    print(f": رقم الملف {resultat['numero_dossier']}")
    print(": الهيئة")
    print(f"  رئيسا ومقررا : {resultat['haia'].get('president_rapporteur', '')}")
    for i, nom in enumerate(resultat['haia'].get('assesseurs', []), 1):
        print(f"  عضو ({i}) : {nom}")
    print(f"  كاتب الضبط : {resultat['haia'].get('greffier', '')}")
    print(f"  المحامي العام : {resultat['haia'].get('procureur', '')}")
    print(f": قرار المحكمة النهائي {resultat['mantouk']}")
