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
from llm_extract import (
    extraire_numero_dossier,
    extraire_tribunal,
    extraire_haia,
    extraire_mantouk,
    extraire_indemnisation,
)


def traiter_document(chemin_pdf: str) -> dict:
    print(f"[1/2] OCR (EasyOCR) : {chemin_pdf}")
    texte = pdf_vers_texte_easyocr(chemin_pdf)

    print("[2/2] Extraction LLM...")
    numero = extraire_numero_dossier(texte)
    tribunal = extraire_tribunal(texte)
    haia = extraire_haia(texte)
    mantouk = extraire_mantouk(texte)
    indemnisation = extraire_indemnisation(texte)

    return {
        "fichier": os.path.basename(chemin_pdf),
        "numero_dossier": numero,
        "tribunal": tribunal,
        "haia": haia,
        "mantouk": mantouk,
        "indemnisation": indemnisation,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python3 pipeline/main.py chemin/vers/document.pdf")
        sys.exit(1)

    chemin_pdf = sys.argv[1]
    resultat = traiter_document(chemin_pdf)

    print("\n" + "=" * 60)
    print("  RESULTAT DE L'EXTRACTION")
    print("=" * 60)
    print(f"\nرقم الملف : {resultat['numero_dossier']}")
    print(f"المحكمة : {resultat['tribunal']}")

    print(f"\nالهيئة")
    print(f"   - رئيسا ومقررا : {resultat['haia'].get('president_rapporteur', '') or '-'}")
    assesseurs = resultat['haia'].get("assesseurs", [])
    if assesseurs:
        for i, nom in enumerate(assesseurs, 1):
            print(f"   - عضو {i} : {nom}")
    else:
        print(f"   - عضو : -")
    print(f"   - كاتب الضبط : {resultat['haia'].get('greffier', '') or '-'}")
    print(f"   - المحامي العام : {resultat['haia'].get('procureur', '') or '-'}")

    print(f"\nقرار المحكمة النهائي")
    print(f"   {resultat['mantouk']}")

    print(f"\nالتعويض")
    print(f"   - المبلغ المطلوب : {resultat['indemnisation'].get('montant_reclame', '-')}")
    print(f"   - المبلغ الممنوح : {resultat['indemnisation'].get('montant_accorde', '-')}")
    print(f"   - الوضعية : {resultat['indemnisation'].get('statut', '-')}")
    print("\n" + "=" * 60 + "\n")
