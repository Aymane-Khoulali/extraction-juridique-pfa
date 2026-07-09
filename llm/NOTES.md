# Notes techniques — Extraction du numéro de dossier (LLM)

## Objectif

Extraire automatiquement le numéro de dossier (رقم الملف) à partir du texte OCR
brut d'une décision de justice marocaine en arabe, quel que soit le tribunal ou
le type de document (jugement de 1ère instance, arrêt d'appel, arrêt de Cassation).

## Approche finale retenue
Le LLM (Qwen2.5:7b via Ollama) n'est utilisé qu'en tout dernier recours, si la
regex ne détecte aucun candidat. **Il n'est plus utilisé pour choisir entre
plusieurs candidats** — voir la section "Pourquoi" ci-dessous.

## Règles de la regex

- Motif : `(?:19|20)\d{2}(?:/\d{1,6}){1,3}` — doit commencer par un vrai
  millésime (19xx ou 20xx).
- Exclusion des dates (format AAAA/mois/jour où mois ≤ 12 et jour ≤ 31).
- Le premier candidat valide trouvé, dans l'ordre d'apparition du texte, est
  retenu comme numéro de dossier.

## Pièges rencontrés et résolus (par ordre chronologique de découverte)

1. **Numéro de jugement/arrêt vs numéro de dossier**
   Ex : "رقم 3762" (numéro du jugement) vs "في الملف رقم 2017/8218/11122"
   (numéro de dossier). Solution : la regex ne matche que les motifs avec
   au moins un `/`, ce qui exclut le numéro de jugement (souvent un nombre seul).

2. **Numéro de dossier d'une affaire référencée (citée) dans le texte**
   Cas d'un arrêt de Cassation citant une affaire antérieure : le texte
   mentionne un premier numéro dans l'en-tête (le bon), puis un second numéro
   plus loin dans les faits, en référence à un jugement antérieur cité
   ("الملف المدني عدد ..."). Le second numéro est souvent MIEUX écrit
   (moins d'erreurs OCR) que le premier, ce qui attire le LLM vers la
   mauvaise réponse.
   → Tenté : prompt engineering (règles explicites, few-shot avec exemple
     concret). Résultat : fonctionne parfois, mais pas de façon fiable à 100%.
   → Solution finale : ne plus laisser le LLM choisir. Le premier candidat
     dans l'ordre d'apparition du texte est toujours le bon, de façon
     déterministe.

3. **Confusion avec une date au même format**
   Ex : "المؤرخ في : 2015/2/26" (une date) matche la même regex qu'un vrai
   numéro de dossier ("عدد : 2012/6/1/4002"), et apparaît AVANT lui dans le
   texte — ce qui cassait la règle "premier candidat" si les dates n'étaient
   pas filtrées.
   → Solution : fonction `ressemble_a_une_date()` qui exclut tout motif où
     les 2e et 3e segments ressemblent à un mois (≤12) et un jour (≤31) valides.

4. **Confusion avec un numéro de loi**
   Ex : "القانون رقم 15/02" (référence à une loi) matche un format proche
   d'un numéro de dossier, mais commence par un petit nombre (15), pas une
   année.
   → Solution : la regex exige un préfixe 19xx ou 20xx (vrai millésime).

5. **Hallucination du LLM**
   Sur un cas, le LLM a renvoyé un numéro (`490/21`) qui n'apparaissait NULLE
   PART dans le texte source.
   → Solution : filet de sécurité (si le LLM est utilisé) vérifiant que sa
     réponse fait bien partie des candidats détectés, sinon rejet automatique.
     Dans la version finale, ce risque est éliminé puisque le LLM n'est plus
     sollicité pour ce choix.

## Pourquoi avoir abandonné le LLM pour ce choix précis ?

Sur les cas testés (jugements, arrêts d'appel, arrêts de Cassation, avec et
sans références à d'autres affaires), la règle déterministe "premier candidat
valide" s'est vérifiée vraie à 100% une fois les faux positifs (dates, lois)
filtrés. Le LLM (Qwen2.5:7b), même avec un prompt détaillé et un exemple
few-shot explicite, se laissait parfois distraire par un numéro plus loin
dans le texte quand celui-ci était mieux reconnu par l'OCR (donc plus "clair"
sémantiquement) que le numéro réel de l'en-tête.

**Conclusion retenue pour le rapport** : pour une tâche avec une règle
positionnelle simple et vérifiable, une approche déterministe (regex + règles)
est plus fiable qu'un LLM, même bien prompté. Le LLM garde son utilité comme
filet de secours pour les cas où aucune règle mécanique ne s'applique.

## Résultats

- 10/10 documents corrects (texte OCR Tesseract), incluant les 5 cas pièges
  décrits ci-dessus.
- Comparaison en cours avec PaddleOCR et EasyOCR (partie OCR, Ghizlane) pour
  vérifier la robustesse de la regex face à des erreurs de reconnaissance de
  chiffres différentes selon le moteur OCR utilisé.

## Limites connues / points de vigilance pour la suite

- La règle "premier candidat = le bon" a été validée empiriquement sur les
  documents testés, mais n'est pas garantie à 100% sur tout type de document
  marocain (à surveiller si de nouveaux formats apparaissent en Phase 3).
- Si l'OCR se trompe sur un CHIFFRE (pas juste sur le texte arabe autour),
  la regex peut ne pas détecter le bon candidat du tout. Ce risque est plus
  élevé si un moteur OCR est nettement moins précis sur les chiffres que
  Tesseract ne l'a été sur notre corpus de test.

## Comparaison entre moteurs OCR (Tesseract vs EasyOCR vs PaddleOCR)

Pour évaluer si le script d'extraction reste fiable quel que soit le moteur
OCR utilisé en amont (partie de Ghizlane), on génère un fichier de résultats
par moteur OCR, en relançant `extraire_numero_dossier()` sur les mêmes 10
documents de test, une fois pour chaque moteur.

### Comment générer un fichier de résultats

Exemple pour un moteur "X" (remplacer le chemin du dossier source) :

```bash
{
  echo "# Résultats extraction numéro de dossier — OCR X"
  echo ""
  echo "| Document | Numéro de dossier extrait |"
  echo "|---|---|"
  for f in data/ocr_output/DOSSIER_DU_MOTEUR/*.txt; do
    nom=$(basename "$f")
    resultat=$(python3 llm/llm_extract.py "$f" | sed 's/Numéro de dossier : //')
    echo "| $nom | $resultat |"
  done
} > llm/resultats/resultats_X.md
```

### Fichiers générés

- `llm/resultats/resultats_tesseract.md` : 10/10 corrects
- `llm/resultats/resultats_easyocr.md` : en cours d'analyse
- `llm/resultats/resultats_paddleocr.md` : à venir (Ghizlane encore en train de le générer)

### Ce qu'on cherche à observer

Le principal risque identifié est que le script dépend de la bonne
reconnaissance des CHIFFRES par l'OCR (la regex ne tolère aucune erreur sur
les chiffres du numéro de dossier, contrairement au texte arabe environnant
où le bruit OCR est toléré). Si un moteur OCR est moins précis que Tesseract
sur les chiffres, le taux de réussite peut baisser même si le texte arabe
global est mieux reconnu.
