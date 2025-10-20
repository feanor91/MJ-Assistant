"""
Script pour tester la qualité de l'extraction PDF
Compare l'extraction automatique avec un échantillon manuel
"""

from pathlib import Path
from core.rag import DocumentExtractor

# Choisis un PDF de test
test_pdf = Path("Documents/Regles/nom_du_fichier.pdf")  # ⚠️ MODIFIE CE CHEMIN

if test_pdf.exists():
    print(f"📄 Test d'extraction pour : {test_pdf.name}")
    print("=" * 60)

    # Extraire le contenu
    content = DocumentExtractor.extract_from_pdf(test_pdf, max_pages=3)

    # Afficher les 3 premières pages
    print(content[:3000])  # Premiers 3000 caractères

    print("\n" + "=" * 60)
    print(f"✅ Total : {len(content)} caractères extraits")

    # Sauvegarder dans un fichier pour inspection
    output = Path("test_extraction.txt")
    output.write_text(content, encoding='utf-8')
    print(f"💾 Contenu complet sauvegardé dans : {output}")

    # Vérifications automatiques
    print("\n🔍 Vérifications :")
    issues = []

    if "--- COLONNE DROITE ---" in content:
        print("✅ Détection colonnes active")
    else:
        print("ℹ️  PDF simple colonne détecté")

    # Caractères problématiques
    problematic = ["Ã©", "Ã¨", "Ã ", "â€™", "œ"]
    for char in problematic:
        if char in content:
            issues.append(f"Encodage suspect : '{char}'")

    # Vérifier si du texte manque (pages très courtes)
    if len(content) < 500:
        issues.append("⚠️ Très peu de texte extrait - possible problème")

    if issues:
        print("\n⚠️ PROBLÈMES DÉTECTÉS :")
        for issue in issues:
            print(f"  - {issue}")
        print("\n💡 Recommandation : Conversion manuelle pourrait améliorer la qualité")
    else:
        print("✅ Aucun problème évident détecté")
        print("💡 L'extraction automatique semble bonne")
else:
    print(f"❌ Fichier non trouvé : {test_pdf}")
    print("💡 Modifie la variable 'test_pdf' avec le chemin correct")
