"""
Test d'extraction avec PyMuPDF (fitz)
"""

import sys
import io
from pathlib import Path

# Fix encodage Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import fitz  # PyMuPDF

def test_pymupdf_extraction(pdf_path: Path, page_num: int = 54):
    """Teste l'extraction avec PyMuPDF"""

    print(f"✅ Test avec PyMuPDF (fitz)")
    print(f"📖 Extraction de la page {page_num} depuis : {pdf_path.name}")
    print("="*80)

    doc = fitz.open(pdf_path)

    if page_num <= len(doc):
        page = doc[page_num - 1]  # 0-indexed

        # Méthode 1 : Extraction simple
        text_simple = page.get_text("text")

        print(f"\n📄 MÉTHODE 1 : get_text('text') - premiers 2000 caractères :\n")
        print(text_simple[:2000])
        print("\n[...]\n")

        # Méthode 2 : Extraction avec blocks (respecte mieux la structure)
        text_blocks = page.get_text("blocks")

        print(f"\n📄 MÉTHODE 2 : get_text('blocks') - Reconstruction :\n")
        # Trier les blocs par position (haut vers bas, gauche vers droite)
        sorted_blocks = sorted(text_blocks, key=lambda b: (b[1], b[0]))  # y puis x

        reconstructed = ""
        for block in sorted_blocks:
            if block[6] == 0:  # Type texte
                text = block[4].strip()
                if text:
                    reconstructed += text + "\n"

        print(reconstructed[:2000])
        print("\n[...]\n")

        # Statistiques
        lines = text_simple.split('\n')
        print(f"\n📊 STATISTIQUES (méthode simple) :")
        print(f"   - Longueur totale : {len(text_simple)} caractères")
        print(f"   - Nombre de lignes : {len(lines)}")
        print(f"   - Longueur moyenne des lignes : {sum(len(l) for l in lines) / max(len(lines), 1):.1f} caractères")

        # Vérifier la qualité
        print(f"\n🔍 VÉRIFICATION DE QUALITÉ :")

        # Chercher des phrases clés qui doivent être présentes
        key_phrases = [
            "Difficulté de l'épreuve",
            "Résistance de l'obstacle",
            "Test éclair",
            "Test dramatique"
        ]

        for phrase in key_phrases:
            if phrase.lower() in text_simple.lower():
                print(f"   ✅ '{phrase}' trouvée")
            else:
                print(f"   ❌ '{phrase}' NON trouvée")

        # Chercher des mélanges suspects
        print(f"\n⚠️  DÉTECTION DE MÉLANGES :")
        suspicious_lines = []
        for line in lines[:50]:  # Vérifier les 50 premières lignes
            # Une ligne suspecte contient deux phrases complètes côte à côte
            if ". " in line or "! " in line or "? " in line:
                parts = [p for p in line.split('. ') if len(p) > 30]
                if len(parts) >= 2:
                    suspicious_lines.append(line[:100])

        if suspicious_lines:
            print(f"   {len(suspicious_lines)} lignes suspectes détectées")
            print(f"   Exemple : {suspicious_lines[0]}...")
        else:
            print(f"   ✅ Aucune ligne suspecte détectée")

    doc.close()


if __name__ == "__main__":
    pdf_path = Path("D:/IA/MJ-Assistant/Data/Regles/Livre 2 - Le Jeu.pdf")

    if not pdf_path.exists():
        print(f"❌ PDF non trouvé : {pdf_path}")
        sys.exit(1)

    test_pymupdf_extraction(pdf_path, page_num=54)

    print("\n\n" + "="*80)
    print("💡 CONCLUSION :")
    print("="*80)
    print("Si PyMuPDF donne un texte PROPRE et LISIBLE,")
    print("alors on doit modifier core/rag.py pour l'utiliser !")
