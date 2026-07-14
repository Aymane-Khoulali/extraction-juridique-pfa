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
# PARTIE 2 : الهيئة (bench) - fenêtre isolée + liste flexible de membres
# ---------------------------------------------------------------------------

ANCRES_HAIA = [
    "الهيئة الحاكمة",
    "مؤلفة من السادة",
    "مؤلفة من",
    "تتكون من السادة",
    "تتكون من",
    "متركبة من",   # variante rencontrée sur les cours administratives
]

TAILLE_FENETRE_HAIA = 900

# Mots/labels de rôle qui ne doivent JAMAIS constituer, à eux seuls, la valeur
# d'un champ nom - sert de garde-fou après l'appel LLM.
MOTS_ROLES = [
    "رئيسا ومقررا",
    "رئيسا",
    "ومقررا",
    "عضوا",
    "أعضاء",
    "كاتب الضبط",
    "كاتبة الضبط",
    "بمساعدة",
    "المحامي العام",
    "محامي العام",
    "النيابة العامة",
    "الوكيل العام",
    "المفوض الملكي",
]

# Marقueurs typiques qui précèdent un vrai nom propre en arabe judiciaire.
MARQUEURS_NOM = ["السيد", "السيدة", "الأستاذ", " ذ."]


def isoler_zone_haia(texte: str) -> str:
    for ancre in ANCRES_HAIA:
        idx = texte.find(ancre)
        if idx != -1:
            debut = idx
            fin = idx + len(ancre) + TAILLE_FENETRE_HAIA
            return texte[debut:fin]
    return texte[:800]


# Mots de liaison/parasites sans valeur informative, à retirer avant de juger
# s'il reste un vrai nom (préposition "بمساعدة" isolée, article, ponctuation OCR,
# artefacts de filigrane/en-tête, fragments de la formule légale du procureur).
MOTS_PARASITES = [
    "بمساعدة",
    "بال",
    " ب ",
    "المملكة المغربية",
    "للدفاع عن القانون والحق",
    "المجلس الأعلى للسلطة القضائية",
]

# Titres seuls (sans nom propre derrière) qui ne comptent pas comme un vrai nom.
TITRES_SEULS = ["السيد", "السيدة", "الأستاذ", "ذ."]


def extraire_nom_residuel(valeur: str) -> str:
    """Retire tous les labels de rôle connus d'une chaîne et renvoie ce qu'il
    reste, nettoyé. Sert à juger si un vrai nom propre subsiste derrière le
    label, plutôt que de simplement vérifier la présence d'un marqueur."""
    if not valeur:
        return ""
    residu = valeur
    # Les labels les plus longs d'abord, pour ne pas laisser de fragments
    # partiels d'un label plus long (ex: retirer "رئيسا ومقررا" avant "رئيسا").
    for mot in sorted(MOTS_ROLES, key=len, reverse=True):
        residu = residu.replace(mot, " ")
    for mot in MOTS_PARASITES:
        residu = residu.replace(mot, " ")
    # Préposition "ب" isolée en tout début de chaîne (pas toujours précédée
    # d'un espace, donc non captée par MOTS_PARASITES) - ex: "ب السيد فلان".
    residu = re.sub(r"^ب\s+", "", residu)
    residu = re.sub(r"\s+", " ", residu).strip(" :.")
    return residu


def ressemble_a_un_role_pas_un_nom(valeur: str) -> bool:
    """Détecte si, une fois les labels de rôle retirés, il ne reste aucun nom
    propre substantiel (donc que la valeur n'était qu'un label recopié, seul
    ou accolé à un marqueur de nom sans vrai nom derrière)."""
    if not valeur:
        return False
    valeur = valeur.strip()
    if not valeur:
        return False
    residu = extraire_nom_residuel(valeur)
    # Un vrai nom marocain tient rarement en moins de ~4 caractères une fois
    # les labels retirés (ex: "أحمد اليوسفي العلوي" reste long, alors qu'un
    # label vidé de son contenu ne laisse presque rien).
    if len(residu) < 4:
        return True

    # Rejeter aussi un résidu qui n'est qu'un titre seul (ex: "السيد" tout seul,
    # sans nom propre derrière) - on retire les titres et on vérifie qu'il
    # reste quelque chose de substantiel.
    sans_titre = residu
    for titre in TITRES_SEULS:
        sans_titre = sans_titre.replace(titre, " ")
    sans_titre = re.sub(r"\s+", " ", sans_titre).strip(" :.")
    return len(sans_titre) < 4


def nettoyer_champs_haia(haia: dict) -> dict:
    """Passe chaque champ du résultat au garde-fou : si ce n'est qu'un label
    de rôle (seul ou accolé à un marqueur de nom sans vrai nom derrière), on
    vide le champ ; sinon on ne garde que le nom résiduel propre (sans le
    label collé devant/derrière)."""
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


