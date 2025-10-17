"""
core/parser.py
Parsing des réponses du LLM pour extraire les éléments structurés
"""

import re
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class ParsedResponse:
    """Résultat du parsing d'une réponse"""
    raw_text: str
    options: List[str] = field(default_factory=list)
    npcs: Dict[str, str] = field(default_factory=dict)  # nom -> statut
    locations: Dict[str, str] = field(default_factory=dict)
    intrigues: Dict[str, str] = field(default_factory=dict)
    
    def has_structured_content(self) -> bool:
        """Vérifie si la réponse contient des éléments structurés"""
        return bool(self.options or self.npcs or self.locations or self.intrigues)


class ResponseParser:
    """Parse les réponses du LLM pour extraire les éléments structurés"""
    
    # Patterns regex plus robustes
    OPTION_PATTERNS = [
        r"OPTION\s*(\d+)\s*:\s*(.+?)(?=OPTION\s*\d+\s*:|$)",
        r"(?:^|\n)\s*(\d+)\.\s*(.+?)(?=\n\s*\d+\.|$)",
        r"(?:^|\n)\s*-\s*Option\s*(\d+)\s*:\s*(.+?)(?=\n\s*-\s*Option|$)"
    ]
    
    NPC_PATTERN = r"\[PNJ\s*:\s*([^\]:]+?)\s*:\s*([^\]]+?)\]"
    LOCATION_PATTERN = r"\[Lieu\s*:\s*([^\]:]+?)\s*:\s*([^\]]+?)\]"
    INTRIGUE_PATTERN = r"\[Intrigue\s*:\s*([^\]:]+?)\s*:\s*([^\]]+?)\]"
    
    @classmethod
    def parse(cls, response_text: str) -> ParsedResponse:
        """Parse une réponse complète"""
        return ParsedResponse(
            raw_text=response_text,
            options=cls.extract_options(response_text),
            npcs=cls.extract_entities(response_text, cls.NPC_PATTERN),
            locations=cls.extract_entities(response_text, cls.LOCATION_PATTERN),
            intrigues=cls.extract_entities(response_text, cls.INTRIGUE_PATTERN)
        )
    
    @classmethod
    def extract_options(cls, text: str) -> List[str]:
        """Extrait les options proposées"""
        options = []
        
        # Essayer chaque pattern
        for pattern in cls.OPTION_PATTERNS:
            matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
            if matches:
                options = [match[1].strip() for match in matches]
                break
        
        return options
    
    @classmethod
    def extract_entities(cls, text: str, pattern: str) -> Dict[str, str]:
        """Extrait les entités (PNJ, Lieux, Intrigues)"""
        entities = {}
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        for name, status in matches:
            entities[name.strip()] = status.strip()
        
        return entities
    
    @classmethod
    def clean_response(cls, text: str) -> str:
        """Nettoie la réponse en retirant les marqueurs structurels"""
        # Retire les marqueurs [PNJ:...], [Lieu:...], [Intrigue:...]
        text = re.sub(cls.NPC_PATTERN, "", text, flags=re.IGNORECASE)
        text = re.sub(cls.LOCATION_PATTERN, "", text, flags=re.IGNORECASE)
        text = re.sub(cls.INTRIGUE_PATTERN, "", text, flags=re.IGNORECASE)
        
        # Nettoie les lignes vides multiples
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text.strip()


class GameState:
    """État du jeu (PNJ, lieux, intrigues)"""
    
    def __init__(self):
        self.npcs: Dict[str, str] = {}
        self.locations: Dict[str, str] = {}
        self.intrigues: Dict[str, str] = {}
    
    def update_from_parsed(self, parsed: ParsedResponse):
        """Met à jour l'état à partir d'une réponse parsée"""
        self.npcs.update(parsed.npcs)
        self.locations.update(parsed.locations)
        self.intrigues.update(parsed.intrigues)
    
    def get_npc_icon(self, status: str) -> str:
        """Retourne une icône pour un statut de PNJ"""
        status_lower = status.lower()
        if "ami" in status_lower or "allié" in status_lower:
            return "🤝"
        elif "ennemi" in status_lower or "hostile" in status_lower:
            return "⚔️"
        elif "neutre" in status_lower:
            return "😐"
        elif "mort" in status_lower:
            return "💀"
        else:
            return "❓"
    
    def get_location_icon(self, status: str) -> str:
        """Retourne une icône pour un statut de lieu"""
        status_lower = status.lower()
        if "visité" in status_lower or "découvert" in status_lower:
            return "✅"
        elif "inconnu" in status_lower or "non visité" in status_lower:
            return "❌"
        elif "dangereux" in status_lower:
            return "⚠️"
        else:
            return "📍"
    
    def get_intrigue_icon(self, status: str) -> str:
        """Retourne une icône pour un statut d'intrigue"""
        status_lower = status.lower()
        if "résolue" in status_lower or "terminée" in status_lower:
            return "🟢"
        elif "en cours" in status_lower or "active" in status_lower:
            return "🟡"
        elif "bloquée" in status_lower or "échouée" in status_lower:
            return "🔴"
        elif "partielle" in status_lower:
            return "🟠"
        else:
            return "⚪"
    
    def to_dict(self) -> Dict[str, Any]:
        """Export en dictionnaire"""
        return {
            "npcs": self.npcs,
            "locations": self.locations,
            "intrigues": self.intrigues
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Import depuis dictionnaire"""
        self.npcs = data.get("npcs", {})
        self.locations = data.get("locations", {})
        self.intrigues = data.get("intrigues", {})
    
    def clear(self):
        """Réinitialise l'état"""
        self.npcs.clear()
        self.locations.clear()
        self.intrigues.clear()
    
    def get_summary(self) -> str:
        """Retourne un résumé textuel de l'état"""
        lines = []
        
        if self.npcs:
            lines.append("**PNJ:**")
            for name, status in self.npcs.items():
                icon = self.get_npc_icon(status)
                lines.append(f"  {icon} {name}: {status}")
        
        if self.locations:
            lines.append("\n**Lieux:**")
            for name, status in self.locations.items():
                icon = self.get_location_icon(status)
                lines.append(f"  {icon} {name}: {status}")
        
        if self.intrigues:
            lines.append("\n**Intrigues:**")
            for name, status in self.intrigues.items():
                icon = self.get_intrigue_icon(status)
                lines.append(f"  {icon} {name}: {status}")
        
        return "\n".join(lines) if lines else "Aucun état de jeu pour le moment."