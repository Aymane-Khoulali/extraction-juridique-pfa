
# Report — OCR Spelling Correction Module (`corriger_texte.py`)

## Objective

Automatically correct OCR errors in complete Arabic texts (judicial documents), complementing the targeted extraction of the project's four main fields.

## Challenges Encountered

When tested on a real document containing significant OCR noise, the initial module successfully corrected simple errors, such as split words and incorrectly recognized characters.

However, it tended to **hallucinate information** in severely corrupted passages:

| Error Type | Observed Example |
|---|---|
| Invented date | A vague reference ("on the date mentioned above") was replaced with an incorrect date copied from another context in the document. |
| Invented word | A stamp artifact was transformed into a nonexistent Arabic word in an attempt to "repair" the grammar. |
| Merged institutions | The names of two distinct, real institutions were combined into a fictional entity. |

## Implemented Solution

Two improvements were introduced to reduce hallucinations and improve the reliability of the correction process.

### 1. Strengthened Prompt Engineering

The correction prompt was reinforced with strict rules accompanied by concrete counterexamples drawn from previously observed failures.

These examples helped clarify the model's expected behavior and discourage it from inventing information when dealing with ambiguous or corrupted text.

### 2. Automatic Validation Safeguard

An automatic validation mechanism was implemented to detect numerical information, such as dates or identification numbers, introduced during correction but absent from the original document.

When suspicious numerical information is detected:

1. The affected corrected text chunk is rejected.
2. The original, unmodified chunk is preserved.
3. The system prevents the potentially hallucinated information from being included in the final output.

## Results

During subsequent testing, the validation safeguard successfully detected and prevented the invented-date error.

The affected chunk was rejected and replaced with its original version, simultaneously eliminating the incorrect merging of institutions that occurred within the same passage.

However, the isolated invented Arabic word was not detected.

Unlike numerical information, fabricated words are considerably more difficult to identify automatically without additional linguistic validation mechanisms.

## Conclusion

The module is useful for **light to moderate OCR error correction** and for improving the readability of extracted Arabic text during preliminary document review.

However, it should not replace human verification when processing severely corrupted OCR passages, particularly those involving:

- Personal names
- Institution names
- Numerical information
- Sensitive legal references

This limitation is explicitly acknowledged and documented.

It highlights a broader challenge encountered throughout the project: preventing a language model from silently filling gaps in noisy or incomplete text with plausible but fabricated information.

**Key takeaway:** Reliable AI-based document processing requires more than effective prompting. It also requires validation mechanisms, transparent limitations, and human oversight when accuracy is critical.

# Report — OCR Spelling Correction Module (`corriger_texte.py`)

## Objective

Automatically correct OCR errors in complete Arabic texts (judicial documents), complementing the targeted extraction of the project's four main fields.

## Challenges Encountered

When tested on a real document containing significant OCR noise, the initial module successfully corrected simple errors, such as split words and incorrectly recognized characters.

However, it tended to **hallucinate information** in severely corrupted passages:

| Error Type | Observed Example |
|---|---|
| Invented date | A vague reference ("on the date mentioned above") was replaced with an incorrect date copied from another context in the document. |
| Invented word | A stamp artifact was transformed into a nonexistent Arabic word in an attempt to "repair" the grammar. |
| Merged institutions | The names of two distinct, real institutions were combined into a fictional entity. |

## Implemented Solution

Two improvements were introduced to reduce hallucinations and improve the reliability of the correction process.

### 1. Strengthened Prompt Engineering

The correction prompt was reinforced with strict rules accompanied by concrete counterexamples drawn from previously observed failures.

These examples helped clarify the model's expected behavior and discourage it from inventing information when dealing with ambiguous or corrupted text.

### 2. Automatic Validation Safeguard

An automatic validation mechanism was implemented to detect numerical information, such as dates or identification numbers, introduced during correction but absent from the original document.

When suspicious numerical information is detected:

1. The affected corrected text chunk is rejected.
2. The original, unmodified chunk is preserved.
3. The system prevents the potentially hallucinated information from being included in the final output.

## Results

During subsequent testing, the validation safeguard successfully detected and prevented the invented-date error.

The affected chunk was rejected and replaced with its original version, simultaneously eliminating the incorrect merging of institutions that occurred within the same passage.

However, the isolated invented Arabic word was not detected.

Unlike numerical information, fabricated words are considerably more difficult to identify automatically without additional linguistic validation mechanisms.

## Conclusion

The module is useful for **light to moderate OCR error correction** and for improving the readability of extracted Arabic text during preliminary document review.

However, it should not replace human verification when processing severely corrupted OCR passages, particularly those involving:

- Personal names
- Institution names
- Numerical information
- Sensitive legal references

This limitation is explicitly acknowledged and documented.

It highlights a broader challenge encountered throughout the project: preventing a language model from silently filling gaps in noisy or incomplete text with plausible but fabricated information.

**Key takeaway:** Reliable AI-based document processing requires more than effective prompting. It also requires validation mechanisms, transparent limitations, and human oversight when accuracy is critical.
