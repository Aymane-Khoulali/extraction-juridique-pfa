
# Technical Notes — Complete Processing Pipeline

## Objective

Integrate the project's two main components into a single executable workflow:

1. **OCR (Ghizlane):** PDF document → raw Arabic text
2. **LLM (Aymane):** Raw Arabic text → structured information (case number, judgment panel composition, and final judicial ruling)

The goal is to process a judicial document through both components using a single command.

## How `pipeline/main.py` Works

### Dynamic Module Imports

```python
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "ocr"))
sys.path.insert(0, os.path.join(RACINE, "llm"))
```

This section calculates the absolute path to the project's root directory, regardless of where the script is executed.

It then adds the `ocr/` and `llm/` directories to Python's module search path.

This allows the script to import functions directly:

```python
from run_all_easyocr import pdf_vers_texte_easyocr
from llm_extract import extraire_numero_dossier, extraire_haia, extraire_mantouk
```

Without requiring these directories to be structured as standard Python packages.

In particular, no `__init__.py` files are necessary.

This approach provides a straightforward solution for a small project developed by two contributors.

### Main Function — `traiter_document(chemin_pdf)`

```python
def traiter_document(chemin_pdf: str) -> dict:
    texte = pdf_vers_texte_easyocr(chemin_pdf)   # OCR step
    numero = extraire_numero_dossier(texte)       # Extraction step 1
    haia = extraire_haia(texte)                   # Extraction step 2
    mantouk = extraire_mantouk(texte)              # Extraction step 3
    return {...}
```

The function sequentially calls the OCR and extraction functions that were previously developed and tested independently.

The pipeline itself does not introduce additional processing logic.

Instead, it acts as an **orchestration layer**, connecting the existing modules into a complete workflow.

The main implementation complexity remains within the individual `ocr/` and `llm/` components.

### Why This Modular Architecture Matters

Each function, including:

- `pdf_vers_texte_easyocr()`
- `extraire_numero_dossier()`
- `extraire_haia()`
- `extraire_mantouk()`

Can be tested, maintained, and improved independently.

This separation allows each contributor to modify their respective component without disrupting the complete pipeline.

As long as each function maintains a consistent input/output interface, the overall workflow remains functional.

This design improves:

- **Modularity:** OCR and LLM components remain separate.
- **Maintainability:** Individual functions can be updated independently.
- **Testability:** Each processing stage can be evaluated separately.
- **Collaboration:** Contributors can work on different components without interfering with one another.

## Required Dependencies

The complete pipeline requires the dependencies of **both the OCR and LLM components** to be installed on the same machine.

### Python Dependencies

- `numpy`
- `easyocr`
- `pdf2image`
- `requests`

### Local LLM Requirements

Ollama must be installed and running in the background:

```bash
ollama serve
```

The following model must already be downloaded:

```bash
ollama pull qwen2.5:7b
```

The model is executed locally through Ollama, allowing the pipeline to process documents without using an external LLM API.

## Usage

Run the complete pipeline using:

```bash
python3 pipeline/main.py path/to/document.pdf
```

The script processes the input PDF through the following stages:

1. Convert the PDF into images.
2. Extract Arabic text using EasyOCR.
3. Extract the case number.
4. Extract the judgment panel composition.
5. Extract the final judicial ruling.
6. Return the extracted information as structured data.

## Known Limitation

### Slower Initial Execution

The first execution may take longer because EasyOCR needs to load its recognition models into memory.

The OCR reader is initialized only once at the module level inside `ocr/run_all_easyocr.py`:

```python
easyocr.Reader(...)
```

Rather than being initialized every time an OCR function is called.

This reduces repeated model-loading overhead when processing multiple documents within the same Python process.

## Conclusion

The complete pipeline connects independently developed OCR and LLM components into a single executable workflow.

Its modular design enables the OCR and information-extraction stages to be developed, tested, and maintained separately while remaining integrated through a common interface.

**Key takeaway:** A simple orchestration layer can effectively combine complex processing modules without introducing unnecessary dependencies or tightly coupling their internal implementations.

