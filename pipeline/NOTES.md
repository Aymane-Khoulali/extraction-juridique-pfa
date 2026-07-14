# Notes techniques — Pipeline complet

## Objectif

Relier en une seule commande les deux briques du projet :
1. OCR (Ghizlane) : PDF -> texte brut arabe
2. LLM (Aymane) : texte brut -> données structurées (numéro de dossier,
   composition du collège de juges, dispositif final)

## Fonctionnement du script `pipeline/main.py`

### Import dynamique des modules

```python
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "ocr"))
sys.path.insert(0, os.path.join(RACINE, "llm"))
```

Cette section calcule le chemin absolu de la racine du projet (peu importe
d'où le script est lancé), puis ajoute les dossiers `ocr/` et `llm/` à la
liste des emplacements où Python cherche les modules à importer. Ça permet
d'écrire simplement :

```python
from run_all_easyocr import pdf_vers_texte_easyocr
from llm_extract import extraire_numero_dossier, extraire_haia, extraire_mantouk
```

sans avoir à transformer ces dossiers en vrais "packages" Python (pas de
fichier `__init__.py` nécessaire) - plus simple pour un petit projet à deux.

### La fonction principale `traiter_document(chemin_pdf)`

```python
def traiter_document(chemin_pdf: str) -> dict:
    texte = pdf_vers_texte_easyocr(chemin_pdf)   # étape OCR
    numero = extraire_numero_dossier(texte)       # étape LLM 1
    haia = extraire_haia(texte)                   # étape LLM 2
    mantouk = extraire_mantouk(texte)              # étape LLM 3
    return {...}
```

Elle enchaîne simplement les fonctions déjà développées et testées
séparément par chacun, sans aucune logique supplémentaire - le pipeline
n'est qu'un "assemblage", toute la complexité réside dans les modules
`ocr/` et `llm/` eux-mêmes.

### Pourquoi ce découpage est important

Chaque fonction (`pdf_vers_texte_easyocr`, `extraire_numero_dossier`, etc.)
peut continuer à être testée et améliorée indépendamment par chacun, sans
casser le pipeline global - tant que la signature (entrée/sortie) de chaque
fonction reste stable, le pipeline continue de fonctionner.

## Dépendances requises

Le pipeline nécessite TOUTES les dépendances des deux parties (OCR ET LLM)
sur la même machine : `numpy`, `easyocr`, `pdf2image`, `requests`, ainsi
qu'Ollama actif en arrière-plan (`ollama serve`) avec le modèle `qwen2.5:7b`
déjà téléchargé.

## Utilisation

```bash
python3 pipeline/main.py chemin/vers/document.pdf
```

## Limite connue

Le tout premier appel est plus lent car EasyOCR charge ses modèles de
reconnaissance en mémoire (`easyocr.Reader(...)`, initialisé une seule fois
au niveau du module `ocr/run_all_easyocr.py`, pas à chaque appel de fonction).
