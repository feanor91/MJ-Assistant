"""
tests/test_core.py
Tests unitaires pour les modules core
"""

import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory import Memory, MemoryEntry, SessionManager
from core.parser import ResponseParser, GameState
from core.characters import CharacterManager
from core.utils import truncate_text, format_file_size


class TestMemory:
    """Tests pour le module memory"""
    
    def test_memory_add_entry(self, tmp_path):
        """Test ajout d'entrées"""
        memory = Memory(max_size=5)
        
        memory.add("Question 1", "Réponse 1")
        memory.add("Question 2", "Réponse 2")
        
        assert len(memory) == 2
        assert memory.entries[0].user == "Question 1"
        assert memory.entries[1].assistant == "Réponse 2"
    
    def test_memory_max_size(self):
        """Test limitation de taille"""
        memory = Memory(max_size=3)
        
        for i in range(5):
            memory.add(f"Q{i}", f"R{i}")
        
        assert len(memory) == 3
        assert memory.entries[0].user == "Q2"  # Les 2 premiers ont été supprimés
    
    def test_memory_format_for_prompt(self):
        """Test formatage pour prompt"""
        memory = Memory(max_size=10)
        memory.add("Bonjour", "Salut")
        memory.add("Comment ça va?", "Bien merci")
        
        formatted = memory.format_for_prompt(n=2)
        
        assert "Bonjour" in formatted
        assert "Salut" in formatted
        assert "Comment ça va?" in formatted
    
    def test_memory_persistence(self, tmp_path):
        """Test sauvegarde et chargement"""
        memory_file = tmp_path / "test_memory.json"
        
        # Créer et sauvegarder
        memory = Memory(max_size=5, memory_file=memory_file)
        memory.add("Test 1", "Réponse 1")
        memory.add("Test 2", "Réponse 2")
        memory.save()
        
        # Charger dans une nouvelle instance
        memory2 = Memory(max_size=5, memory_file=memory_file)
        
        assert len(memory2) == 2
        assert memory2.entries[0].user == "Test 1"


class TestParser:
    """Tests pour le module parser"""
    
    def test_extract_options(self):
        """Test extraction des options"""
        response = """
        Voici la situation.
        
        OPTION 1: Attaquer frontalement
        OPTION 2: Contourner par la gauche
        OPTION 3: Négocier
        """
        
        parsed = ResponseParser.parse(response)
        
        assert len(parsed.options) == 3
        assert "Attaquer frontalement" in parsed.options[0]
    
    def test_extract_npcs(self):
        """Test extraction des PNJ"""
        response = """
        [PNJ:Cardinal Richelieu:Ennemi]
        Vous rencontrez le Cardinal.
        [PNJ:Anne d'Autriche:Ami]
        """
        
        parsed = ResponseParser.parse(response)
        
        assert len(parsed.npcs) == 2
        assert parsed.npcs["Cardinal Richelieu"] == "Ennemi"
        assert parsed.npcs["Anne d'Autriche"] == "Ami"
    
    def test_extract_locations(self):
        """Test extraction des lieux"""
        response = """
        [Lieu:Paris:Visité]
        [Lieu:Londres:Non visité]
        """
        
        parsed = ResponseParser.parse(response)
        
        assert len(parsed.locations) == 2
        assert parsed.locations["Paris"] == "Visité"
    
    def test_extract_intrigues(self):
        """Test extraction des intrigues"""
        response = """
        [Intrigue:Complot du Cardinal:En cours]
        [Intrigue:Ferrets de la Reine:Résolue]
        """
        
        parsed = ResponseParser.parse(response)
        
        assert len(parsed.intrigues) == 2
        assert parsed.intrigues["Complot du Cardinal"] == "En cours"
    
    def test_has_structured_content(self):
        """Test détection de contenu structuré"""
        response1 = "Simple réponse sans structure"
        parsed1 = ResponseParser.parse(response1)
        assert not parsed1.has_structured_content()
        
        response2 = "OPTION 1: Test"
        parsed2 = ResponseParser.parse(response2)
        assert parsed2.has_structured_content()


