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

## Fichiers

- `extract_text.py` — version officielle (Tesseract), utilisée par le LLM
- `extract_text_easyocr.py` — version alternative testée (EasyOCR)
- `run_all.py` / `run_all_easyocr.py` — scripts batch sur les 10 documents de test
- `run_all_paddle.py` — conservé pour trace, non utilisé (voir ci-dessus)