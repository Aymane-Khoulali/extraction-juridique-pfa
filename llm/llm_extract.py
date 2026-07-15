"""
Module d'extraction : numéro de dossier + tribunal + الهيئة (bench) + المنطوق (dispositif final)
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
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
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
# PARTIE 2 : Nom du tribunal - en-tête d'abord, puis texte complet en repli
# ---------------------------------------------------------------------------

TAILLE_FENETRE_TRIBUNAL = 600


def isoler_zone_tribunal(texte: str) -> str:
    return texte[:TAILLE_FENETRE_TRIBUNAL]


def _demander_tribunal(contenu_texte: str) -> str:
    prompt = f"""You are an expert assistant for Moroccan judicial documents written in Arabic.

The text below is (an excerpt of) a Moroccan court decision. It may contain OCR
errors - mentally correct obvious spelling mistakes before extracting.

Extract the FULL NAME of the court/tribunal that issued this decision (اسم
المحكمة), including its city if mentioned. Common formats include:
- "المحكمة التجارية ب<ville>" (Commercial Court of <city>)
- "المحكمة الابتدائية ب<ville>" (Court of First Instance of <city>)
- "محكمة الاستئناف التجارية ب<ville>" (Commercial Court of Appeal of <city>)
- "محكمة الاستئناف الإدارية ب<ville>" (Administrative Court of Appeal of <city>)
- "محكمة النقض" (Court of Cassation - no city, it is the supreme court)

The court name may appear anywhere in the text - in the header (often repeated
in a box/table), or later in the body (e.g. in the closing formula near the
ruling, such as "فإن محكمة الاستئناف التجارية بفاس..."). Search the WHOLE text
if needed. Extract it once, in its clean, complete, correct form. Do not
include the case number, decision number, or date - only the court's name.
If truly not found anywhere, return an empty string.

Text:
\"\"\"
{contenu_texte}
\"\"\"

Respond ONLY with this JSON:
{{"tribunal": "..."}}
"""
    try:
        reponse = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
            timeout=120,
        )
        reponse.raise_for_status()
        contenu = reponse.json()["response"]
        resultat = json.loads(contenu)
        return resultat.get("tribunal", "")
    except Exception:
        return ""


def extraire_tribunal(texte: str) -> str:
    resultat = _demander_tribunal(isoler_zone_tribunal(texte))
    if resultat and resultat.strip():
        return resultat
    resultat = _demander_tribunal(texte[:4000])
    return resultat if resultat and resultat.strip() else "NON TROUVE"


# ---------------------------------------------------------------------------
# PARTIE 3 : الهيئة (bench) - fenêtre isolée + liste flexible de membres
# ---------------------------------------------------------------------------

ANCRES_HAIA = [
    "الهيئة الحاكمة",
    "مؤلفة من السادة",
    "مؤلفة من",
    "تتكون من السادة",
    "تتكون من",
    "متركبة من",
]

TAILLE_FENETRE_HAIA = 900

MOTS_ROLES = [
    "رئيسا ومقررا",
    "رئيسا",
    "ومقررا",
    "عضوا",
    "أعضاء",
    "مستشارا",
    "مستشار",
    "كاتب الضبط",
    "كاتبة الضبط",
    "بمساعدة",
    "المحامي العام",
    "محامي العام",
    "النيابة العامة",
    "الوكيل العام",
    "المفوض الملكي",
]

MOTS_PARASITES = [
    "بمساعدة",
    "بال",
    " ب ",
    "المملكة المغربية",
    "للدفاع عن القانون والحق",
    "المجلس الأعلى للسلطة القضائية",
]

TITRES_SEULS = ["السيد", "السيدة", "الأستاذ", "ذ."]


def extraire_nom_residuel(valeur: str) -> str:
    if not valeur:
        return ""
    residu = valeur
    for mot in sorted(MOTS_ROLES, key=len, reverse=True):
        residu = residu.replace(mot, " ")
    for mot in MOTS_PARASITES:
        residu = residu.replace(mot, " ")
    residu = re.sub(r"^ب\s+", "", residu)
    residu = re.sub(r"\s+", " ", residu).strip(" :.()")
    return residu


def ressemble_a_un_role_pas_un_nom(valeur: str) -> bool:
    if not valeur:
        return False
    valeur = valeur.strip()
    if not valeur:
        return False
    residu = extraire_nom_residuel(valeur)
    if len(residu) < 2:
        return True
    sans_titre = residu
    for titre in TITRES_SEULS:
        sans_titre = sans_titre.replace(titre, " ")
    sans_titre = re.sub(r"\s+", " ", sans_titre).strip(" :.()")
    return len(sans_titre) < 2


def nettoyer_champs_haia(haia: dict) -> dict:
    for champ in ("president_rapporteur", "greffier", "procureur"):
        valeur = haia.get(champ, "")
        if ressemble_a_un_role_pas_un_nom(valeur):
            haia[champ] = ""
        else:
            haia[champ] = extraire_nom_residuel(valeur)

    assesseurs = haia.get("assesseurs", [])
    if isinstance(assesseurs, list):
        nouveaux = []
        for nom in assesseurs:
            if not ressemble_a_un_role_pas_un_nom(nom):
                nouveaux.append(extraire_nom_residuel(nom))
        haia["assesseurs"] = nouveaux

    return haia


def isoler_zone_haia(texte: str) -> str:
    for ancre in ANCRES_HAIA:
        idx = texte.find(ancre)
        if idx != -1:
            debut = idx
            fin = idx + len(ancre) + TAILLE_FENETRE_HAIA
            return texte[debut:fin]
    return texte[:800]


def extraire_haia(texte: str) -> dict:
    fenetre = isoler_zone_haia(texte)

    prompt = f"""You are an expert assistant for Moroccan judicial documents written in Arabic.

