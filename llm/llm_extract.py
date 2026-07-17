"""
Module d'extraction : numéro de dossier + tribunal + الهيئة (bench) +
المنطوق (dispositif final) + indemnisation (montant réclamé calculé vs accordé)
"""

import sys
import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"


# ---------------------------------------------------------------------------
# PARTIE 1 : Numéro de dossier (règle déterministe)
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
- "المحكمة الإدارية ب<ville>" (Administrative Court of <city>)
- "محكمة الاستئناف التجارية ب<ville>" (Commercial Court of Appeal of <city>)
- "محكمة الاستئناف الإدارية ب<ville>" (Administrative Court of Appeal of <city>)
- "محكمة النقض" (Court of Cassation - no city, it is the supreme court)

IMPORTANT: this text is OCR output and often contains letter-level corruption
(e.g. "الاستئنانف" instead of "الاستئناف", "الفادرة" instead of "الإدارية").
Correct these into the standard, grammatically correct court name - do not
reproduce OCR corruption in your answer.

Note: a document can mention MULTIPLE courts (e.g. the court that originally
handled a related file, versus the court actually issuing THIS decision).
The court issuing THIS decision is the one associated with the judges panel
(الهيئة) and the final ruling (المنطوق) - prefer that one if there is any
ambiguity between two different court names in the text.

The court name may appear anywhere in the text - in the header (often repeated
in a box/table), or later in the body. Search the WHOLE text if needed.
Extract it once, in its clean, complete, correct form. Do not include the
case number, decision number, or date - only the court's name.
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
    "متكونة من السادة",
    "متكونة من",
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
be split by stray spaces, or have garbled/missing letters, including the ROLE
LABELS themselves (e.g. "رئيسا" can appear corrupted as OCR noise like "رنبسا").
Do NOT assume a corrupted word next to a name is part of that person's name
just because it doesn't look like a clean role word - if a short garbled word
sits exactly where a role label is grammatically expected (right after the
first name in a judges list, before "عضوا" for others), treat it as a
corrupted ROLE LABEL, not as part of the name.

The role label can appear BEFORE or AFTER the name, on the same line or a
separate line. Examples of valid patterns:
  Pattern A (label then name, next line):
    "رئيسا ومقررا .
    السيد هشام الوازيكي"
  Pattern B (name then label, same line):
    "السيد(ة) ادريس    رئيسا ومقررا"
    "السيد(ة) إلهام    مستشارا"
  Pattern C (list of names, first is implicitly "رئيسا" / president even if
  the role word is OCR-corrupted, others explicitly marked "عضوا"):
    "متكونة من السادة: فلان [رئيسا-corrompu]. علان [اسم آخر] عضوا"

CRITICAL - do not deduplicate similar-looking names: family names are
sometimes redacted for privacy, so two DIFFERENT judges can appear with the
exact same visible OCR text. List each occurrence separately in its correct
role slot, even if identical or very short. NEVER skip, merge, or shift roles
because a name looks repeated.

Extract ONLY names found in THIS excerpt - do not invent names, and do not
include lawyers or parties. If NO panel composition information is present in
this excerpt at all, return empty values for all fields.

Note: a Cassation Court panel "بغرفتين" can have MANY assessor judges (6+).
A normal tribunal/appeal panel usually has 1-2. Extract ALL assessor names,
in exact order, however many there are.

Roles to identify:
- "president_rapporteur": marked by "رئيسا" or "رئيسا ومقررا" (often the
  FIRST person named, even if the role word is OCR-corrupted)
- "assesseurs": list of judges marked by "عضوا", "أعضاء", "مستشارا"/"مستشار"
- "greffier": the court CLERK ("كاتب الضبط" / "كاتبة الضبط"), often
  introduced by "بحضور" or "بمساعدة" together with the "المفوض الملكي" -
  these are TWO DIFFERENT PEOPLE even when named right next to each other.
  Never put the "المفوض الملكي" name in this field.
- "procureur": the ROYAL COMMISSIONER / PROSECUTOR, marked by "المفوض الملكي"
  or "المحامي العام" or "النيابة العامة" or "الوكيل العام للملك"

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
# PARTIE 5 : Indemnisation - calcul déterministe du montant réclamé (Python),
#            LLM uniquement pour interpréter le montant réellement accordé
# ---------------------------------------------------------------------------

def parser_montant(chaine: str):
    """Convertit un montant en notation marocaine (point = milliers,
    virgule = décimales) en nombre flottant Python."""
    chaine = re.sub(r"[^\d,.]", "", chaine)
    if not chaine:
        return None
    chaine = chaine.replace(".", "")
    chaine = chaine.replace(",", ".")
    try:
        return float(chaine)
    except ValueError:
        return None


def isoler_section_faits(texte: str) -> str:
    """Retourne la partie du texte AVANT le dispositif final (donc la section
    des faits/demandes), pour ne jamais mélanger un montant réclamé par une
    partie avec un montant mentionné par le tribunal lui-même."""
    fenetre_mantouk = isoler_zone_mantouk(texte)
    idx = texte.find(fenetre_mantouk)
    if idx > 0:
        return texte[:idx]
    return texte


def trouver_montants_individuels(texte: str):
    """Trouve TOUS les montants suivis de 'درهم' dans la section des faits.

    Le regex capture toute la sequence de chiffres/points/virgules qui
    precede 'درهم', sans limite de taille sur le premier groupe (sinon un
    montant sans separateur de milliers, ex: '5500 درهم', est tronque)."""

    section_faits = isoler_section_faits(texte)

    motif = r"([\d]+(?:[.,][\d]+)*)\s*درهم"
    montants = []

    for match in re.finditer(motif, section_faits):
        debut_contexte = max(0, match.start() - 25)
        contexte_avant = section_faits[debut_contexte:match.start()]

        # Exclut le montant si c'est celui de la ligne de total explicite
        if "مجموع" in contexte_avant:
            continue

        valeur = parser_montant(match.group(1))
        if valeur is not None and valeur > 0:
            montants.append(valeur)

    return montants


