# Extraction Juridique PFA

🇫🇷 [Lire en français](README.md)

Automatic extraction of legal information (case number, judgment panel composition, ruling, compensation amounts) from Moroccan judicial decisions written in Arabic — combining OCR and a locally-run LLM, built during a final-year internship (PFA) at the Directorate of Information Systems Modernization, Ministry of Justice (Morocco).

## Problem

Judicial documents contain sensitive, confidential data that cannot be sent to a cloud-based API. This project needed a pipeline that runs **100% locally** — no external calls, no data leaving the machine — while still extracting structured information reliably from long, unstructured Arabic legal text.

## Approach

Rather than relying on a single "black box" LLM call, the pipeline combines OCR, a local LLM, and deterministic rule-based logic depending on what each field actually needs:

- **OCR**: Benchmarked three engines (Tesseract, EasyOCR, PaddleOCR) on real Arabic judicial documents and selected the most reliable one for this document type.
- **LLM**: Runs Qwen2.5 locally via Ollama for fields that require language understanding (e.g. judgment panel composition, rulings).
- **Deterministic rules**: For fields where LLM output wasn't reliable enough — most notably case numbers — replaced the LLM with rule-based Python logic, achieving 10/10 reliability on test documents. Recognizing where an LLM is the wrong tool, and using something simpler and more reliable instead, was one of the main engineering takeaways from this project.
- **Interface**: A Streamlit demo app to run the pipeline end-to-end and inspect extracted results.

## Project structure

```
├── ocr/         # OCR engine comparison and text extraction from scanned documents
├── llm/         # Local LLM (Qwen2.5 / Ollama) prompting and extraction logic
├── pipeline/    # End-to-end orchestration: OCR → LLM → rule-based post-processing
├── interface/   # Streamlit demo application
└── requirements.txt
```

## Tech stack

Python · Qwen2.5 (via Ollama) · Tesseract / EasyOCR / PaddleOCR · Streamlit

## Results

- Case number extraction: **10/10** reliability using deterministic rules (vs. inconsistent LLM-only extraction)
- Fully local pipeline — no cloud API calls, preserving confidentiality of judicial data
- Successfully extracts case number, judgment panel composition, final ruling, and compensation amounts from real-world Arabic legal documents

## Data note

All demonstrations and test documents used in this repository are publicly available decisions from the [mahakim.ma](http://mahakim.ma) portal. No confidential or non-public judicial data is included in this repository.

## Context

Built as a two-person final-year internship (PFA) project at the Directorate of Information Systems Modernization (DMSI), Ministry of Justice, Morocco, in collaboration with Ghizlane Chahid, who led the OCR benchmarking work. Supervised by Ahmed Ouardi (DMSI) and Hajar El Gadi (Université Internationale de Rabat).
