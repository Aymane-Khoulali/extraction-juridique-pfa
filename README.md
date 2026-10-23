
# Arabic Legal Information Extraction 🇲🇦

### Privacy-Preserving OCR & LLM Pipeline for Moroccan Judicial Documents

A Python-based system for extracting structured legal information from Moroccan judicial decisions written in Arabic.

Developed during an academic internship (PFA) at the **Direction de la Modernisation des Systèmes d'Information (DMSI), Moroccan Ministry of Justice**, in July 2026.

The project combines Optical Character Recognition (OCR), a locally deployed Large Language Model (LLM), and deterministic Python validation to process complex judicial documents without relying on external cloud APIs.

## The Problem

Moroccan judicial decisions contain important information buried in long, unstructured Arabic text.

Extracting this information presents several challenges:

- Arabic OCR errors caused by scanned documents and complex layouts.
- Inconsistent document structures across courts and jurisdictions.
- Difficulty distinguishing case identifiers from dates and references to earlier cases.
- LLM hallucinations and incorrect field extraction.
- Privacy constraints that favor local document processing.

**Objective:** Develop a reliable, fully local pipeline for extracting structured legal information from Arabic judicial documents.

## System Architecture

The processing pipeline follows these steps:

1. **Document Input:** Load a scanned judicial decision in PDF format.
2. **OCR:** Convert document images into Arabic text using EasyOCR.
3. **Information Extraction:** Use Qwen2.5:7B through Ollama for fields requiring language understanding.
4. **Deterministic Validation:** Apply Python rules and regular expressions where LLM output is unreliable.
5. **Structured Output:** Return extracted information in JSON format.
6. **User Interface:** Display results through a Streamlit application.

## Extracted Information

The pipeline targets:

- Case number
- Court name
- Judgment panel composition
- Final judicial ruling
- Claimed compensation amount
- Awarded compensation amount

## Technologies

| Component | Technology |
|---|---|
| Programming | Python |
| OCR | EasyOCR, Tesseract, PaddleOCR |
| Local LLM | Qwen2.5:7B |
| Model execution | Ollama |
| Validation | Python, Regular Expressions |
| Interface | Streamlit |
| Output | JSON |
| Version control | Git, GitHub |

## Key Engineering Decisions

### 1. Choosing an OCR Engine

Three OCR engines were evaluated on a corpus of 10 Arabic judicial documents.

| OCR Engine | Successful Case-Number Extractions |
|---|---:|
| Tesseract | 9/10 |
| EasyOCR | 10/10 |
| PaddleOCR | 0/10 |

EasyOCR was selected for the final pipeline based on its performance on this test corpus.

These results are specific to the documents and evaluation method used in this project.

### 2. Combining LLMs with Deterministic Rules

Initial experiments revealed that LLM-based case-number extraction was not consistently reliable.

Observed problems included:

- Confusing case numbers with judgment numbers.
- Selecting identifiers from previously referenced cases.
- Mistaking dates for case identifiers.
- Generating identifiers absent from the source text.

Several prompt-engineering approaches were tested.

Because prompting alone did not resolve these issues consistently, case-number extraction was redesigned using deterministic Python rules.

The final approach uses regular expressions, candidate filtering, and validation safeguards, with the LLM retained as a fallback.

**Result: 10/10 correct case-number extractions on the 10-document test corpus.**

This result demonstrates performance on the evaluated documents; it does not establish accuracy on unseen datasets.

### 3. Privacy-Preserving Local Deployment

The system uses Qwen2.5:7B through Ollama.

Inference runs locally, without sending document contents to an external LLM API.

This design supports privacy-sensitive document processing and reduces dependence on external AI services.

## Project Structure

```text
ocr/          OCR benchmarking and text extraction
llm/          Local LLM prompting and extraction logic
pipeline/     End-to-end processing and validation
interface/    Streamlit demonstration application
requirements.txt
```

## Results

The prototype demonstrated:

- 10/10 correct case-number extractions on the evaluated corpus.
- Extraction of court composition and judicial rulings from the tested documents.
- Separation of claimed and awarded compensation amounts.
- Local LLM inference without external cloud APIs.
- An integrated Streamlit interface for reviewing extraction results.

## Limitations

This project is an academic prototype, not a production-ready judicial information system.

Current limitations include:

- A relatively small evaluation corpus of 10 documents.
- Sensitivity to OCR quality and document formatting.
- Possible extraction errors on unfamiliar document structures.
- Local hardware requirements for running Qwen2.5:7B.
- The need for broader evaluation before deployment.

## Team & Contributions

This project was developed collaboratively by:

**Aymane Khoulali — LLM & Information Extraction**

- Local LLM deployment and integration
- Prompt engineering and structured extraction
- Python validation and hallucination safeguards
- OCR text correction strategies
- Compensation information extraction
- Streamlit interface co-development

**Ghizlane Chahid — OCR & Document Processing**

- OCR engine benchmarking
- Document preprocessing
- Arabic text recognition and extraction
- OCR output evaluation
- Streamlit interface co-development

Both contributors collaborated on pipeline integration, repository organization, and technical documentation.

## Data & Privacy

The project demonstrations use publicly available Moroccan judicial decisions from [mahakim.ma](https://www.mahakim.ma/).

The repository is intended to contain no confidential or non-public judicial documents.

The system is a technical research prototype and should not be used as a substitute for legal review.

## Acknowledgments

Developed during an academic internship at the Moroccan Ministry of Justice, DMSI.

**Professional Supervisor:** Ahmed Ouardi  
**Academic Supervisor:** Hajar El Gadi — International University of Rabat

Special thanks to the DMSI team for their guidance and support.

## Authors

**Aymane Khoulali**  
[GitHub](https://github.com/Aymane-Khoulali) · [LinkedIn](https://www.linkedin.com/in/aymanekhoulali/)

**Ghizlane Chahid**  
OCR development and project collaboration
