"""
Script pour chercher des mots-clés dans le PDF des règles
"""

import sys
import io
from pathlib import Path

# Fix encodage Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import pdfplumber
    USE_PDFPLUMBER = True
except ImportError:
    import PyPDF2
    USE_PDFPLUMBER = False

def search_in_pdf(pdf_path: Path, keywords: list, context_chars: int = 300):
    """Cherche des mots-clés dans un PDF et affiche le contexte"""

    print(f"📖 Recherche dans : {pdf_path.name}")
    print(f"🔍 Mots-clés : {', '.join(keywords)}")
    print("="*80)

    if USE_PDFPLUMBER:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""

                # Chercher chaque mot-clé
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    text_lower = text.lower()

                    if keyword_lower in text_lower:
                        # Trouver toutes les occurrences
                        pos = 0
                        while True:
                            pos = text_lower.find(keyword_lower, pos)
                            if pos == -1:
                                break

                            # Extraire le contexte
                            start = max(0, pos - context_chars)
                            end = min(len(text), pos + len(keyword) + context_chars)
                            context = text[start:end]

                            # Remplacer les retours à la ligne multiples
                            context = ' '.join(context.split())

                            print(f"\n📍 Page {page_num} - Mot-clé: '{keyword}'")
                            print("-"*80)
                            print(f"...{context}...")
                            print("-"*80)

                            pos += len(keyword)
    else:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""

                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    text_lower = text.lower()

                    if keyword_lower in text_lower:
                        pos = 0
                        while True:
                            pos = text_lower.find(keyword_lower, pos)
                            if pos == -1:
                                break

                            start = max(0, pos - context_chars)
                            end = min(len(text), pos + len(keyword) + context_chars)
                            context = text[start:end]
                            context = ' '.join(context.split())

                            print(f"\n📍 Page {page_num} - Mot-clé: '{keyword}'")
                            print("-"*80)
                            print(f"...{context}...")
                            print("-"*80)

                            pos += len(keyword)


if __name__ == "__main__":
    # Chemin du PDF de règles
    pdf_path = Path("D:/IA/MJ-Assistant/Data/Regles/Livre 2 - Le Jeu.pdf")

    if not pdf_path.exists():
        print(f"❌ PDF non trouvé : {pdf_path}")
        sys.exit(1)

    # Mots-clés à rechercher
    keywords = [
        "opposition",
        "Difficulté",
        "Résistance",
        "Test",
        "Réussites",
        "pioche",
        "carte",
        "Tarot des Ombres"
    ]

    search_in_pdf(pdf_path, keywords, context_chars=400)
