import os
import csv
import json
import urllib.request
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("VF_USERNAME")
PASSWORD = os.environ.get("VF_PASSWORD")
WEBHOOK_URL = os.environ.get("GOOGLE_WEBHOOK_URL")

# URL de l'équipe de ton camarade
URL_CAMARADE = "https://www.virtuafoot.com/#club?uid=689237"

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

        # Attente souple de la redirection post-connexion
        page.wait_for_url("**/#*", timeout=15000)
        print("Connecté avec succès !")

        # ====================================================
        # 1. EXTRACTION DE TON EFFECTIF
        # ====================================================
        print("\n--- Accès et extraction de ton effectif ---")
        page.goto("https://www.virtuafoot.com/#joueurs?view=niv")
        page.wait_for_timeout(7000)

        data_perso = []
        rows = page.locator("div[class*='css-g5y9jx'][style*='background-color']").all()
        
        if not rows:
            rows = page.locator("div[class*='css-g5y9jx']").all()

        seen_rows = set()
        for row in rows:
            text = row.inner_text().strip()
            if text:
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if 5 <= len(lines) <= 25:
                    row_tuple = tuple(lines)
                    if row_tuple not in seen_rows:
                        seen_rows.add(row_tuple)
                        data_perso.append(lines)

        # Sauvegarde locale de ton CSV
        csv_perso = "virtuafoot_effectif.csv"
        with open(csv_perso, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data_perso)

        print(f"Fichier {csv_perso} généré avec succès ({len(data_perso)} lignes enregistrées) !")

        # ====================================================
        # 2. EXTRACTION DE L'EFFECTIF DU CAMARADE
        # ====================================================
        print(f"\n--- Accès et extraction de l'effectif du camarade ---")
        page.goto(URL_CAMARADE)
        page.wait_for_timeout(7000)

        # Petit défilement vers le bas pour déclencher le chargement des éléments en bas de page
        print("Défilement de la page pour charger les données...")
        for _ in range(3):
            page.keyboard.press("PageDown")
            page.wait_for_timeout(1000)

        data_camarade = []
        rows_camarade = page.locator("div[class*='css-g5y9jx'][style*='background-color']").all()
        
        if not rows_camarade:
            rows_camarade = page.locator("div[class*='css-g5y9jx']").all()

        seen_rows_camarade = set()
        for row in rows_camarade:
            text = row.inner_text().strip()
            if text:
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if 5 <= len(lines) <= 25:
                    row_tuple = tuple(lines)
                    if row_tuple not in seen_rows_camarade:
                        seen_rows_camarade.add(row_tuple)
                        data_camarade.append(lines)

        # Méthode de secours textuelle si les blocs structurés ne remontent rien sur cette page
        if not data_camarade:
            print("Utilisation de la méthode de secours textuelle pour le camarade...")
            content_text = page.locator("#content, #divbody").inner_text()
            for line in content_text.split("\n"):
                cleaned = line.strip()
                if cleaned:
                    data_camarade.append([cleaned])

        # Sauvegarde locale du CSV pour le camarade
        csv_camarade = "virtuafoot_effectif_camarade.csv"
        with open(csv_camarade, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data_camarade)

        print(f"Fichier {csv_camarade} généré avec succès ({len(data_camarade)} lignes enregistrées) !")

        # ====================================================
        # 3. SYNCHRONISATION WEBHOOK (OPTIONNELLE)
        # ====================================================
        if WEBHOOK_URL and data_perso:
            print("\nSynchronisation de ton effectif avec Google Sheets...")
            try:
                payload = json.dumps(data_perso).encode("utf-8")
                req = urllib.request.Request(
                    WEBHOOK_URL,
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req) as response:
                    print("Synchronisation Google Sheets réussie !")
            except Exception as e:
                print(f"Erreur lors de la synchronisation Google Sheets : {e}")

        browser.close()

if __name__ == "__main__":
    run()
