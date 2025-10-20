"""
Script pour vérifier la qualité de l'extraction PDF
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
    print("✅ Utilisation de pdfplumber")
except ImportError:
    import PyPDF2
    USE_PDFPLUMBER = False
    print("✅ Utilisation de PyPDF2")

def check_extraction(pdf_path: Path, page_num: int = 54):
    """Vérifie l'extraction d'une page spécifique"""

    print(f"\n📖 Extraction de la page {page_num} depuis : {pdf_path.name}")
    print("="*80)

    if USE_PDFPLUMBER:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num <= len(pdf.pages):
                page = pdf.pages[page_num - 1]  # 0-indexed
                text = page.extract_text() or ""

                print(f"\n📄 TEXTE EXTRAIT (premiers 2000 caractères) :\n")
                print(text[:2000])
                print("\n[...]\n")

                # Vérifier si le texte semble cohérent
                lines = text.split('\n')
                print(f"\n📊 STATISTIQUES :")
                print(f"   - Longueur totale : {len(text)} caractères")
                print(f"   - Nombre de lignes : {len(lines)}")
                print(f"   - Longueur moyenne des lignes : {sum(len(l) for l in lines) / len(lines):.1f} caractères")

                # Vérifier les lignes suspectes (trop courtes ou trop longues)
                short_lines = [l for l in lines if 0 < len(l) < 20]
                long_lines = [l for l in lines if len(l) > 200]

                print(f"\n⚠️  PROBLÈMES POTENTIELS :")
                print(f"   - Lignes très courtes (< 20 car) : {len(short_lines)}")
                print(f"   - Lignes très longues (> 200 car) : {len(long_lines)}")

                if short_lines:
                    print(f"\n   Exemples de lignes courtes :")
                    for line in short_lines[:5]:
                        print(f"      '{line}'")

                # Tentative d'extraction avec layout
                print(f"\n\n🔧 TENTATIVE AVEC extract_text(layout=True) :")
                print("="*80)
                text_layout = page.extract_text(layout=True) or ""
                print(text_layout[:2000])

    else:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            if page_num <= len(reader.pages):
                page = reader.pages[page_num - 1]
                text = page.extract_text() or ""

                print(f"\n📄 TEXTE EXTRAIT (premiers 2000 caractères) :\n")
                print(text[:2000])
                print("\n[...]\n")

                lines = text.split('\n')
                print(f"\n📊 STATISTIQUES :")
                print(f"   - Longueur totale : {len(text)} caractères")
                print(f"   - Nombre de lignes : {len(lines)}")
                print(f"   - Longueur moyenne des lignes : {sum(len(l) for l in lines) / len(lines):.1f} caractères")


def search_in_pdf(pdf_path: Path, search_text: str):
    """Cherche un texte dans toutes les pages du PDF"""

    print(f"\n🔍 Recherche de '{search_text}' dans : {pdf_path.name}")
    print("="*80)

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"📊 Total pages : {total_pages}\n")

        found = False
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text("text")

            if search_text.lower() in text.lower():
                found = True
                print(f"✅ TROUVÉ à la page {page_num + 1}")

                # Afficher le contexte
                pos = text.lower().find(search_text.lower())
                start = max(0, pos - 200)
                end = min(len(text), pos + len(search_text) + 200)
                context = text[start:end]

                print(f"\nContexte (400 caractères) :")
                print(context)
                print("\n" + "="*80)

        if not found:
            print(f"❌ '{search_text}' NON TROUVÉ dans les {total_pages} pages")

            # Essayer variantes
            print("\n🔄 Essai de variantes...")
            variants = ["Voleur", "voleur", "mémoire", "memoire", "2.", "arcane"]
            for v in variants:
                for page_num in range(total_pages):
                    page = doc[page_num]
                    text = page.get_text("text")
                    if v.lower() in text.lower():
                        print(f"  ✅ '{v}' trouvé (page {page_num + 1})")
                        break
                else:
                    print(f"  ❌ '{v}' NON trouvé")

        doc.close()
    except ImportError:
        print("❌ PyMuPDF non installé")
        print("  pip install pymupdf")


if __name__ == "__main__":
    # Chercher les PDFs dans Data/
    data_dir = Path("Data")
    pdfs = list(data_dir.rglob("*.pdf"))

    if not pdfs:
        print("❌ Aucun PDF trouvé dans Data/")
        sys.exit(1)

    print(f"📚 PDFs trouvés : {len(pdfs)}\n")
    for i, pdf in enumerate(pdfs, 1):
        print(f"{i}. {pdf.relative_to(data_dir)}")

    # Chercher dans tous les PDFs
    search_text = "Voleur sans"

    for pdf in pdfs:
        search_in_pdf(pdf, search_text)
        print("\n" + "="*80 + "\n")

    print("\n💡 Si le texte n'est trouvé dans AUCUN PDF :")
    print("  1. Le texte est une IMAGE (non extractible)")
    print("  2. La police est spéciale et n'est pas reconnue")
    print("  3. Le PDF est protégé ou encodé")
    print("\n💡 Solution : Utiliser un PDF avec texte sélectionnable")
