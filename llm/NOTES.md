# Notes techniques — Extraction du numéro de dossier (LLM)

## Objectif

Extraire automatiquement le numéro de dossier (رقم الملف) à partir du texte OCR
brut d'une décision de justice marocaine en arabe, quel que soit le tribunal ou
le type de document (jugement de 1ère instance, arrêt d'appel, arrêt de Cassation).

## Approche finale retenue

Texte OCR → regex (détection de candidats plausibles) → premier candidat = réponse.

Le LLM (Qwen2.5:7b via Ollama) n'est utilisé qu'en tout dernier recours, si la
regex ne détecte aucun candidat. Il n'est plus utilisé pour choisir entre
plusieurs candidats — voir la section "Pourquoi" ci-dessous.

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

## Résultats par moteur OCR

Le script `extraire_numero_dossier()` a été testé sur les mêmes 10 documents,
avec le texte OCR produit par différents moteurs (partie de Ghizlane) :

- **Tesseract** : 10/10 numéros de dossier corrects.
- **EasyOCR** : 10/10 numéros de dossier corrects.
- **PaddleOCR** : à venir.

Fait notable : sur le document 4, le texte brut produit par Tesseract et celui
produit par EasyOCR différaient (erreur de lecture OCR différente selon le
moteur sur ce document précis), mais dans les deux cas le script a quand même
réussi à extraire le bon numéro de dossier. Cela suggère que la règle
"premier candidat valide" reste robuste même face à des variations de qualité
OCR d'un moteur à l'autre, tant que les chiffres du numéro de dossier lui-même
restent lisibles.

### Comment régénérer un fichier de résultats pour un nouveau moteur OCR

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

Fichiers déjà générés : `llm/resultats/resultats_tesseract.md`,
`llm/resultats/resultats_easyocr.md`. À venir : `resultats_paddleocr.md`.

## Limites connues / points de vigilance pour la suite

- La règle "premier candidat = le bon" a été validée empiriquement sur les
  documents testés, mais n'est pas garantie à 100% sur tout type de document
  marocain (à surveiller si de nouveaux formats apparaissent en Phase 3).
- Si l'OCR se trompe sur un CHIFFRE (pas juste sur le texte arabe autour),
  la regex peut ne pas détecter le bon candidat du tout. Ce risque est plus
  élevé si un moteur OCR est nettement moins précis sur les chiffres que
  Tesseract et EasyOCR ne l'ont été sur notre corpus de test.

### Résultat observé (Tesseract vs EasyOCR)

- **Tesseract** : 10/10 numéros de dossier corrects.
- **EasyOCR** : 10/10 numéros de dossier corrects également.
- Fait notable : sur le document 4, le texte brut produit par Tesseract et
  celui produit par EasyOCR différaient (erreur de lecture OCR différente
  selon le moteur sur ce document précis), mais dans les deux cas le script
  a quand même réussi à extraire le bon numéro de dossier. Cela suggère que
  la règle "premier candidat valide" reste robuste même face à des
  variations de qualité OCR d'un moteur à l'autre, tant que les chiffres du
  numéro de dossier lui-même restent lisibles.

## Extraction الهيئة (bench) et المنطوق (dispositif) - Phase 3

### Approche

Comme pour le numéro de dossier, on isole d'abord une fenêtre de texte pertinente
en Python (recherche d'ancres textuelles comme "الهيئة الحاكمة" ou "مؤلفة من
السادة") avant de la donner au LLM, plutôt que de donner tout le document. Ça
évite que le LLM confonde les juges du panel avec d'autres noms cités ailleurs
(avocats, parties, juges d'affaires antérieures).

### Découvertes importantes

- La position de la composition du collège varie selon le type de juridiction :
  en en-tête pour un tribunal/cour d'appel, en FIN de document pour un arrêt de
  Cassation (après le dispositif final).
- Un panel de Cassation "بغرفتين" (deux chambres réunies) peut compter 6+ juges
  assesseurs, contre 1-2 pour un tribunal normal. Le schéma d'extraction utilise
  donc une liste de taille variable (`assesseurs: []`), pas des champs fixes.
- Le greffier n'est pas toujours annoncé par le mot-clé exact "كاتب الضبط" - il
  peut être introduit simplement par "بمساعدة" (assisté de), qu'il faut aussi
  détecter.

### Limite connue : noms fusionnés par perte de ponctuation OCR

Quand la liste des juges est dense (formation à 6+ membres), l'OCR (EasyOCR
testé ici) perd parfois la ponctuation de séparation entre deux noms consécutifs
(tiret ou virgule manquant). Le LLM reçoit alors deux noms accolés sans aucun
séparateur visible et ne peut pas deviner où couper - ce n'est pas récupérable
par prompt engineering, c'est une perte d'information en amont (qualité OCR).

### Limite connue : correction orthographique partielle

Sur des mots très abîmés par l'OCR (ex: "بمسا اعدة" au lieu de "بمساعدة", "ىيدة"
au lieu de "السيدة"), le LLM (Qwen2.5:7b) parvient à repérer correctement le bon
passage et la bonne personne, mais ne corrige pas toujours l'orthographe du nom
lui-même dans sa sortie. La localisation de l'information prime sur la
correction esthétique du texte, qui reste imparfaite avec un modèle de cette
taille sur du bruit OCR sévère.

## Bilan final Phase 3 (الهيئة + المنطوق) - EasyOCR

Après plusieurs itérations de correction (ancres multiples pour الهيئة selon
le type de juridiction, distinction label-de-rôle vs vrai nom avec garde-fou
Python, verbes de décision spécifiques pour éviter la confusion avec la
demande d'une partie, instruction "ne rien omettre" pour éviter que le LLM
ne saute le verbe de décision + nom du tribunal en croyant "nettoyer" une
clause procédurale) :

- **رقم الملف** : fiable à 100% (règle déterministe).
- **الهيئة** : extraction correcte sur tous les documents testés ; les champs
  vides correspondent à une absence réelle de l'information dans le texte
  source (ex: extraits de recueils de jurisprudence qui omettent parfois
  cette section), pas à des erreurs d'extraction.
- **المنطوق** : le bon passage est systématiquement repéré et complet (plus
  de troncature ni d'omission du verbe de décision). Reste une limite
  mineure : quelques fautes d'orthographe résiduelles sur des mots très
  abîmés par l'OCR, qui ne remettent pas en cause le sens ni la complétude
  du dispositif extrait.

Difficultés clés résolues durant cette phase :
1. Confusion entre "لهذه الأسباب" introduisant la demande d'une partie et
   celui introduisant la vraie décision du tribunal -> recherche de verbes
   de décision spécifiques au tribunal (حكمت/قضت/تصرح/قررت + nom de la cour).
2. Le LLM recopiait parfois le label de rôle (ex: "رئيسا ومقررا") comme si
   c'était le nom de la personne, quand le nom était sur la ligne suivante ->
   garde-fou Python qui détecte et vide ces faux positifs après l'appel LLM.
3. Instruction trop nuancée sur "ignorer la clause procédurale" a conduit le
   LLM à sauter le verbe de décision et le nom du tribunal par excès de zèle
   -> remplacée par une instruction stricte "tout garder, rien omettre".

## Module complémentaire : correction orthographique du texte complet (corriger_texte.py)

En complément des 4 champs extraits (numéro de dossier, tribunal, هيئة,
منطوق), un module séparé a été développé pour corriger l'orthographe de
l'ensemble d'un texte OCR, utile pour une relecture humaine du document
complet plutôt que des champs isolés.

### Approche

Le texte est découpé en morceaux (~2500 caractères, coupés aux sauts de
ligne/espaces pour ne pas trancher un mot), chaque morceau étant corrigé
séparément par le LLM avant réassemblage.

### Problème identifié lors des premiers tests

Sur du texte fortement abîmé par l'OCR, le modèle ne se contentait pas de
corriger les fautes : il **inventait** parfois du contenu plausible mais faux
pour "faire fonctionner" la phrase. Trois cas concrets observés :
1. Une référence vague ("à la date mentionnée ci-dessus") remplacée par une
   date précise mais fausse, recopiée d'un tout autre contexte du document.
2. Un mot arabe inventé (qui n'existe pas dans la langue) créé pour combler
   un artefact de tampon au lieu de simplement le retirer.
3. Deux noms d'institutions réelles et distinctes fusionnées en une entité
   fictive qui n'existe pas.

### Corrections apportées

1. **Prompt renforcé** avec 5 règles strictes, chacune illustrée par un
   contre-exemple réel tiré des échecs observés (plus efficace qu'une règle
   abstraite, comme constaté sur d'autres parties du projet).
2. **Garde-fou automatique** : toute séquence numérique (3 chiffres ou plus)
   apparaissant dans le texte corrigé mais absente de l'intégralité du
   document original est détectée ; le morceau concerné est alors rejeté et
   la version originale (non corrigée) est conservée à la place.

### Résultat après correction

Sur le même document de test, le garde-fou a détecté et neutralisé le
problème de date inventée : le morceau concerné a été automatiquement rejeté
et remplacé par sa version d'origine, ce qui a éliminé par la même occasion
la fusion d'institutions fictive (présente dans le même morceau).

Le mot arabe inventé (cas n°2), présent dans un autre morceau sans nombre
suspect, n'a en revanche pas été intercepté : aucun garde-fou mécanique
équivalent n'existe pour détecter un mot inventé isolé (contrairement à un
nombre absent du document, un mot arabe fabriqué n'est pas trivialement
détectable sans un dictionnaire de référence).

### Limite connue

Ce module reste donc utile pour une relecture rapide et pour corriger le
bruit OCR léger à modéré, mais ne doit pas être considéré comme une source
de vérité fiable à 100% sur des passages très abîmés, en particulier pour
les noms propres, institutions et références numériques - une vérification
humaine reste recommandée sur les passages sensibles.
