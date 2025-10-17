@echo off
REM start.bat - Script de démarrage pour Windows

setlocal EnableDelayedExpansion

echo ========================================
echo   Assistant MJ - Les Lames du Cardinal
echo ========================================
echo.

REM Vérifier Python
echo [*] Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH
    echo Installe Python depuis: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python detecte
echo.

REM Vérifier l'environnement virtuel
if not exist "venv" (
    echo [*] Creation de l'environnement virtuel...
    python -m venv venv
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer l'environnement virtuel
        pause
        exit /b 1
    )
    echo [OK] Environnement virtuel cree
) else (
    echo [OK] Environnement virtuel trouve
)
echo.

REM Activer l'environnement virtuel
echo [*] Activation de l'environnement virtuel...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERREUR] Impossible d'activer l'environnement virtuel
    pause
    exit /b 1
)
echo [OK] Environnement virtuel active
echo.

REM Vérifier les dépendances
echo [*] Verification des dependances...
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [*] Installation des dependances...
    python -m pip install --upgrade pip --quiet
    python -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [ERREUR] Echec de l'installation des dependances
        pause
        exit /b 1
    )
    echo [OK] Dependances installees
) else (
    echo [OK] Dependances deja installees
)
echo.

REM Vérifier Ollama
echo [*] Verification d'Ollama...
where ollama >nul 2>&1
if errorlevel 1 (
    echo [ATTENTION] Ollama n'est pas installe
    echo Installe depuis: https://ollama.ai
    echo.
) else (
    echo [OK] Ollama est installe
    
    REM Vérifier si Ollama est en cours d'exécution
    tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
    if errorlevel 1 (
        echo [ATTENTION] Ollama n'est pas en cours d'execution
        echo Demarre Ollama avant de continuer
        echo.
    ) else (
        echo [OK] Ollama est en cours d'execution
    )
)
echo.

REM Vérifier la configuration
if not exist "config.yaml" (
    echo [ATTENTION] Fichier config.yaml non trouve
    echo Execute: python setup.py
    echo.
    set /p SETUP="Executer le setup maintenant? (O/n): "
    if /i "!SETUP!"=="O" (
        python setup.py
        if errorlevel 1 (
            echo [ERREUR] Echec du setup
            pause
            exit /b 1
        )
    )
) else (
    echo [OK] Fichier config.yaml trouve
)
echo.

REM Démarrer l'application
echo ========================================
echo   Demarrage de l'application
echo ========================================
echo.
echo L'application va s'ouvrir dans votre navigateur...
echo Appuie sur Ctrl+C pour arreter l'application
echo.

streamlit run app.py

REM Si Streamlit se ferme, attendre
if errorlevel 1 (
    echo.
    echo [ERREUR] L'application a rencontre une erreur
    pause
    exit /b 1
)

pause