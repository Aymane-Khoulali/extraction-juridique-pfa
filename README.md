# Extraction Juridique PFA

🇬🇧 [Read in English](README.en.md)

Extraction automatique d'informations juridiques (numéro de dossier, formation de jugement, dispositif, montants d'indemnisation) à partir de décisions judiciaires marocaines rédigées en arabe — combinant OCR et un LLM exécuté localement, dans le cadre d'un stage de fin d'études (PFA) à la Direction de la Modernisation des Systèmes d'Information, Ministère de la Justice.

## Problématique

Les documents judiciaires contiennent des données sensibles et confidentielles qui ne peuvent pas transiter par une API cloud. Ce projet nécessitait un pipeline fonctionnant **100% en local** — aucun appel externe, aucune donnée ne quittant la machine — tout en extrayant de manière fiable des informations structurées à partir de textes juridiques arabes longs et non structurés.

## Approche

Plutôt que de s'appuyer sur un unique appel LLM en "boîte noire", le pipeline combine OCR, LLM local et règles déterministes selon les besoins réels de chaque champ à extraire :

- **OCR** : Comparaison de trois moteurs (Tesseract, EasyOCR, PaddleOCR) sur des documents judiciaires arabes réels, et sélection du plus fiable pour ce type de document.
- **LLM** : Qwen2.5 exécuté localement via Ollama pour les champs nécessitant une compréhension du langage (ex. formation de jugement, dispositif).
- **Règles déterministes** : Pour les champs où le LLM n'était pas assez fiable — notamment le numéro de dossier — remplacement du LLM par une logique Python basée sur des règles, atteignant une fiabilité de 10/10 sur les documents de test. Savoir reconnaître les limites d'un LLM et le remplacer par une solution plus simple et plus fiable a été l'un des principaux enseignements techniques de ce projet.
- **Interface** : Une application de démonstration Streamlit permettant d'exécuter le pipeline de bout en bout et de visualiser les résultats extraits.

## Structure du projet

```
├── ocr/         # Comparaison des moteurs OCR et extraction de texte à partir des documents scannés
├── llm/         # Logique de prompting et d'extraction avec le LLM local (Qwen2.5 / Ollama)
├── pipeline/    # Orchestration de bout en bout : OCR → LLM → post-traitement par règles
├── interface/   # Application de démonstration Streamlit
└── requirements.txt
```

## Stack technique

Python · Qwen2.5 (via Ollama) · Tesseract / EasyOCR / PaddleOCR · Streamlit

## Résultats

- Extraction du numéro de dossier : fiabilité de **10/10** grâce aux règles déterministes (contre une extraction incohérente avec le LLM seul)
- Pipeline entièrement local — aucun appel API cloud, préservant la confidentialité des données judiciaires
- Extraction réussie du numéro de dossier, de la formation de jugement, du dispositif final et des montants d'indemnisation à partir de documents juridiques arabes réels

## Note sur les données

Toutes les démonstrations et documents de test utilisés dans ce dépôt proviennent de décisions publiquement disponibles sur le portail [mahakim.ma](http://mahakim.ma). Aucune donnée judiciaire confidentielle ou non publique n'est incluse dans ce dépôt.

## Contexte

Projet réalisé en binôme dans le cadre d'un stage de fin d'études (PFA) à la Direction de la Modernisation des Systèmes d'Information (DMSI), Ministère de la Justice, en collaboration avec Ghizlane Chahid, qui a piloté le travail de comparaison des moteurs OCR. Encadré par M. Ahmed Ouardi (DMSI) et Mme Hajar El Gadi (Université Internationale de Rabat).
