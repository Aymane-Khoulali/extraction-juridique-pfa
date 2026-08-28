"""
interface/app_streamlit.py

Interface Streamlit pour la demo du pipeline OCR + LLM.
Upload d'un PDF -> traitement via pipeline/main.py -> affichage des resultats.

Usage :
    pip3 install streamlit
    streamlit run interface/app_streamlit.py

Un onglet s'ouvre automatiquement dans le navigateur.
"""

import os
import sys
import time
import tempfile

import streamlit as st

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "pipeline"))

from main import traiter_document

st.set_page_config(
    page_title="Extraction Juridique - Demo PFA",
    page_icon="📄",
    layout="centered",
)

# ---------- Style ----------
st.markdown("""
<style>
    .eyebrow {
        font-size: 12px; letter-spacing: 1.5px; text-transform: uppercase;
        color: #C9A24B; font-weight: 600; margin-bottom: 4px;
    }
    .titre-principal { color: #1F3864; margin-bottom: 0; }
    .sous-titre { color: #6B6B6B; font-size: 14px; margin-top: 4px; }
    .champ-label {
        font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;
        color: #6B6B6B; margin-bottom: 6px; margin-top: 18px;
    }
    .arabe {
        direction: rtl; text-align: right; font-size: 17px; line-height: 2;
        background: #FAFAF7; border: 1px solid #E3E1D9; border-radius: 8px;
        padding: 14px 18px;
    }
    .numero-dossier {
        direction: rtl; text-align: right; font-size: 24px; font-weight: 700;
        color: #1F3864;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
st.markdown('<div class="eyebrow">Direction de la Modernisation des Systèmes Informatiques</div>', unsafe_allow_html=True)
st.markdown('<h1 class="titre-principal">Extraction automatique d\'informations juridiques</h1>', unsafe_allow_html=True)
st.markdown('<p class="sous-titre">OCR (EasyOCR) + LLM local (Qwen2.5:7b) — Démonstration Stage PFA</p>', unsafe_allow_html=True)
st.divider()

# ---------- Upload ----------
fichier = st.file_uploader(
    "Sélectionnez un document PDF (décision de justice scannée, en arabe)",
    type=["pdf"],
)

if fichier is not None:
    if st.button("Analyser le document", type="primary", use_container_width=True):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(fichier.getvalue())
            chemin_pdf = tmp.name

        debut = time.time()
        try:
            with st.spinner("Traitement en cours (OCR puis extraction LLM)... cela peut prendre 1 à 2 minutes."):
                resultat = traiter_document(chemin_pdf)
            duree = round(time.time() - debut, 1)

            st.success(f"Analyse terminée en {duree}s")

            # --- Numero de dossier ---
            st.markdown('<div class="champ-label">رقم الملف — Numéro de dossier</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="numero-dossier">{resultat["numero_dossier"]}</div>', unsafe_allow_html=True)

            # --- Haia ---
            st.markdown('<div class="champ-label">الهيئة — Composition du collège de juges</div>', unsafe_allow_html=True)
            haia = resultat.get("haia", {})
            lignes_haia = [f"<strong>رئيسا ومقررا :</strong> {haia.get('president_rapporteur') or '—'}"]
            for i, nom in enumerate(haia.get("assesseurs", []), 1):
                lignes_haia.append(f"<strong>عضو ({i}) :</strong> {nom}")
            lignes_haia.append(f"<strong>كاتب الضبط :</strong> {haia.get('greffier') or '—'}")
            lignes_haia.append(f"<strong>المحامي العام :</strong> {haia.get('procureur') or '—'}")
            st.markdown(f'<div class="arabe">{"<br>".join(lignes_haia)}</div>', unsafe_allow_html=True)

            # --- Mantouk ---
            st.markdown('<div class="champ-label">المنطوق — Dispositif final</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="arabe">{resultat["mantouk"]}</div>', unsafe_allow_html=True)

            with st.expander("Voir les données brutes (JSON)"):
                st.json(resultat)

        except Exception as e:
            st.error(f"Erreur pendant le traitement : {e}")
        finally:
            os.remove(chemin_pdf)

st.markdown(
    '<p style="text-align:center;color:#6B6B6B;font-size:12px;margin-top:40px;">'
    "Démonstration interne — Stage PFA, Aymane Khoulali &amp; Ghizlane</p>",
    unsafe_allow_html=True,
)