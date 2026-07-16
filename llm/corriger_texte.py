"""
Module de correction orthographique : corrige les fautes d'OCR dans un texte
arabe complet, sans changer le sens ni résumer.

Usage :
    python3 llm/corriger_texte.py fichier.txt > fichier_corrige.txt
    cat fichier.txt | python3 llm/corriger_texte.py > fichier_corrige.txt
"""

import sys
import re
import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

TAILLE_MORCEAU = 2500


def decouper_en_morceaux(texte: str, taille: int = TAILLE_MORCEAU):
    morceaux = []
    debut = 0
    n = len(texte)

    while debut < n:
        fin = min(debut + taille, n)
        if fin < n:
            coupure = texte.rfind("\n", debut, fin)
            if coupure == -1 or coupure <= debut:
                coupure = texte.rfind(" ", debut, fin)
            if coupure != -1 and coupure > debut:
                fin = coupure
        morceaux.append(texte[debut:fin])
        debut = fin

    return morceaux


def extraire_sequences_numeriques(texte: str):
    """Extrait toutes les séquences de 3 chiffres ou plus (dates, numéros de
    dossier/loi/article...) présentes dans un texte."""
    return set(re.findall(r"\d{3,}", texte))


def contient_nombre_invente(morceau_corrige: str, texte_complet_original: str) -> bool:
    """Vérifie si le texte corrigé contient une séquence numérique (3+ chiffres)
    qui n'apparaît NULLE PART dans le document original complet - signe quasi
    certain d'une date/numéro inventé par le LLM plutôt que recopié du texte."""
    nombres_originaux = extraire_sequences_numeriques(texte_complet_original)
    nombres_corriges = extraire_sequences_numeriques(morceau_corrige)
    nombres_suspects = nombres_corriges - nombres_originaux
    return len(nombres_suspects) > 0


def corriger_morceau(morceau: str, texte_complet_original: str) -> str:
    """Envoie un morceau de texte au LLM pour correction orthographique pure,
    avec garde-fous stricts contre l'invention de contenu."""

    prompt = f"""You are an expert proofreader for Moroccan judicial documents written in Arabic.

The text below is raw OCR output and contains spelling/character recognition
errors: missing or swapped letters, stray spaces splitting words in the
middle, garbled fragments, and occasional watermark/stamp artifacts bleeding
into the text.

Your task: rewrite this text correcting ONLY the OCR/spelling errors, so it
reads as clean, grammatically correct Arabic.

ABSOLUTE RULES - violating any of these is a serious failure:

1. NEVER replace a vague or generic reference with a specific value pulled
   from elsewhere. Example of what NOT to do: the original says "بالتاريخ
   المذكور أعلاه" (= "on the date mentioned above", a vague back-reference) -
   you must KEEP this vague reference exactly as-is. Do NOT replace it with
   an actual date like "1958/12/9" even if such a date appears elsewhere in
   the text - that would be a fabrication, not a correction.

2. NEVER invent a word that does not exist in real Arabic just to make a
   sentence grammatically complete. Example of what NOT to do: an artifact
   like "المملكة التيغرببة" must NOT become "المملكة التي غرببت" (inventing
   a fake verb "غرببت" to patch the grammar). If a watermark/stamp artifact
   breaks a sentence, REMOVE the artifact fragment entirely rather than
   inventing words to stitch the sentence back together.

3. NEVER merge two distinct real institution names into one that does not
   exist. Example of what NOT to do: "المجلس الأعلى للسلطة القضائية" (Supreme
   Council of the Judiciary) and "محكمة النقض" (Court of Cassation) are TWO
   DIFFERENT institutions - if OCR garbled their boundary, keep them as two
   separate recognizable names, do not fuse them into a single invented name
   like "محكمة النقض العليا للسلطة القضائية".

4. If a fragment is too corrupted to confidently reconstruct with real
   certainty, DO NOT GUESS. Leave it as close to the original garbled form as
   possible, or mark it with [?] rather than inventing plausible-sounding but
   uncertain content. A visibly imperfect but honest result is better than a
   fluent but fabricated one.

5. Do NOT summarize, paraphrase, shorten, or change the meaning in any way.
   Do NOT add any information that is not already present in the text.
   Keep the same structure, paragraph breaks, and order of ideas.

Text to correct:
\"\"\"
{morceau}
\"\"\"

Respond ONLY with this JSON, containing the corrected text:
{{"texte_corrige": "..."}}
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
        corrige = resultat.get("texte_corrige", "")

        # Filet 1 : texte vide ou anormalement raccourci -> on garde l'original
        if not corrige or len(corrige) < len(morceau) * 0.5:
            return morceau

        # Filet 2 : nombre inventé (date/numéro absent de tout le document
        # original) -> signe fort d'hallucination, on rejette et garde l'original
        if contient_nombre_invente(corrige, texte_complet_original):
            print("[garde-fou] nombre suspect détecté, morceau original conservé", file=sys.stderr)
            return morceau

        return corrige
    except Exception:
        return morceau


def corriger_texte_complet(texte: str) -> str:
    if not texte or not texte.strip():
        return ""

    morceaux = decouper_en_morceaux(texte)
    morceaux_corriges = []

    for i, morceau in enumerate(morceaux, 1):
        print(f"[correction] morceau {i}/{len(morceaux)}...", file=sys.stderr)
        morceaux_corriges.append(corriger_morceau(morceau, texte))

    return "".join(morceaux_corriges)


def lire_texte_entree() -> str:
    if len(sys.argv) > 1:
        chemin = sys.argv[1]
        with open(chemin, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return sys.stdin.read()


if __name__ == "__main__":
    texte = lire_texte_entree()
    texte_corrige = corriger_texte_complet(texte)
    print(texte_corrige)
