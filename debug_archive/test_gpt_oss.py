"""
Script de diagnostic pour tester gpt-oss avec Langchain
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.utils import load_config
try:
    from langchain_ollama import OllamaLLM
except ImportError:
    from langchain_community.llms import Ollama
    OllamaLLM = Ollama
import time

def test_gpt_oss():
    """Teste gpt-oss avec différentes configurations"""

    print("=" * 60)
    print("🔍 TEST DIAGNOSTIC GPT-OSS")
    print("=" * 60)

    # Charger la config
    config = load_config(Path("config.yaml"))

    # Test 1 : Réponse simple sans contexte
    print("\n📝 TEST 1 : Réponse simple (sans contexte RAG)")
    print("-" * 60)

    try:
        llm = Ollama(
            model="gpt-oss",
            temperature=0.0,
            num_ctx=8192,
            num_predict=500
        )

        prompt = "Réponds en français en une phrase : Qui es-tu ?"

        print(f"Prompt : {prompt}")
        print("⏱️  En attente de réponse...")

        start = time.time()
        response = llm.invoke(prompt)
        duration = time.time() - start

        print(f"\n✅ RÉPONSE (en {duration:.2f}s) :")
        print(response)
        print()

    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 2 : Réponse avec contexte court
    print("\n📝 TEST 2 : Réponse avec contexte court (~500 mots)")
    print("-" * 60)

    context = """
    Le Voleur sans Mémoire est l'arcane 2 du Tarot des Ombres.

    Symbole : Symbole chez les dragons de la soif insatiable de pouvoir,
    de la volonté de régner sans partage, cet arcane représente l'individualisme
    des dragons, qui délaissent le bien collectif pour assouvir leur faim.

    Valeurs de Jeu :
    - VD : Avidité
    - M : Ambiance de pénurie, de crise, de famine
    - C : Négoce
    - MD : Le personnage est constamment Insatisfait. Il est obsédé par les
      accomplissements futurs, et peine à se souvenir de ses exploits passés.
    """

    prompt = f"""Contexte :
{context}

Question : Quelle est la Maladie Draconique du Voleur sans Mémoire ?

Réponds en français en citant le texte."""

    try:
        print("⏱️  En attente de réponse...")
        start = time.time()
        response = llm.invoke(prompt)
        duration = time.time() - start

        print(f"\n✅ RÉPONSE (en {duration:.2f}s) :")
        print(response)
        print()

    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 3 : Réponse avec contexte long (simulation RAG)
    print("\n📝 TEST 3 : Réponse avec contexte long (~2000 mots)")
    print("-" * 60)

    long_context = context * 10  # Répéter pour simuler beaucoup de chunks

    prompt = f"""Tu es une encyclopédie technique des règles du jeu de rôle 'Les Lames du Cardinal'.

CONTEXTE (extraits du corpus) :
{long_context}

Question : Explique le Voleur sans Mémoire.

Réponds en français en citant directement le contexte."""

    try:
        print("⏱️  En attente de réponse (peut prendre 30-60s)...")
        start = time.time()
        response = llm.invoke(prompt)
        duration = time.time() - start

        print(f"\n✅ RÉPONSE (en {duration:.2f}s) :")
        print(response[:1000])  # Premiers 1000 caractères
        if len(response) > 1000:
            print(f"... [TRONQUÉ - {len(response)} caractères au total]")
        print()

    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 4 : Test avec le prompt système encyclopédique complet
    print("\n📝 TEST 4 : Prompt système encyclopédique complet")
    print("-" * 60)

    encyclo_prompt = f"""{config['prompts']['encyclo_system']}

===== DÉBUT DU CONTEXTE OBLIGATOIRE =====
{context}
===== FIN DU CONTEXTE OBLIGATOIRE =====

Question : Quelle est la VD du Voleur sans Mémoire ?

Ta réponse (COPIE du contexte uniquement) :"""

    try:
        print("⏱️  En attente de réponse...")
        start = time.time()
        response = llm.invoke(encyclo_prompt)
        duration = time.time() - start

        print(f"\n✅ RÉPONSE (en {duration:.2f}s) :")
        print(response)
        print()

    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        return

    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DU DIAGNOSTIC")
    print("=" * 60)
    print("✅ gpt-oss fonctionne avec Langchain")
    print("💡 Si l'application Streamlit ne répond pas, le problème vient de :")
    print("   1. Timeout trop court dans l'interface")
    print("   2. Contexte RAG trop volumineux (>8192 tokens)")
    print("   3. Prompt système trop directif qui confond le modèle")
    print("\n💡 RECOMMANDATIONS :")
    print("   - Utilise qwen2.5:14b pour le mode encyclopédique (plus rapide)")
    print("   - Réduis le nombre de chunks si gpt-oss est trop lent")
    print("   - Vérifie les logs Streamlit pour timeout/erreurs")

if __name__ == "__main__":
    test_gpt_oss()