def dedupliquer_montants(montants: list) -> list:
    """Les jugements marocains reformulent souvent la meme demande deux fois:
    une fois dans les faits ('بناء على المقال الافتتاحي'), une fois dans le
    paragraphe 'وبعد المداولة ... عين بهدف الطلب' juste avant que le tribunal
    ne traite une question de forme (competence, recevabilite, etc). Si la
    liste de montants trouves se scinde en deux moities strictement
    identiques (memes valeurs, meme ordre), c'est cette repetition - on ne
    garde que la premiere moitie pour ne pas compter chaque montant deux
    fois dans le total."""
    n = len(montants)
    if n % 2 == 0 and n > 0:
        moitie = n // 2
        if montants[:moitie] == montants[moitie:]:
            return montants[:moitie]
    return montants


def formater_montant(valeur: float) -> str:
    entier = int(valeur)
    decimales = round((valeur - entier) * 100)
    entier_str = f"{entier:,}".replace(",", ".")
    return f"{entier_str},{decimales:02d}"


def calculer_montant_reclame(texte: str) -> dict:
    """Calcule le montant total réclamé en additionnant chaque montant
    individuel trouvé dans la section des faits (calcul Python déterministe,
    jamais confié au LLM), après avoir retiré une éventuelle répétition
    intégrale de la liste (voir dedupliquer_montants)."""
    montants_bruts = trouver_montants_individuels(texte)
    montants = dedupliquer_montants(montants_bruts)

    if not montants:
        return {"montant_reclame_calcule": "NON TROUVE", "detail_montants": []}

    total = sum(montants)
    return {
        "montant_reclame_calcule": formater_montant(total) + " درهم",
        "detail_montants": [formater_montant(m) for m in montants],
    }


def extraire_indemnisation(texte: str) -> dict:
    """Combine le calcul déterministe du montant réclamé (Python) avec
    l'analyse contextuelle du LLM pour déterminer ce que le tribunal a
    réellement accordé."""

    calcul = calculer_montant_reclame(texte)
    fenetre_mantouk = isoler_zone_mantouk(texte)

    prompt = f"""You are an expert assistant for Moroccan judicial documents written in Arabic.

The plaintiff's total claimed compensation has ALREADY been calculated
automatically by summing each individual amount mentioned in the facts
section: {calcul['montant_reclame_calcule']}. You do NOT need to recompute
this - it is provided for your context only.

Your ONLY task here is to determine whether the COURT actually AWARDED any
amount in its final ruling below, and how much. Moroccan court rulings may:
- Award the full or a partial amount ("الحكم بأداء ... مبلغ ... درهم")
- REJECT the claim entirely ("رفض الطلب")
- Decline jurisdiction without ruling on the merits at all
  ("عدم اختصاص المحكمة نوعيا للبت في الطلب" / "عدم الاختصاص")
- Declare the claim inadmissible ("عدم قبول الطلب")

If the court rejected the claim, declared itself incompetent, or did not rule
on the merits at all, montant_accorde must be "0 - aucun montant accordé" and
"statut" must be EXACTLY one of these short labels (nothing else, no full
sentence): "juridiction incompétente", "demande rejetée", "montant accordé
intégralement", "montant accordé partiellement", "demande irrecevable".

Ruling excerpt:
\"\"\"
{fenetre_mantouk}
\"\"\"

Respond ONLY with this JSON:
{{
  "montant_accorde": "...",
  "statut": "..."
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
            timeout=180,
        )
        reponse.raise_for_status()
        contenu = reponse.json()["response"]
        resultat = json.loads(contenu)
    except Exception as e:
        resultat = {"montant_accorde": f"ERREUR: {e}", "statut": "erreur"}

    return {
        "montant_reclame": calcul["montant_reclame_calcule"],
        "detail_montants_individuels": calcul["detail_montants"],
        "montant_accorde": resultat.get("montant_accorde", "NON TROUVE"),
        "statut": resultat.get("statut", ""),
    }


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
    indemnisation = extraire_indemnisation(texte)

    print("\n" + "=" * 60)
    print("  RESULTAT DE L'EXTRACTION")
    print("=" * 60)
    print(f"\nرقم الملف : {numero}")
    print(f"المحكمة : {tribunal}")

    print(f"\nالهيئة")
    print(f"   - رئيسا ومقررا : {haia.get('president_rapporteur', '') or '-'}")
    assesseurs = haia.get("assesseurs", [])
    if assesseurs:
        for i, nom in enumerate(assesseurs, 1):
            print(f"   - عضو {i} : {nom}")
    else:
        print(f"   - عضو : -")
    print(f"   - كاتب الضبط : {haia.get('greffier', '') or '-'}")
    print(f"   - المحامي العام : {haia.get('procureur', '') or '-'}")

    print(f"\nقرار المحكمة النهائي")
    print(f"   {mantouk}")

    print(f"\nالتعويض")
    print(f"   - المبالغ الفردية المكتشفة : {', '.join(indemnisation.get('detail_montants_individuels', [])) or '-'}")
    print(f"   - المبلغ المطلوب (مجموع محسوب) : {indemnisation.get('montant_reclame', '-')}")
    print(f"   - المبلغ الممنوح : {indemnisation.get('montant_accorde', '-')}")
    print(f"   - الوضعية : {indemnisation.get('statut', '-')}")
    print("\n" + "=" * 60 + "\n")
