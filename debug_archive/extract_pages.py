"""
Script pour extraire des pages spécifiques du PDF
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

def extract_pages(pdf_path: Path, pages: list):
    """Extrait des pages spécifiques du PDF"""

    print(f"📖 Extraction de pages depuis : {pdf_path.name}")
    print(f"📄 Pages : {pages}")
    print("="*80)

    if USE_PDFPLUMBER:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num in pages:
                if page_num <= len(pdf.pages):
                    page = pdf.pages[page_num - 1]  # 0-indexed
                    text = page.extract_text() or ""

                    print(f"\n{'='*80}")
                    print(f"PAGE {page_num}")
                    print('='*80)
                    print(text)
                else:
                    print(f"⚠️ Page {page_num} n'existe pas (PDF a {len(pdf.pages)} pages)")
    else:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page_num in pages:
                if page_num <= len(reader.pages):
                    page = reader.pages[page_num - 1]
                    text = page.extract_text() or ""

                    print(f"\n{'='*80}")
                    print(f"PAGE {page_num}")
                    print('='*80)
                    print(text)
                else:
                    print(f"⚠️ Page {page_num} n'existe pas (PDF a {len(reader.pages)} pages)")


if __name__ == "__main__":
    pdf_path = Path("D:/IA/MJ-Assistant/Data/Regles/Livre 2 - Le Jeu.pdf")

    if not pdf_path.exists():
        print(f"❌ PDF non trouvé : {pdf_path}")
        sys.exit(1)

    # Extraire les pages contenant les règles sur les Tests et Oppositions
    # D'après la table des matières :
    # - Page 54-55 : Réussir un Test, Difficulté, Résistance
    # - Page 56-60 : Simuler une épreuve, Tester sa Compétence
    # - Page 62-63 : Gérer une opposition active
    pages_to_extract = [54, 55, 56, 57, 58, 59, 60, 62, 63]

    extract_pages(pdf_path, pages_to_extract)
