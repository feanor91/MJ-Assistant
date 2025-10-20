"""
Script de diagnostic simple pour tester gpt-oss avec Langchain
"""

import sys
import io

# Fix encoding for Windows
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except:
    pass

try:
    from langchain_ollama import OllamaLLM
except ImportError:
    from langchain_community.llms import Ollama as OllamaLLM

import time

def test_gpt_oss_simple():
    """Teste gpt-oss avec une requête simple"""

    print("=" * 60)
    print("TEST DIAGNOSTIC GPT-OSS - VERSION SIMPLE")
    print("=" * 60)

    # Test 1 : Réponse simple
    print("\nTEST 1 : Reponse simple en francais")
    print("-" * 60)

    try:
        llm = OllamaLLM(
            model="gpt-oss",
            temperature=0.0
        )

        prompt = "Reponds en francais en UNE phrase courte : Qui es-tu ?"

        print("Prompt :", prompt)
        print("En attente... (gpt-oss peut prendre 10-30s)")

        start = time.time()
        response = llm.invoke(prompt)
        duration = time.time() - start

        print("\nREPONSE (en {:.2f}s) :".format(duration))
        print(response)
        print("\nLongueur : {} caracteres".format(len(response)))

    except Exception as e:
        print("\nERREUR :", e)
        import traceback
        traceback.print_exc()
        return

    # Test 2 : Réponse avec contexte RAG-like
    print("\n" + "=" * 60)
    print("\nTEST 2 : Question avec contexte (simulation RAG)")
    print("-" * 60)

    context = """--- DOCUMENT: Regles.pdf ---

Le Voleur sans Memoire

Symbole chez les dragons de la soif insatiable de pouvoir,
de la volonte de regner sans partage, cet arcane represente
l'individualisme des dragons, qui delaissent le bien collectif
pour assouvir leur faim.

Valeurs de Jeu :
- VD : Avidite
- M : Ambiance de penurie, de crise, de famine
- C : Negoce
- MD : Le personnage est constamment Insatisfait."""

    prompt = """Tu es une encyclopedie technique.

CONTEXTE :
{}

Question : Quelle est la VD du Voleur sans Memoire ?

Reponds en citant le texte.""".format(context)

    try:
        print("En attente... (peut prendre 20-40s avec contexte)")

        start = time.time()
        response = llm.invoke(prompt)
        duration = time.time() - start

        print("\nREPONSE (en {:.2f}s) :".format(duration))
        print(response)
        print("\nLongueur : {} caracteres".format(len(response)))

    except Exception as e:
        print("\nERREUR :", e)
        import traceback
        traceback.print_exc()
        return

    # Résumé
    print("\n" + "=" * 60)
    print("DIAGNOSTIC")
    print("=" * 60)

    if duration > 30:
        print("ALERTE : gpt-oss est LENT (>30s par reponse)")
        print("Dans Streamlit avec 10 chunks, ca peut prendre 1-2 minutes")
        print("L'utilisateur peut croire que ca ne repond pas")
        print("\nSOLUTIONS :")
        print("   1. Utilise qwen2.5:14b (plus rapide)")
        print("   2. Ajoute un message 'Patience, generation en cours...'")
        print("   3. Reduis le nombre de chunks pour gpt-oss")
    elif duration > 15:
        print("ATTENTION : gpt-oss est moderement lent (15-30s)")
        print("Acceptable mais ajoute un spinner patient")
    else:
        print("OK : gpt-oss repond rapidement (<15s)")
        print("Le probleme vient d'ailleurs")

if __name__ == "__main__":
    test_gpt_oss_simple()
