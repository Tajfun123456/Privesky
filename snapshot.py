import os
import json
import re
from pathlib import Path

# --- Konfigurace Snímku ---

# Adresáře, které mají být zcela ignorovány
DIRS_TO_IGNORE = {'node_modules', '__pycache__', '.git', '.vscode'}

# Klíčové soubory, jejichž obsah chceme přečíst
# Upraveno na základě analýzy V2 - index.js a index.css neexistují
KEY_FILES_TO_READ = {
    'package.json',
    'index.html',
    'api/send-order-email.js',
    '_headers',  # Ponecháno pro případné budoucí použití
    '_redirects' # Ponecháno pro případné budoucí použití
}

# Hledané proměnné prostředí
# Přidána PACKETA_API_KEY na základě analýzy index.html
ENV_VARS_TO_CHECK = [
    'RESEND_API_KEY',
    'PACKETA_API_KEY', # NOVĚ PŘIDÁNO
    'SVIX_WEBHOOK_SECRET',
    'NODE_ENV',
    'CI'
]

# --- Funkce Skriptu ---

def snapshot_directory_structure(start_path: Path, output: list, prefix=""):
    """
    Rekurzivně prochází adresář a vytváří textový strom, přičemž ignoruje
    adresáře v DIRS_TO_IGNORE.
    """
    try:
        items = sorted([p for p in start_path.iterdir() if p.name not in ('.', '..')])
    except PermissionError:
        output.append(f"{prefix}└── [Chyba: Přístup odepřen]")
        return
    except FileNotFoundError:
        output.append(f"{prefix}└── [Chyba: Adresář nenalezen]")
        return

    for i, item in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        
        if item.is_dir():
            if item.name in DIRS_TO_IGNORE:
                output.append(f"{prefix}{connector}{item.name}/ [Ignorováno]")
                continue
            
            output.append(f"{prefix}{connector}{item.name}/")
            new_prefix = prefix + ("    " if is_last else "│   ")
            snapshot_directory_structure(item, output, new_prefix)
        else:
            output.append(f"{prefix}{connector}{item.name}")

def read_key_files(start_path: Path, output: list):
    """
    Hledá klíčové soubory a přidává jejich obsah do výstupu.
    """
    output.append("\n" + "=" * 80)
    output.append(" OBSAH KLÍČOVÝCH SOUBORŮ")
    output.append("=" * 80)
    
    base_path = Path(start_path).resolve()

    for file_pattern in KEY_FILES_TO_READ:
        found_files = list(base_path.rglob(file_pattern))
        
        if not found_files:
            direct_path = base_path / file_pattern
            if direct_path.exists() and direct_path.is_file():
                found_files = [direct_path]
            else:
                output.append(f"\n--- Soubor nenalezen (to může být v pořádku): {file_pattern} ---")
                continue

        for file_path in found_files:
            try:
                relative_path = file_path.relative_to(base_path)
                output.append(f"\n--- ZAČÁTEK: {relative_path} ---")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    output.append(content)
                
                output.append(f"--- KONEC: {relative_path} ---")
            
            except UnicodeDecodeError:
                output.append(f"[Chyba: Nelze přečíst soubor '{relative_path}' (problém s kódováním)]")
            except Exception as e:
                output.append(f"[Chyba při čtení souboru '{relative_path}': {e}]")

def snapshot_environment(output: list):
    """
    Kontroluje proměnné prostředí a lokální .env soubory.
    """
    output.append("\n" + "=" * 80)
    output.append(" ANALÝZA PROSTŘEDÍ (LOKÁLNÍ STROJ)")
    output.append("=" * 80)

    output.append("\n--- Systémové proměnné (OS) ---")
    output.append(f"Operační systém: {os.name} ({os.sys.platform})")
    output.append(f"Aktuální uživatel: {os.getenv('USERNAME') or os.getenv('USER', 'Neznámý')}")
    output.append(f"Cesta k Pythonu: {os.sys.executable}")

    output.append("\n--- Proměnné prostředí projektu ---")
    output.append("Poznámka: 'Nenastaveno' znamená, že proměnná není nalezena na tomto stroji.")
    output.append("V produkčním prostředí (Vercel/Netlify) by měly být nastaveny.")
    
    for var in ENV_VARS_TO_CHECK:
        value = os.getenv(var)
        if value:
            output.append(f"{var}: ********** (Nastaveno)")
        else:
            output.append(f"{var}: Nenastaveno")

    output.append("\n--- Lokální konfigurační soubory (.env) ---")
    for env_name in ['.env', '.env.local', '.env.development', '.env.production']:
        env_file = Path('.') / env_name
        if env_file.exists():
            output.append(f"Nalezen soubor: {env_name} (POZOR: Obsah se nenačítá z bezpečnostních důvodů)")
        else:
            output.append(f"Soubor {env_name} nenalezen.")

