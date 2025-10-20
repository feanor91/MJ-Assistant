"""Extraire la page 124 du Livre 2"""

import pymupdf

doc = pymupdf.open('Data/Regles/Livre 2 - Le Jeu.pdf')
page = doc[123]  # Page 124 (index 123)

text = page.get_text()

# Sauvegarder dans un fichier
with open('page_124_tisserande.txt', 'w', encoding='utf-8') as f:
    f.write(text)

print(f"Page 124 extraite ({len(text)} caracteres)")
print(f"Sauvegardee dans page_124_tisserande.txt")

# Afficher les 50 premières lignes
lines = text.split('\n')
print(f"\nPremières 50 lignes:")
for i, line in enumerate(lines[:50], 1):
    print(f"{i:3d}: {line[:100]}")
