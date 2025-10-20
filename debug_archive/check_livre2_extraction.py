"""
Vérifier l'extraction complète de Livre 2 - Le Jeu.pdf
"""

import sys
import io

# Fix encodage Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
import fitz  # PyMuPDF

pdf_path = Path("Data/Regles/Livre 2 - Le Jeu.pdf")

print("🔍 ANALYSE DE L'EXTRACTION DE LIVRE 2\n")
print("="*80)

# 1. Informations générales du PDF
doc = fitz.open(pdf_path)
total_pages = len(doc)

print(f"\n📖 Informations du PDF:")
print(f"   Fichier: {pdf_path.name}")
print(f"   Total pages: {total_pages}")

# 2. Chercher "Voleur sans" dans le PDF brut
print(f"\n🔍 Recherche de 'Voleur sans' dans le PDF:")

voleur_pages = []
for page_num in range(total_pages):
    page = doc[page_num]
    text = page.get_text("text")
    if "voleur sans" in text.lower():
        voleur_pages.append(page_num + 1)
        print(f"   ✅ Page {page_num + 1}")

if not voleur_pages:
    print("   ❌ NON TROUVÉ dans le PDF")
else:
    print(f"\n✅ Trouvé sur {len(voleur_pages)} pages: {voleur_pages}")

# 3. Extraire la page 125 pour voir le contenu exact
print(f"\n📄 EXTRACTION DE LA PAGE 125:")
print("="*80)

if total_pages >= 125:
    page = doc[124]  # 0-indexed
    text = page.get_text("text")
    print(text[:2000])  # Premiers 2000 caractères

    print(f"\n📊 Statistiques page 125:")
    print(f"   Longueur: {len(text)} caractères")
    print(f"   Contient 'Voleur': {'✅' if 'voleur' in text.lower() else '❌'}")
    print(f"   Contient 'sans': {'✅' if 'sans' in text.lower() else '❌'}")
    print(f"   Contient 'mémoire': {'✅' if 'mémoire' in text.lower() or 'memoire' in text.lower() else '❌'}")
else:
    print(f"   ❌ Le PDF n'a que {total_pages} pages")

doc.close()

# 4. Vérifier l'extraction complète (comme dans rag.py)
print(f"\n\n🔧 SIMULATION DE L'EXTRACTION COMPLÈTE (comme rag.py):")
print("="*80)

doc = fitz.open(pdf_path)
all_text = ""

for page_num in range(len(doc)):
    page = doc[page_num]
    all_text += page.get_text("text") + "\n"

doc.close()

print(f"   Texte total extrait: {len(all_text)} caractères")
print(f"   Contient 'Voleur sans': {'✅' if 'voleur sans' in all_text.lower() else '❌'}")

# Si trouvé, afficher le contexte
if "voleur sans" in all_text.lower():
    pos = all_text.lower().find("voleur sans")
    context = all_text[max(0, pos-200):min(len(all_text), pos+500)]
    print(f"\n   📝 Contexte (700 car autour de 'Voleur sans'):")
    print("   " + "-"*76)
    print("   " + context.replace("\n", "\n   "))
else:
    print("\n   ❌ PROBLÈME: Le texte n'est PAS dans l'extraction complète")

    # Vérifier si c'est un problème de casse ou d'espaces
    print("\n   🔍 Tests alternatifs:")
    test_variants = [
        "voleur",
        "Voleur",
        "VOLEUR",
        "sans mémoire",
        "sans memoire",
        "2.",  # Numéro de l'arcane
        "arcane"
    ]

    for variant in test_variants:
        found = variant.lower() in all_text.lower()
        print(f"      '{variant}': {'✅ trouvé' if found else '❌ absent'}")
