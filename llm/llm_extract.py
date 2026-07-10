"""
Module d'extraction : numéro de dossier + الهيئة (bench) + المنطوق (dispositif final)
"""

import sys
import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"


# ---------------------------------------------------------------------------
# PARTIE 1 : Numéro de dossier (règle déterministe, INCHANGÉE)
# ---------------------------------------------------------------------------

def ressemble_a_une_date(candidat: str) -> bool:
    parties = candidat.split("/")
    if len(parties) != 3:
        return False
    _annee, mois, jour = parties
    if mois.isdigit() and jour.isdigit():
        if 1 <= int(mois) <= 12 and 1 <= int(jour) <= 31 and len(mois) <= 2 and len(jour) <= 2:
            return True
    return False


def trouver_candidats_regex(texte: str):
    motif = r"(?:19|20)\d{2}(?:/\d{1,6}){1,3}"
    candidats_bruts = re.findall(motif, texte)
    vus = set()
    resultat = []
    for c in candidats_bruts:
        if c not in vus and not ressemble_a_une_date(c):
            vus.add(c)
            resultat.append(c)
    return resultat


def demander_au_llm_en_dernier_recours(texte: str) -> str:
    prompt = f"""You are an expert assistant for Moroccan judicial documents written in Arabic.

No case file number could be automatically detected by pattern matching in this text.
Try to find the CASE FILE NUMBER (رقم الملف / ملف رقم / عدد) yourself, usually located
in the first few lines of the document.

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
    if not texte or not texte.strip():
        return "ERREUR: texte vide"
    candidats = trouver_candidats_regex(texte)
    if candidats:
        return candidats[0]
    return demander_au_llm_en_dernier_recours(texte)


# ---------------------------------------------------------------------------
# PARTIE 2 : الهيئة (bench) - fenêtre isolée + liste flexible de membres
# ---------------------------------------------------------------------------

ANCRES_HAIA = [
    "الهيئة الحاكمة",
    "مؤلفة من السادة",
    "مؤلفة من",
    "تتكون من السادة",
    "تتكون من",
]

TAILLE_FENETRE_HAIA = 900


def isoler_zone_haia(texte: str) -> str:
    for ancre in ANCRES_HAIA:
        idx = texte.find(ancre)
        if idx != -1:
            debut = idx
            fin = idx + len(ancre) + TAILLE_FENETRE_HAIA
            return texte[debut:fin]
    return texte[:800]


def extraire_haia(texte: str) -> dict:
    """Extrait la composition du collège de juges, en tolérant les mots
    cassés par des espaces parasites ou des lettres mal reconnues (OCR)."""

    fenetre = isoler_zone_haia(texte)

    prompt = f"""You are an expert assistant for Moroccan judicial documents written in Arabic.

The text below is a SHORT EXCERPT (already isolated) that introduces the panel
of judges (الهيئة) for ONE specific decision. It contains OCR errors: words can
be split by stray spaces in the middle (e.g. "بمسا عدة" instead of "بمساعدة"),
or have garbled/missing letters (e.g. "ىيدة" instead of "السيدة", "غا اشي"
instead of "غاشي"). MENTALLY RECONSTRUCT such broken words before extracting -
do not require them to be spelled perfectly to recognize them.

Extract ONLY the names found in THIS excerpt - do not invent names, and do not
include lawyers or parties.

Note: a Moroccan Cassation Court panel sitting "بغرفتين" (two chambers combined)
can have MANY assessor judges (up to 6+), not just 1-2. Extract ALL assessor
names you find, however many there are.

Roles to identify:
- "president_rapporteur": marked by "رئيسا" or "رئيسا ومقررا" (if 2 co-presidents,
  separate with " ; ")
- "assesseurs": a LIST of all judges marked by "عضوا" or "أعضاء" or listed after
  "والمستشارين السادة"
- "greffier": the court clerk. Look for "كاتب الضبط", "كاتبة الضبط", or a name
  following a (possibly broken/misspelled) form of "بمساعدة" (assisted by...).
  Reconstruct broken OCR spellings of this word before searching for it.
- "procureur": marked by "المحامي العام" or "النيابة العامة" or "الوكيل العام للملك"

If a role is not present in this excerpt, use "" (or [] for assesseurs).

Excerpt:
\"\"\"
{fenetre}
\"\"\"

Respond ONLY with this JSON:
{{
  "president_rapporteur": "",
  "assesseurs": [],
  "greffier": "",
  "procureur": ""
}}
"""

    try:
        reponse = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False, "format": "json"},
            timeout=120,
        )
        reponse.raise_for_status()
        contenu = reponse.json()["response"]
        return json.loads(contenu)
    except Exception as e:
        return {
            "president_rapporteur": f"ERREUR: {e}",
            "assesseurs": [],
            "greffier": "",
            "procureur": "",
        }


# ---------------------------------------------------------------------------
# PARTIE 3 : المنطوق (dispositif final) - INCHANGÉ
# ---------------------------------------------------------------------------

def extraire_mantouk(texte: str) -> str:
    prompt = f"""You are an expert assistant for Moroccan judicial documents written in Arabic.

The text below is raw OCR output and may contain spelling/character recognition errors.
Locate the FINAL DISPOSITIVE / RULING section (منطوق الحكم أو القرار), usually near
the end, after "لهذه الأسباب", starting with "حكمت المحكمة" or "قضت محكمة النقض" or
"قضت محكمة الاستئناف". Extract that section, correcting obvious OCR spelling
mistakes so it reads as proper Arabic, but do NOT paraphrase, summarize, or
change the legal meaning.

Full OCR text:
\"\"\"
{texte}
\"\"\"

Respond ONLY with this JSON:
{{"mantouk": "..."}}
"""
    try:
        reponse = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False, "format": "json"},
            timeout=180,
        )
        reponse.raise_for_status()
        contenu = reponse.json()["response"]
        resultat = json.loads(contenu)
        return resultat.get("mantouk", "NON TROUVE")
    except Exception as e:
        return f"ERREUR: {e}"


# ---------------------------------------------------------------------------
# POINT D'ENTRÉE
# ---------------------------------------------------------------------------

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
    haia = extraire_haia(texte)
    mantouk = extraire_mantouk(texte)

    print(f": رقم الملف {numero}")
    print(": الهيئة")
    print(f"  رئيسا ومقررا : {haia.get('president_rapporteur', '')}")
    assesseurs = haia.get("assesseurs", [])
    for i, nom in enumerate(assesseurs, 1):
        print(f"  عضو ({i}) : {nom}")
    print(f"  كاتب الضبط : {haia.get('greffier', '')}")
    print(f"  المحامي العام : {haia.get('procureur', '')}")
    print(f": قرار المحكمة النهائي {mantouk}")
