"""
interface/app.py

Interface web simple pour la demo du pipeline OCR + LLM.
Upload d'un PDF -> traitement via pipeline/main.py -> affichage des resultats.

Usage :
    cd extraction-juridique-pfa
    pip3 install flask
    python3 interface/app.py

Puis ouvrir http://localhost:5000 dans le navigateur.
"""

import os
import sys
import time
from flask import Flask, request, render_template, redirect, url_for, flash

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "pipeline"))

from main import traiter_document

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "demo-pfa-extraction-juridique"
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 Mo max


@app.route("/", methods=["GET"])
def accueil():
    return render_template("index.html")


@app.route("/analyser", methods=["POST"])
def analyser():
    fichier = request.files.get("pdf")

    if not fichier or fichier.filename == "":
        flash("Merci de choisir un fichier PDF.")
        return redirect(url_for("accueil"))

    if not fichier.filename.lower().endswith(".pdf"):
        flash("Le fichier doit etre un PDF.")
        return redirect(url_for("accueil"))

    nom_sûr = f"{int(time.time())}_{fichier.filename}"
    chemin_pdf = os.path.join(UPLOAD_DIR, nom_sûr)
    fichier.save(chemin_pdf)

    debut = time.time()
    try:
        resultat = traiter_document(chemin_pdf)
        erreur = None
    except Exception as e:
        resultat = None
        erreur = str(e)
    duree = round(time.time() - debut, 1)

    return render_template(
        "resultat.html",
        resultat=resultat,
        erreur=erreur,
        duree=duree,
        nom_fichier=fichier.filename,
    )


if __name__ == "__main__":
    print("Interface disponible sur http://localhost:5000")
    app.run(debug=True, port=5000)