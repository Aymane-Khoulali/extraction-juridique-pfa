
# OCR Technical Notes — Phase 1

Three OCR engines were evaluated on 10 real judicial documents to assess their ability to extract case numbers.

## Results

| OCR Engine | Case Number Extraction | Overall Text Quality | Processing Speed |
|---|---|---|---|
| **Tesseract** | 9/10 (90%) | Good | Fast |
| **EasyOCR** | 10/10 (100%) | Good, with minor recognition errors | Moderate |
| **PaddleOCR** | 0/10 (0%) | Readable, but numerical characters were missing | Very slow (CPU) |

## Why PaddleOCR Was Discarded

PaddleOCR was excluded after testing because the Arabic recognition model used (`arabic_PP-OCRv5_mobile_rec`) failed to recognize **any numerical characters** in the evaluated documents.

This was a critical limitation because case numbers, dates, and legal references are essential to the project's information extraction objectives.

### Example — `doc1.pdf`

**PaddleOCR output:**

> القردر عرو / الصاور بتاريغيرليوز / في الف لمرني عر

**Tesseract output for the same document:**

> القرار عرو 511 الصادر بتاريغ 06 يجوز 2021 اللف الرني عرو 2020/9/1/1711

The case number (`2020/9/1/1711`) and the date are completely missing from PaddleOCR's output.

In contrast, Tesseract and EasyOCR successfully preserve this numerical information, even when other parts of the extracted text contain recognition errors.

The issue persisted even after enabling text-line orientation detection.

Additionally, processing took several minutes per document on CPU, making PaddleOCR impractical for this project's requirements.

**Final decision:** PaddleOCR was not selected for further use.

The `ocr/run_all_paddle.py` script remains in the repository for documentation and traceability purposes but is no longer actively used.

## Final Selection — EasyOCR

Although Tesseract achieved a comparable result for case-number extraction (9/10 versus EasyOCR's 10/10), **EasyOCR was selected as the project's primary OCR engine**.

The `pdf_vers_texte_easyocr()` function, implemented in `run_all_easyocr.py`, is used by the complete processing pipeline (`pipeline/main.py`) and provides the text required for downstream extraction tasks, including:

- Case numbers (رقم الملف)
- Judgment panel composition (الهيئة)
- Final judicial rulings (المنطوق)

The `extract_text.py` script, based on Tesseract, remains in the repository as a historical reference and comparison implementation.

It is no longer used by the final pipeline.

## Project Files

### `run_all_easyocr.py`

**Primary OCR implementation — EasyOCR**

- Used by the complete processing pipeline and LLM components.
- Contains the `pdf_vers_texte_easyocr()` function.
- Includes a batch-processing mode that automatically processes all PDFs in `data/samples/`.

### `extract_text.py`

**Reference implementation — Tesseract**

- Preserved for comparison and documentation.
- Not used by the final processing pipeline.

### `run_all_paddle.py`

**Experimental implementation — PaddleOCR**

- Preserved for traceability.
- No longer actively used due to the limitations described above.

---

## Technical Code Explanation

### 1. `extract_text.py` — Tesseract

```python
def pdf_vers_texte(chemin_pdf: str) -> str:
    pages = convert_from_path(chemin_pdf, dpi=300)
    texte_complet = []
    for page in pages:
        texte = pytesseract.image_to_string(page, lang="ara")
        texte_complet.append(texte)
    return "\n".join(texte_complet)
```

#### How It Works

1. **PDF conversion:** Each page is converted into an image at 300 DPI using `convert_from_path()`.
2. **Arabic OCR:** Tesseract processes each image using the Arabic language pack (`lang="ara"`).
3. **Text collection:** The extracted text from each page is stored in a list.
4. **Output:** All page results are concatenated into a single string, separated by newline characters.

This approach processes the document page by page and produces a complete text representation of the original PDF.

### 2. `run_all_easyocr.py` — EasyOCR

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

#### How It Works

**1. Initialize the OCR model**

```python
_reader = easyocr.Reader(["ar"], gpu=False)
```

The EasyOCR reader is initialized **only once at the module level**, rather than every time the function is called.

This avoids repeatedly loading the recognition model for each processed document.

The configuration specifies:

- `["ar"]`: Arabic language recognition.
- `gpu=False`: CPU-based execution.

**2. Convert PDF pages into images**

```python
pages = convert_from_path(chemin_pdf, dpi=200)
```

Each PDF page is converted into an image at 200 DPI.

**3. Convert images into NumPy arrays**

```python
np.array(page)
```

Each page image is converted into a NumPy array, the input format expected by EasyOCR.

**4. Extract and group text**

```python
_reader.readtext(np.array(page), detail=0, paragraph=True)
```

The parameters control the extraction behavior:

- `detail=0`: Return only recognized text, without bounding boxes or confidence scores.
- `paragraph=True`: Automatically group nearby text lines into coherent paragraphs.

**5. Combine extracted text**

The recognized paragraphs from each page are joined together, producing a single text output for the complete document.

## Batch Processing

The `run_all_easyocr.py` file also includes a batch-processing mode implemented through its `main()` function.

This mode:

1. Reads all PDF documents from `data/samples/`.
2. Processes each document using EasyOCR.
3. Extracts and combines the recognized Arabic text.
4. Saves each result as a text file in:

```text
data/ocr_output/easyOCR_output/<name>_easyocr.txt
```

This automated workflow enables multiple judicial documents to be processed without manually executing OCR for each individual file.

## Conclusion

EasyOCR was selected as the primary OCR engine because it achieved the best case-number extraction performance on the evaluated corpus while maintaining acceptable text quality and processing speed.

Tesseract remains a useful reference implementation, whereas PaddleOCR was excluded due to its inability to preserve numerical information in the tested documents and its high CPU processing time.

**Important limitation:** These findings are based on a corpus of 10 judicial documents and the specific model configurations tested. They should not be interpreted as a general performance ranking of the three OCR engines across all Arabic documents.
