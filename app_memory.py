"""
app_memory.py
Module de gestion de la mémoire pour l'assistant MJ
"""

def render_memory_content(mode: str):
    """
    Affiche la mémoire selon le mode
    """
    if mode == 'mj':
        st.info("### 🎮 Mémoire de la partie (Mode MJ)")
        st.write("Contenu de la mémoire du jeu...")
    elif mode == 'encyclo':
        st.info("### 📚 Mémoire des derniers échanges (Mode Encyclopédique)")
        st.write("Contenu de la mémoire encyclopédique...")