The text below is a SHORT EXCERPT (already isolated) that introduces the panel
of judges (الهيئة) for ONE specific decision. It contains OCR errors: words can
be split by stray spaces, or have garbled/missing letters. The role label can
appear BEFORE or AFTER the name, on the same line or a separate line. Examples
of BOTH valid patterns:
  Pattern A (label then name, next line):
    "رئيسا ومقررا .
    السيد هشام الوازيكي"
  Pattern B (name then label, same line):
    "السيد(ة) ادريس    رئيسا ومقررا"
    "السيد(ة) إلهام    مستشارا"
In both patterns, extract the NAME part (e.g. "السيد ادريس", "السيد إلهام"),
never the role label itself (رئيسا, ومقررا, عضوا, مستشارا, كاتب الضبط, etc.)
as if it were a name.

CRITICAL - do not deduplicate similar-looking names: in Moroccan court
documents, family names are sometimes redacted/blacked out for privacy in the
source document, so two DIFFERENT judges can appear with the exact same
visible OCR text (e.g. two entries both reading "السيد(ة) ادريس" - once for
"رئيسا ومقررا" and again for "مستشارا"). These are TWO SEPARATE PEOPLE, not a
duplicate - you MUST list each occurrence separately in its correct role slot,
even if the visible name text is identical or very short. NEVER skip, merge,
or shift roles because a name looks repeated.

Extract ONLY the names found in THIS excerpt - do not invent names, and do not
include lawyers or parties. If NO panel composition information is present in
this excerpt at all, return empty values for all fields.

Note: a Moroccan Cassation Court panel sitting "بغرفتين" can have MANY
assessor judges (up to 6+). A normal tribunal/appeal panel usually has 1-2.
Extract ALL assessor names you find, in the exact order they appear, however
many there are - do not drop any.

Roles to identify:
- "president_rapporteur": marked by "رئيسا" or "رئيسا ومقررا"
- "assesseurs": a LIST of all judges marked by "عضوا", "أعضاء", "مستشارا"/"مستشار"
- "greffier": the court clerk, marked by "كاتب الضبط", "كاتبة الضبط", or a name
  following a (possibly broken) form of "بمساعدة" - this is NEVER an assessor,
  keep it in its own separate field even if it appears right after the last
  assessor in the list.
- "procureur": marked by "المحامي العام" or "النيابة العامة" or "الوكيل العام للملك"
  or "المفوض الملكي للدفاع عن القانون والحق"

If a role is not present in this excerpt, use "" (or [] for assesseurs).

Excerpt:
\"\"\"
{fenetre}
\"\"\"

Respond ONLY with this JSON, with clean corrected Arabic text (no OCR artifacts):
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
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
            timeout=120,
        )
        reponse.raise_for_status()
        contenu = reponse.json()["response"]
        resultat = json.loads(contenu)
        return nettoyer_champs_haia(resultat)
    except Exception as e:
        return {
            "president_rapporteur": f"ERREUR: {e}",
            "assesseurs": [],
            "greffier": "",
            "procureur": "",
        }


# ---------------------------------------------------------------------------
# PARTIE 4 : المنطوق (dispositif final)
# ---------------------------------------------------------------------------

TAILLE_FENETRE_MANTOUK = 1200

VERBES_DECISION = [
    "حكمت المحكمة",
    "قضت محكمة",
    "قضت المحكمة",
    "تصرح محكمة",
    "قررت محكمة",
    "حكمت محكمة",
    "فإن محكمة",
]


