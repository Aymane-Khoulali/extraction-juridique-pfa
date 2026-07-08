"""
ocr/extract_text.py

Etape 1 : version de base, Tesseract uniquement.
But : PDF (arabe, scanné) -> texte brut.
"""

from pdf2image import convert_from_path
import pytesseract


def pdf_vers_texte(chemin_pdf: str) -> str:
    """
    Prend le chemin d'un PDF et retourne le texte brut extrait (arabe).
    Peu importe comment c'est fait en interne : ça doit TOUJOURS
    retourner une simple chaîne de caractères.
    """
    pages = convert_from_path(chemin_pdf, dpi=300)

    texte_complet = []
    for page in pages:
        texte = pytesseract.image_to_string(page, lang="ara")
        texte_complet.append(texte)

    return "\n".join(texte_complet)


if __name__ == "__main__":
    import sys
    chemin = sys.argv[1] if len(sys.argv) > 1 else "data/samples/cas1.pdf"
    resultat = pdf_vers_texte(chemin)
    print(resultat)