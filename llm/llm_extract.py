"""
Module d'extraction du numéro de dossier à partir d'un texte OCR brut (arabe)

Usage :
    python3 llm_extract.py fichier_texte.txt
    cat fichier_texte.txt | python3 llm_extract.py

Approche : détection par regex + règle déterministe (premier candidat valide).
Le LLM n'est utilisé qu'en dernier recours, si aucun candidat n'est trouvé par regex.
"""

import sys
import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"


def ressemble_a_une_date(candidat: str) -> bool:
    """Détecte si un candidat ressemble à une date (AAAA/M/J) plutôt qu'à un numéro de dossier."""
    parties = candidat.split("/")
    if len(parties) != 3:
        return False
    _annee, mois, jour = parties
    if mois.isdigit() and jour.isdigit():
        if 1 <= int(mois) <= 12 and 1 <= int(jour) <= 31 and len(mois) <= 2 and len(jour) <= 2:
            return True
    return False


def trouver_candidats_regex(texte: str):
    """Trouve tous les motifs plausibles de numéro de dossier dans un texte OCR arabe.

    Règles apprises sur des documents réels (jugements, arrêts d'appel, Cassation) :
    - Doit commencer par un vrai millésime (19xx ou 20xx), pour exclure les numéros
      de loi (ex: "القانون رقم 15/02") qui ont un format similaire mais commencent
      par un petit nombre.
    - Exclu si le motif ressemble à une date (jour/mois valides).
    """
    motif = r"(?:19|20)\d{2}(?:/\d{1,6}){1,3}"
    candidats_bruts = re.findall(motif, texte)

    vus = set()
    resultat = []
    for c in candidats_bruts:
        if c not in vus and not ressemble_a_une_date(c):
            vus.add(c)
            resultat.append(c)
    return resultat  # dans l'ordre d'apparition dans le texte


def demander_au_llm_en_dernier_recours(texte: str) -> str:
    """Utilisé UNIQUEMENT si la regex ne trouve aucun candidat du tout."""
    prompt = f"""You are an expert assistant for Moroccan judicial documents written in Arabic.

No case file number could be automatically detected by pattern matching in this text.
Try to find the CASE FILE NUMBER (رقم الملف / ملف رقم / عدد) yourself, usually located
in the first few lines of the document, right after the judgment/ruling number and date.

Text:
\"\"\"
{texte[:3000]}
\"\"\"

Respond ONLY with this JSON:
{{"numero_dossier": "..."}}
"""
    try:
        reponse = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False, "format": "json"},
            timeout=120,
        )
        reponse.raise_for_status()
        contenu = reponse.json()["response"]
        resultat = json.loads(contenu)
        return resultat.get("numero_dossier", "NON TROUVE")
    except Exception:
        return "NON TROUVE"


def extraire_numero_dossier(texte: str) -> str:
    """Prend un texte OCR brut arabe et retourne le numéro de dossier.

    RÈGLE PRINCIPALE (déterministe, validée sur plusieurs documents réels) :
    le PREMIER candidat valide détecté par regex, dans l'ordre d'apparition du
    texte, EST le numéro de dossier. Aucun appel au LLM ici : c'est fiable et
    reproductible à 100%, contrairement à un LLM qui peut se laisser distraire
    par un numéro plus loin dans le texte (référence à une affaire antérieure).

    Le LLM n'intervient qu'en tout dernier recours, si la regex ne trouve
    absolument aucun candidat.
    """
    if not texte or not texte.strip():
        return "ERREUR: texte vide"

    candidats = trouver_candidats_regex(texte)

    if candidats:
        return candidats[0]  # <-- règle déterministe, pas de LLM impliqué ici

    return demander_au_llm_en_dernier_recours(texte)


def lire_texte_entree() -> str:
    if len(sys.argv) > 1:
        chemin = sys.argv[1]
        with open(chemin, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return sys.stdin.read()


if __name__ == "__main__":
    texte = lire_texte_entree()
    numero = extraire_numero_dossier(texte)
    print(f"Numéro de dossier : {numero}")
