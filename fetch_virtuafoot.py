import os
import csv
import json
import urllib.request
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("VF_USERNAME")
PASSWORD = os.environ.get("VF_PASSWORD")
WEBHOOK_URL = os.environ.get("GOOGLE_WEBHOOK_URL")

URL_CAMARADE = "https://www.virtuafoot.com/#club?uid=689237&view=niv"

def clean_rows(raw_blocks):
    """Nettoie, aplatit et filtre les blocs pour ne garder que des lignes de joueurs unitaires propres."""
    cleaned = []
    seen = set()
    for block in raw_blocks:
        if isinstance(block, list):
            flat_lines = []
            for item in block:
                if isinstance(item, str):
                    flat_lines.extend([sub.strip() for sub in item.split("\n") if sub.strip()])
                else:
                    flat_lines.append(str(item))
            
            # Une ligne de joueur valide a généralement entre 3 et 10 éléments (Numéro, Poste, Nom, Âge, Note...)
            if 3 <= len(flat_lines) <= 12:
                row_tuple = tuple(flat_lines)
                if row_tuple not in seen:
                    seen.add(row_tuple)
                    cleaned.append(flat_lines)
    return cleaned

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()

        print("Connexion à Virtuafoot...")
        page.goto("https://www.virtuafoot.com/")

        # Identification
        page.fill("form#login input[type='text'], form#login input[name='login'], input[name='login']", USERNAME)
        page.fill("form#login input[type='password'], form#login input[name='pass'], input[name='pass']", PASSWORD)
        page.locator("form#login button[type='submit'], form#login input[type='submit'], button:has-text('Connexion')").first.click()

        page.wait_for_url("**/#*", timeout=15000)
        print("Connecté avec succès !")

        # ====================================================
        # 1. EXTRACTION DE TON EFFECTIF
        # ====================================================
        print("\n--- Accès et extraction de ton effectif ---")
        page.goto("https://www.virtuafoot.com/#joueurs?view=niv")
        page.wait_for_timeout(7000)

        data_perso_raw = []
        rows = page.locator("div[class*='css-g5y9jx'][style*='background-color']").all()
        if not rows:
            rows = page.locator("div[class*='css-g5y9jx']").all()

        seen_rows = set()
        for row in rows:
            text = row.inner_text().strip()
            if text:
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if 4 <= len(lines) <= 25:
                    row_tuple = tuple(lines)
                    if row_tuple not in seen_rows:
                        seen_rows.add(row_tuple)
                        data_perso_raw.append(lines)

        data_perso = clean_rows(data_perso_raw)

        with open("virtuafoot_effectif.csv", mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data_perso)
        print(f"Fichier virtuafoot_effectif.csv généré ({len(data_perso)} lignes).")

        # ====================================================
        # 2. EXTRACTION DE L'EFFECTIF DU CAMARADE
        # ====================================================
        print("\n--- Accès et extraction de l'effectif du camarade ---")
        page.goto(URL_CAMARADE)
        page.wait_for_timeout(8000)

        print("Défilement de la page pour charger les données...")
        for _ in range(4):
            page.keyboard.press("PageDown")
            page.wait_for_timeout(1000)

        data_camarade_raw = []
        # On cible uniquement les sous-éléments précis (on évite 'div[class*="row"]' qui englobe tout)
        player_blocks = page.locator("div[class*='css-']").all()
        
        for block in player_blocks:
            try:
                text = block.inner_text().strip()
                if text:
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    
                    # Filtre anti-menus du club
                    joined_text = " ".join(lines).upper()
                    if any(keyword in joined_text for keyword in ["STADIUM", "LEVEL", "AWARDS", "RATING", "TRANSFERS", "SCORERS", "PALMARES"]):
                        continue

                    # On ne garde que les blocs de taille unitaire (1 seul joueur par bloc)
                    if 3 <= len(lines) <= 12:
                        data_camarade_raw.append(lines)
            except Exception:
                continue

        data_camarade = clean_rows(data_camarade_raw)

        with open("virtuafoot_effectif_camarade.csv", mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data_camarade)
        print(f"Fichier virtuafoot_effectif_camarade.csv généré ({len(data_camarade)} lignes filtrées).")

        # ====================================================
        # 3. SYNCHRONISATION COMBINÉE VERS GOOGLE SHEETS
        # ====================================================
        if WEBHOOK_URL:
            print("\nSynchronisation des 2 effectifs avec Google Sheets...")
            payload_complet = {
                "perso": data_perso,
                "camarade": data_camarade
            }
            try:
                req = urllib.request.Request(
                    WEBHOOK_URL,
                    data=json.dumps(payload_complet).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req) as response:
                    print("Synchronisation réussie ! Les onglets Mon_Effectif et Effectif_Camarade ont été mis à jour.")
            except Exception as e:
                print(f"Erreur lors de la synchronisation Webhook : {e}")
        else:
            print("Aucun secret GOOGLE_WEBHOOK_URL détecté.")

        browser.close()

if __name__ == "__main__":
    run()