class TestGameState:
    """Tests pour GameState"""
    
    def test_update_from_parsed(self):
        """Test mise à jour depuis ParsedResponse"""
        game_state = GameState()
        
        response = """
        [PNJ:Test:Ami]
        [Lieu:Paris:Visité]
        """
        parsed = ResponseParser.parse(response)
        
        game_state.update_from_parsed(parsed)
        
        assert "Test" in game_state.npcs
        assert "Paris" in game_state.locations
    
    def test_get_icons(self):
        """Test récupération des icônes"""
        game_state = GameState()
        
        # PNJ
        assert game_state.get_npc_icon("Ami") == "🤝"
        assert game_state.get_npc_icon("Ennemi") == "⚔️"
        assert game_state.get_npc_icon("Mort") == "💀"
        
        # Lieux
        assert game_state.get_location_icon("Visité") == "✅"
        assert game_state.get_location_icon("Non visité") == "❌"
        
        # Intrigues
        assert game_state.get_intrigue_icon("Résolue") == "🟢"
        assert game_state.get_intrigue_icon("En cours") == "🟡"
    
    def test_to_dict_from_dict(self):
        """Test sérialisation"""
        game_state = GameState()
        game_state.npcs = {"Test": "Ami"}
        game_state.locations = {"Paris": "Visité"}
        
        data = game_state.to_dict()
        
        game_state2 = GameState()
        game_state2.from_dict(data)
        
        assert game_state2.npcs == game_state.npcs
        assert game_state2.locations == game_state.locations


class TestUtils:
    """Tests pour utils"""
    
    def test_truncate_text(self):
        """Test troncature de texte"""
        text = "Ceci est un texte très long qui doit être tronqué"
        truncated = truncate_text(text, max_length=20)
        
        assert len(truncated) <= 23  # 20 + "..."
        assert truncated.endswith("...")
    
    def test_format_file_size(self):
        """Test formatage de taille"""
        assert format_file_size(512) == "512.0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"


class TestSessionManager:
    """Tests pour SessionManager"""
    
    def test_save_load_session(self, tmp_path):
        """Test sauvegarde et chargement"""
        session_manager = SessionManager(tmp_path)
        
        # Créer des mémoires
        mj_memory = Memory(max_size=10)
        mj_memory.add("Q1", "R1")
        
        encyclo_memory = Memory(max_size=10)
        encyclo_memory.add("Q2", "R2")
        
        # Sauvegarder
        success = session_manager.save_session(
            "test_session",
            mj_memory,
            encyclo_memory,
            metadata={"test": "value"}
        )
        
        assert success
        
        # Charger
        data = session_manager.load_session("test_session")
        
        assert data is not None
        assert len(data['mj_entries']) == 1
        assert data['mj_entries'][0].user == "Q1"
        assert data['metadata']['test'] == "value"
    
    def test_list_sessions(self, tmp_path):
        """Test listage des sessions"""
        session_manager = SessionManager(tmp_path)
        
        # Créer plusieurs sessions
        mj_memory = Memory(max_size=10)
        encyclo_memory = Memory(max_size=10)
        
        session_manager.save_session("session1", mj_memory, encyclo_memory)
        session_manager.save_session("session2", mj_memory, encyclo_memory)
        
        sessions = session_manager.list_sessions()
        
        assert len(sessions) == 2
        assert "session1" in sessions
        assert "session2" in sessions
    
    def test_delete_session(self, tmp_path):
        """Test suppression"""
        session_manager = SessionManager(tmp_path)
        
        mj_memory = Memory(max_size=10)
        encyclo_memory = Memory(max_size=10)
        
        session_manager.save_session("to_delete", mj_memory, encyclo_memory)
        
        assert "to_delete" in session_manager.list_sessions()
        
        session_manager.delete_session("to_delete")
        
        assert "to_delete" not in session_manager.list_sessions()


# Fixtures pytest
@pytest.fixture
def sample_config():
    """Config exemple pour les tests"""
    return {
        'paths': {
            'base_dir': Path('/tmp/test'),
            'pdf_root': Path('/tmp/test/Data'),
            'char_dir': Path('/tmp/test/Characters'),
            'db_dir': Path('/tmp/test/lames_db'),
            'save_dir': Path('/tmp/test/saved_sessions'),
            'memory_dir': Path('/tmp/test/memory')
        },
        'model': {
            'default': 'mistral-nemo',
            'temperature': 0.0,
            'top_p': 1.0
        },
        'rag': {
            'embedding_model': 'all-MiniLM-L6-v2',
            'k_retrieval': 6,
            'chunk_size': 1000,
            'chunk_overlap': 150
        },
        'memory': {
            'max_mj_memory': 30,
            'max_encyclo_memory': 10,
            'short_memory_context': 3
        }
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])