def analyze_project(start_path: Path, output: list):
    """
    NOVÁ FUNKCE: Provádí hlubší analýzu klíčových souborů.
    """
    output.append("\n" + "=" * 80)
    output.append(" HLOUBKOVÁ ANALÝZA PROJEKTU")
    output.append("=" * 80)
    
    base_path = Path(start_path).resolve()

    # 1. Analýza package.json
    output.append("\n--- Analýza package.json ---")
    package_json_path = base_path / 'package.json'
    if package_json_path.exists():
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                
            output.append(f"Typ projektu (podle package.json): {pkg.get('type', 'Nespecifikováno (výchozí commonjs)')}")
            
            if 'dependencies' in pkg:
                output.append("Hlavní závislosti (dependencies):")
                for dep, version in pkg['dependencies'].items():
                    output.append(f"  - {dep}: {version}")
            else:
                output.append("Hlavní závislosti (dependencies): Neuvedeny")

            if 'devDependencies' in pkg:
                output.append("Vývojové závislosti (devDependencies):")
                for dep, version in pkg['devDependencies'].items():
                    output.append(f"  - {dep}: {version}")
            else:
                output.append("Vývojové závislosti (devDependencies): Neuvedeny")

            if 'scripts' in pkg:
                output.append("Skripty (scripts):")
                for script, command in pkg['scripts'].items():
                    output.append(f"  - {script}: \"{command}\"")
            else:
                output.append("Skripty (scripts): Neuvedeny")
                
        except Exception as e:
            output.append(f"[Chyba při analýze package.json: {e}]")
    else:
        output.append("Soubor package.json nenalezen.")

    # 2. Analýza index.html (Externí zdroje a API volání)
    output.append("\n--- Analýza index.html ---")
    index_html_path = base_path / 'index.html'
    if index_html_path.exists():
        try:
            with open(index_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Hledání externích skriptů
            scripts = re.findall(r'<script.*?src="(https?://.*?)".*?>', html_content)
            output.append("Externí skripty (CDN):")
            if scripts:
                for script in scripts:
                    output.append(f"  - {script}")
            else:
                output.append("  (Žádné externí skripty nenalezeny)")

            # Hledání externích CSS
            styles = re.findall(r'<link.*?rel="stylesheet".*?href="(https?://.*?)".*?>', html_content)
            output.append("Externí CSS (CDN):")
            if styles:
                for style in styles:
                    output.append(f"  - {style}")
            else:
                output.append("  (Žádné externí CSS nenalezeny)")

            # Hledání API volání uvnitř <script type="text/babel">
            api_calls = re.findall(r'fetch\([\'"](/api/.*?)[\'"]', html_content)
            output.append("Detekovaná API volání (fetch):")
            if api_calls:
                for api_call in sorted(list(set(api_calls))): # Seřadit a odstranit duplicity
                    output.append(f"  - {api_call}")
            else:
                output.append("  (Žádná API volání nenalezena)")

        except Exception as e:
            output.append(f"[Chyba při analýze index.html: {e}]")
    else:
        output.append("Soubor index.html nenalezen.")

    # 3. Analýza adresáře api/
    output.append("\n--- Analýza adresáře 'api/' ---")
    api_dir = base_path / 'api'
    if api_dir.is_dir():
        api_files = [f.name for f in api_dir.iterdir() if f.is_file() and (f.suffix == '.js' or f.suffix == '.ts')]
        if api_files:
            output.append("Nalezené serverless funkce:")
            for api_file in api_files:
                output.append(f"  - /api/{api_file}")
        else:
            output.append("Adresář 'api/' je prázdný.")
    else:
        output.append("Adresář 'api/' nenalezen.")


def main():
    """
    Hlavní funkce pro spuštění snímkování.
    """
    start_path = Path('.').resolve()
    output_lines = []

    output_lines.append("=" * 80)
    output_lines.append(f" SNÍMEK PROJEKTU (v3): {start_path}")
    output_lines.append("=" * 80)

    # 1. Snímek adresářové struktury
    output_lines.append("\n--- Adresářová struktura ---")
    snapshot_directory_structure(start_path, output_lines)

    # 2. Snímek prostředí
    snapshot_environment(output_lines)
    
    # 3. NOVÁ ANALÝZA
    analyze_project(start_path, output_lines)
    
    # 4. Snímek obsahu souborů
    read_key_files(start_path, output_lines)
    
    # Uložení do souboru
    output_filename = "project_snapshot_v3.txt" # Změnil jsem název souboru
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(output_lines))
        
        print(f"\nHotovo! Snímek projektu byl uložen do souboru: {output_filename}")
        print(f"Velikost souboru: {Path(output_filename).stat().st_size} bytes")

    except Exception as e:
        print(f"\nDošlo k chybě při ukládání souboru: {e}")
        print("\n--- Výstup do konzole ---")
        print("\n".join(output_lines))

if __name__ == "__main__":
    main()