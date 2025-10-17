"""
Module core - Assistant MJ Les Lames du Cardinal

Ce module contient tous les composants principaux de l'application :
- rag.py : Gestion du RAG (extraction, vectorstore, QA)
- memory.py : Gestion de la mémoire et des sessions
- parser.py : Parsing des réponses LLM
- characters.py : Gestion des personnages
- utils.py : Fonctions utilitaires
"""

__version__ = "2.0.0"
__author__ = "Assistant MJ Team"

# Imports pour faciliter l'utilisation
from .rag import DocumentExtractor, VectorStore, RAGChain
from .memory import Memory, MemoryEntry, SessionManager, Statistics
from .parser import ResponseParser, ParsedResponse, GameState
from .characters import Character, CharacterManager
from .utils import (
    load_config,
    get_ollama_models,
    validate_ollama_installation,
    format_file_size,
    truncate_text,
    export_session_to_markdown,
    ColorScheme
)

__all__ = [
    # RAG
    "DocumentExtractor",
    "VectorStore",
    "RAGChain",
    # Memory
    "Memory",
    "MemoryEntry",
    "SessionManager",
    "Statistics",
    # Parser
    "ResponseParser",
    "ParsedResponse",
    "GameState",
    # Characters
    "Character",
    "CharacterManager",
    # Utils
    "load_config",
    "get_ollama_models",
    "validate_ollama_installation",
    "format_file_size",
    "truncate_text",
    "export_session_to_markdown",
    "ColorScheme",
]