# Notes OCR — Phase 1

Trois moteurs OCR ont été testés sur 10 documents réels pour l'extraction du numéro de dossier.

## Résultats

| Moteur | Numéro de dossier | Qualité texte global | Vitesse |
|---|---|---|---|
| **Tesseract** | 9/10 (90%) | Bonne | Rapide |
| **EasyOCR** | 10/10 | Bonne, quelques fautes de frappe | Correcte |
| **PaddleOCR** | 0/10 | Lisible mais sans aucun chiffre | Très lente (CPU) |

## PaddleOCR écarté

PaddleOCR a été mis de côté après test : le modèle de reconnaissance arabe utilisé
(`arabic_PP-OCRv5_mobile_rec`) ne détecte **aucun chiffre** dans les documents,
alors que les numéros de dossier, dates et références légales sont essentiels
pour ce projet.

Exemple sur `doc1.pdf` (extrait PaddleOCR) :
> "القردر عرو / الصاور بتاريغيرليوز / في الف لمرني عر"

Comparer avec Tesseract sur le même document :
> "القرار عرو 511 الصادر بتاريغ 06 يجوز 2021 اللف الرني عرو 2020/9/1/1711"

Le numéro de dossier (`2020/9/1/1711`) et la date sont complètement absents
de la sortie PaddleOCR, alors qu'ils sont bien présents (même imparfaitement)
avec Tesseract et EasyOCR.

Ce problème persiste même avec l'orientation des lignes de texte activée,
et le temps de traitement (plusieurs minutes par document sur CPU) rend
PaddleOCR peu adapté à ce projet de toute façon.

**Décision : PaddleOCR n'est pas retenu pour la suite du projet.**
Le script `ocr/run_all_paddle.py` est conservé dans le repo à titre de
documentation/traçabilité, mais n'est plus utilisé activement.

## Choix final : EasyOCR

Malgré un score très proche de Tesseract sur le numéro de dossier (10/10
contre 9/10), **EasyOCR a été retenu comme moteur officiel du projet**, et
c'est `pdf_vers_texte_easyocr` (dans `run_all_easyocr.py`) qui est utilisé
par le pipeline complet (`pipeline/main.py`) et par le module LLM pour
toutes les extractions (numéro de dossier, هيئة, منطوق).

`extract_text.py` (Tesseract) reste dans le repo comme référence/comparatif
historique, mais n'est plus la version utilisée en production.

## Fichiers

- `run_all_easyocr.py` — **version officielle** (EasyOCR), utilisée par le
  pipeline et le LLM ; contient `pdf_vers_texte_easyocr()` ainsi qu'un mode
  batch qui traite tous les PDF de `data/samples/`
- `extract_text.py` — version de référence (Tesseract), conservée pour
  comparaison, non utilisée en production
- `run_all_paddle.py` — conservé pour trace, non utilisé (voir ci-dessus)

## Explication technique du code

### `extract_text.py` (Tesseract)

```python
def pdf_vers_texte(chemin_pdf: str) -> str:
    pages = convert_from_path(chemin_pdf, dpi=300)
    texte_complet = []
    for page in pages:
        texte = pytesseract.image_to_string(page, lang="ara")
        texte_complet.append(texte)
    return "\n".join(texte_complet)
```

Convertit chaque page du PDF en image (300 DPI), puis applique l'OCR
Tesseract avec le pack de langue arabe (`lang="ara"`) page par page. Les
résultats sont concaténés en une seule chaîne de texte.

### `run_all_easyocr.py` (EasyOCR)

```python
_reader = easyocr.Reader(["ar"], gpu=False)

def pdf_vers_texte_easyocr(chemin_pdf):
    pages = convert_from_path(chemin_pdf, dpi=200)
    texte_pages = []
    for page in pages:
        lignes = _reader.readtext(np.array(page), detail=0, paragraph=True)
        texte_pages.append("\n".join(lignes))
    return "\n".join(texte_pages)
```

Le `easyocr.Reader(["ar"], gpu=False)` est chargé UNE SEULE FOIS au niveau
du module (pas à chaque appel), pour éviter de recharger le modèle à
chaque document traité. Chaque page est convertie en tableau numpy
(format attendu par EasyOCR), puis `readtext(..., paragraph=True)`
regroupe automatiquement les lignes proches en paragraphes cohérents.

Le fichier contient aussi un mode "batch" (`main()`) qui traite
automatiquement tous les PDF de `data/samples/` et sauvegarde chaque
résultat dans `data/ocr_output/easyOCR_output/<nom>_easyocr.txt`.