def isoler_zone_mantouk(texte: str) -> str:
    meilleur_idx = -1
    for verbe in VERBES_DECISION:
        idx = texte.rfind(verbe)
        if idx > meilleur_idx:
            meilleur_idx = idx

    if meilleur_idx != -1:
        zone_recherche = texte[max(0, meilleur_idx - 500):meilleur_idx]
        idx_ancre = zone_recherche.rfind("لهذه الأسباب")
        if idx_ancre != -1:
            debut = max(0, meilleur_idx - 500) + idx_ancre
        else:
            debut = meilleur_idx
        return texte[debut:meilleur_idx + TAILLE_FENETRE_MANTOUK]

    idx = texte.rfind("لهذه الأسباب")
    if idx != -1:
        return texte[idx:idx + TAILLE_FENETRE_MANTOUK]

    return texte[-2000:]


def extraire_mantouk(texte: str) -> str:
    fenetre = isoler_zone_mantouk(texte)

    prompt = f"""You are an expert assistant for Moroccan judicial documents written in Arabic.

The text below is a SHORT EXCERPT (already isolated, near the end of the decision)
that may contain OCR errors, including:
- Spelling/character recognition mistakes on real words.
- Watermark or stamp artifacts bleeding into the text - short, out-of-place,
  garbled fragments of a court name - these must be REMOVED, not corrected into place.
- IMPORTANT: the excerpt may begin with a small incomplete/dangling fragment
  cut off mid-word or mid-sentence, left over from unrelated text that
  precedes the actual ruling. If the very beginning of the excerpt does not
  form a grammatically complete, sensible opening, SKIP that leading fragment
  entirely and start your answer from the first clean, complete clause you
  find (typically "لهذه الأسباب" or "وبعد المداولة" or the court's decision
  verb). Do not reproduce a leading fragment that does not make sense on its own.

It should contain the FINAL DISPOSITIVE / RULING (منطوق الحكم أو القرار) - the
court's own decision, typically starting with "حكمت المحكمة" or "قضت محكمة" or
"تصرح محكمة" or "قررت محكمة" or "فإن محكمة". Do NOT confuse this with a
PARTY'S REQUEST/PRAYER ("لهذه الأسباب" followed by "تلتمس العارضة..." = what a
party is asking for, NOT the court's decision).

Extract that ruling, correcting real OCR spelling mistakes and removing
watermark artifacts and leading dangling fragments, so the result reads as
clean, proper Arabic - but do NOT paraphrase, summarize, or change the legal
meaning. If no court ruling is present in this excerpt, return an empty string.

CRITICAL - keep everything from the true start, omit nothing after it:
once you have identified the real starting point, reproduce the ENTIRE ruling
text from there through to the end of the substantive content (up to but not
including the closing signature formula like "وبهذا صدر القرار"). Do NOT skip
the court's name, the decision verb, the procedural qualifiers
(انتهائيا/علنيا/حضوريا/غيابيا), the "في الشكل" section, or the "في الموضوع"/
"في الجوهر" section. Never restructure word order, never replace one verb
with another, never summarize.

CRITICAL - do not invent text: every word you output must correspond to
something actually present in the excerpt (once OCR errors are corrected).

Excerpt:
\"\"\"
{fenetre}
\"\"\"

Respond ONLY with this JSON, with clean corrected Arabic text (no OCR artifacts,
no leading dangling fragments):
{{"mantouk": "..."}}
"""
    try:
        reponse = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
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
    tribunal = extraire_tribunal(texte)
    haia = extraire_haia(texte)
    mantouk = extraire_mantouk(texte)

    print("\n" + "=" * 60)
    print("  RESULTAT DE L'EXTRACTION")
    print("=" * 60)
    print(f"\nرقم الملف (numero de dossier) : {numero}")
    print(f"المحكمة (tribunal)            : {tribunal}")

    print(f"\nالهيئة (college de juges)")
    print(f"   - رئيسا ومقررا (president) : {haia.get('president_rapporteur', '') or '-'}")
    assesseurs = haia.get("assesseurs", [])
    if assesseurs:
        for i, nom in enumerate(assesseurs, 1):
            print(f"   - عضو {i} (assesseur)      : {nom}")
    else:
        print(f"   - عضو (assesseur)         : -")
    print(f"   - كاتب الضبط (greffier)    : {haia.get('greffier', '') or '-'}")
    print(f"   - المحامي العام (procureur) : {haia.get('procureur', '') or '-'}")

    print(f"\nقرار المحكمة النهائي (dispositif final)")
    print(f"   {mantouk}")
    print("\n" + "=" * 60 + "\n")