def extraire_haia(texte: str) -> dict:
    fenetre = isoler_zone_haia(texte)

    prompt = f"""You are an expert assistant for Moroccan judicial documents written in Arabic.

The text below is a SHORT EXCERPT (already isolated) that introduces the panel
of judges (الهيئة) for ONE specific decision. It contains OCR errors:
- Words can be split by stray spaces in the middle, or have garbled/missing letters.
- Isolated, out-of-place repeated words (watermark/stamp artifacts) should be ignored.
- The role label can appear BEFORE or AFTER the name, on the same line or a
  separate line (e.g. "رئيسا ومقررا" on one line, then the name on the next line).
  Adapt to either ordering.
MENTALLY RECONSTRUCT and CORRECT such OCR errors before extracting.

CRITICAL - role label vs. person's name:
A role label is very often immediately followed by the person's actual name on
the VERY NEXT LINE, sometimes with a stray period "." right after the role word
(this is an OCR artifact for what was likely originally a colon ":"). Example:
  "رئيسا ومقررا .
  السيد هشام الوازيكي"
means: president_rapporteur = "السيد هشام الوازيكي" - NOT "رئيسا ومقررا".
NEVER return a role label itself (رئيسا, ومقررا, عضوا, كاتب الضبط, كاتبة الضبط,
المحامي العام, بمساعدة, etc.) as if it were a person's name. A valid name
almost always starts with a title such as السيد / السيدة / الأستاذ / ذ.
followed by an actual proper name. If you cannot find a real proper name for a
role in this excerpt, leave that field empty - do NOT fall back to the label.

Extract ONLY the names found in THIS excerpt - do not invent names, and do not
include lawyers or parties. If NO panel composition information is present in
this excerpt at all, return empty values for all fields.

Note: a Moroccan Cassation Court panel sitting "بغرفتين" (two chambers combined)
can have MANY assessor judges (up to 6+). A normal tribunal/appeal panel usually
has 1-2. Extract ALL assessor names you find, however many there are.

Roles to identify:
- "president_rapporteur": marked by "رئيسا" or "رئيسا ومقررا"
- "assesseurs": a LIST of all judges marked by "عضوا" or "أعضاء"
- "greffier": the court clerk, marked by "كاتب الضبط", "كاتبة الضبط", or a name
  following a (possibly broken) form of "بمساعدة"
- "procureur": marked by "المحامي العام" or "النيابة العامة" or "الوكيل العام للملك"
  or "المفوض الملكي للدفاع عن القانون والحق" (royal commissioner, administrative courts)

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
# PARTIE 3 : المنطوق (dispositif final) - recherche des verbes de décision
# ---------------------------------------------------------------------------

TAILLE_FENETRE_MANTOUK = 1200

VERBES_DECISION = [
    "حكمت المحكمة",
    "قضت محكمة",
    "قضت المحكمة",
    "تصرح محكمة",
    "قررت محكمة",
    "حكمت محكمة",
    "فإن محكمة",   # variante "لهذه الأسباب فإن محكمة X وهي تبت..."
]


def isoler_zone_mantouk(texte: str) -> str:
    """Cherche la DERNIÈRE occurrence d'un vrai verbe de décision du tribunal
    (pas juste 'لهذه الأسباب', qui est ambigu et peut introduire la demande
    d'une partie plutôt que la décision elle-même)."""
    meilleur_idx = -1
    for verbe in VERBES_DECISION:
        idx = texte.rfind(verbe)
        if idx > meilleur_idx:
            meilleur_idx = idx

    if meilleur_idx != -1:
        debut = max(0, meilleur_idx - 100)  # marge arrière pour capter "لهذه الأسباب" s'il précède
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
  garbled fragments of a court name - these are NOT part of the actual ruling
  text and must be REMOVED, not corrected into place.

It should contain the FINAL DISPOSITIVE / RULING (منطوق الحكم أو القرار) - the
court's own decision, typically starting with "حكمت المحكمة" or "قضت محكمة" or
"تصرح محكمة" or "قررت محكمة". IMPORTANT: do NOT confuse this with a PARTY'S
REQUEST/PRAYER (which may also start with "لهذه الأسباب" followed by "تلتمس
العارضة..." = "the petitioner requests..." - this is what a PARTY is asking
for, NOT what the court decided). Only extract the court's own ruling.

Extract that ruling, correcting real OCR spelling mistakes and removing
watermark artifacts, so the result reads as clean, proper Arabic - but do NOT
paraphrase, summarize, or change the legal meaning. If no court ruling is
present in this excerpt, return an empty string.

CRITICAL - keep everything, omit nothing: reproduce the ENTIRE ruling text
from the court's decision verb (حكمت/قضت/تصرح/قررت/فإن محكمة) all the way
through to the end of the substantive content (up to but not including the
closing signature formula like "وبهذا صدر القرار" or "بنفس الهيئة التي
شاركت"). Do NOT skip, drop, or omit ANY clause - not the court's name, not the
decision verb, not the procedural qualifiers (انتهائيا/علنيا/حضوريا/غيابيا),
not the "في الشكل" section, not the "في الموضوع" section. Every one of these
parts must appear in your output, in their original order. The ONLY changes
allowed are: (1) fixing garbled OCR spelling of real words, (2) removing a
clearly extraneous watermark/stamp fragment that interrupts a sentence
mid-way (e.g. a stray repeated court name bleeding into the middle of a
clause). Never restructure word order, never replace one verb with another,
never summarize any part - if in doubt, keep the original wording.

CRITICAL - do not invent text: every word you output must correspond to
something actually present in the excerpt (once OCR errors are corrected).
Do NOT add clauses, verbs, or phrases that are not in the excerpt.

Excerpt:
\"\"\"
{fenetre}
\"\"\"

Respond ONLY with this JSON, with clean corrected Arabic text (no OCR artifacts):
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
