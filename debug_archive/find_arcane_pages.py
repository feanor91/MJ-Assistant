"""Trouver les pages contenant La Tisserande Oubliée dans le Livre 2"""

import pymupdf

doc = pymupdf.open('Data/Regles/Livre 2 - Le Jeu.pdf')

print(f"Total pages: {len(doc)}\n")

for page_num in range(len(doc)):
    page = doc[page_num]
    text = page.get_text()

    if 'tisserande' in text.lower() and 'oubli' in text.lower():
        print(f"=== PAGE {page_num + 1} ===")
        # Extraire les lignes contenant tisserande
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'tisserande' in line.lower():
                # Afficher contexte: 2 lignes avant, la ligne, 5 lignes après
                start = max(0, i - 2)
                end = min(len(lines), i + 6)
                context = '\n'.join(lines[start:end])
                print(f"\nContexte (lignes {start}-{end}):")
                print(context)
                print("-" * 60)

doc.close()
