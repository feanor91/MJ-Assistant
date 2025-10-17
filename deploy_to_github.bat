@echo off
REM deploy_to_github.bat - Script de déploiement GitHub pour Windows

setlocal EnableDelayedExpansion

echo ========================================
echo   Deploiement GitHub
echo   Assistant MJ - Les Lames du Cardinal
echo ========================================
echo.

REM Verifier si Git est installe
where git >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Git n'est pas installe
    echo Installe Git depuis: https://git-scm.com/downloads
    pause
    exit /b 1
)
echo [OK] Git detecte
echo.

REM Demander l'URL du repository
set /p REPO_URL="URL de ton repository GitHub: "

if "%REPO_URL%"=="" (
    echo [ERREUR] URL du repository requise
    pause
    exit /b 1
)

REM Verifier si c'est deja un repository git
if exist ".git" (
    echo [ATTENTION] Repository Git existant detecte
    set /p REINIT="Voulez-vous le reinitialiser? (o/N): "
    if /i "!REINIT!"=="o" (
        rmdir /s /q .git
        echo [OK] Repository reinitialise
    )
)

REM Initialiser le repository si necessaire
if not exist ".git" (
    echo [*] Initialisation du repository Git...
    git init
    echo [OK] Repository initialise
    echo.
)

REM Configurer le remote
echo [*] Configuration du remote...
git remote remove origin 2>nul
git remote add origin "%REPO_URL%"
echo [OK] Remote configure
echo.

REM Verifier les identifiants Git
echo [*] Verification des identifiants Git...
for /f "delims=" %%i in ('git config user.name') do set GIT_NAME=%%i
for /f "delims=" %%i in ('git config user.email') do set GIT_EMAIL=%%i

if "%GIT_NAME%"=="" (
    set /p GIT_NAME="Nom d'utilisateur Git: "
    git config user.name "!GIT_NAME!"
)

if "%GIT_EMAIL%"=="" (
    set /p GIT_EMAIL="Email Git: "
    git config user.email "!GIT_EMAIL!"
)

echo [OK] Identifiants: !GIT_NAME! ^<!GIT_EMAIL!^>
echo.

REM Creer .gitignore si inexistant
if not exist ".gitignore" (
    echo [*] Creation de .gitignore...
    (
        echo # Python
        echo __pycache__/
        echo *.py[cod]
        echo venv/
        echo env/
        echo.
        echo # IDE
        echo .vscode/
        echo .idea/
        echo .DS_Store
        echo.
        echo # Data
        echo **/Data/**
        echo !**/Data/README.txt
        echo **/Characters/**
        echo !**/Characters/README.txt
        echo **/lames_db/**
        echo **/saved_sessions/**
        echo **/memory/**
        echo.
        echo # Logs
        echo *.log
        echo.
        echo # OS
        echo Thumbs.db
    ) > .gitignore
    echo [OK] .gitignore cree
    echo.
)

REM Afficher les fichiers a commiter
echo [*] Fichiers a ajouter:
git status --short
echo.

REM Confirmer avant de continuer
set /p CONFIRM="Continuer avec le commit et push? (O/n): "
if /i "!CONFIRM!"=="n" (
    echo [*] Operation annulee
    pause
    exit /b 0
)

REM Ajouter tous les fichiers
echo [*] Ajout des fichiers...
git add .
echo [OK] Fichiers ajoutes
echo.

REM Demander le message de commit
set /p COMMIT_MSG="Message de commit [Refonte complete v2.0]: "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Refonte complete v2.0 - Architecture modulaire

REM Commit
echo [*] Commit des changements...
git commit -m "%COMMIT_MSG%"
echo [OK] Commit effectue
echo.

REM Demander la branche
set /p BRANCH="Nom de la branche [main]: "
if "%BRANCH%"=="" set BRANCH=main

REM Renommer la branche si necessaire
for /f "delims=" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i
if not "!CURRENT_BRANCH!"=="%BRANCH%" (
    git branch -M %BRANCH%
    echo [OK] Branche renommee en %BRANCH%
    echo.
)

REM Push
echo [*] Push vers GitHub...
echo Note: Tu devras peut-etre entrer tes identifiants GitHub
echo.

git push -u origin %BRANCH%

if errorlevel 1 (
    echo.
    echo [ERREUR] Erreur lors du push
    echo.
    echo Causes possibles:
    echo   - Identifiants incorrects
    echo   - Repository n'existe pas sur GitHub
    echo   - Pas les droits en ecriture
    echo.
    echo Solutions:
    echo   1. Cree le repository sur GitHub d'abord
    echo   2. Verifie tes identifiants Git
    echo   3. Utilise un token d'acces personnel ^(PAT^)
    echo      https://github.com/settings/tokens
    pause
    exit /b 1
)

echo.
echo ========================================
echo   SUCCES!
echo ========================================
echo [OK] Code pousse sur GitHub
echo [OK] Repository: %REPO_URL%
echo [OK] Branche: %BRANCH%
echo ========================================
echo.

REM Proposer de creer un tag de version
set /p CREATE_TAG="Creer un tag de version v2.0.0? (o/N): "
if /i "!CREATE_TAG!"=="o" (
    git tag -a v2.0.0 -m "Version 2.0.0 - Refonte complete"
    git push origin v2.0.0
    echo [OK] Tag v2.0.0 cree et pousse
)

echo.
echo Deploiement termine!
echo.
pause