"""
Extraction du numéro de dossier à partir de documents judiciaires marocains (arabe)
Pipeline : PDF -> images -> OCR (Tesseract, arabe) -> LLM local (Ollama / Qwen2.5) -> JSON
"""

import sys
import json
import re
import requests
from pdf2image import convert_from_path
import pytesseract

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"
MAX_PAGES_HEAD = 2
MAX_PAGES_TAIL = 1


def pdf_vers_texte(chemin_pdf: str) -> str:
    images = convert_from_path(chemin_pdf, dpi=300)
    n = len(images)
    if n <= MAX_PAGES_HEAD + MAX_PAGES_TAIL:
        pages_a_traiter = list(enumerate(images))
    else:
        tete = list(enumerate(images))[:MAX_PAGES_HEAD]
        queue = list(enumerate(images))[-MAX_PAGES_TAIL:]
        pages_a_traiter = tete + queue

    textes = []
    for i, img in pages_a_traiter:
        texte_page = pytesseract.image_to_string(img, lang="ara")
        textes.append(f"--- PAGE {i + 1} ---\n{texte_page}")

    return "\n\n".join(textes)


def trouver_candidats_regex(texte: str):
    motif = r"\d{2,4}(?:/\d{2,6}){1,3}"
    candidats = re.findall(motif, texte)
    vus = set()
    resultat = []
    for c in candidats:
        if c not in vus:
            vus.add(c)
            resultat.append(c)
    return resultat


def demander_au_llm(texte: str, candidats: list) -> dict:
    candidats_str = ", ".join(candidats) if candidats else "(aucun candidat détecté)"

    prompt = f"""Tu es un assistant expert en documents judiciaires marocains rédigés en arabe.

Ta tâche : identifier le NUMERO DE DOSSIER (رقم الملف / ملف رقم) dans le texte ci-dessous.

ATTENTION, ne pas confondre avec le numéro du jugement/arrêt (رقم الحكم / قرار رقم).

Candidats potentiels détectés automatiquement :
{candidats_str}

Texte OCRisé :
\"\"\"
{texte[:4000]}
\"\"\"

Réponds UNIQUEMENT avec un JSON valide :
{{"numero_dossier": "...", "type_document": "jugement ou arret ou autre", "confiance": "haute ou moyenne ou basse"}}
"""

    reponse = requests.post(
        OLLAMA_URL,
        json={"model": MODEL_NAME, "prompt": prompt, "stream": False, "format": "json"},
        timeout=120,
    )
    reponse.raise_for_status()
    contenu = reponse.json()["response"]

    try:
        resultat = json.loads(contenu)
    except json.JSONDecodeError:
        resultat = {"erreur": "JSON invalide", "brut": contenu}

    return resultat


def main():
    if len(sys.argv) < 2:
        print("Usage : python3 extract_numero_dossier.py chemin/vers/document.pdf")
        sys.exit(1)

    chemin_pdf = sys.argv[1]
    texte = pdf_vers_texte(chemin_pdf)
    candidats = trouver_candidats_regex(texte)
    resultat = demander_au_llm(texte, candidats)

    print(json.dumps(resultat, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
