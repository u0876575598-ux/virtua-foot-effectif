import os
import csv
import json
import urllib.request
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("VF_USERNAME")
PASSWORD = os.environ.get("VF_PASSWORD")
WEBHOOK_URL = os.environ.get("GOOGLE_WEBHOOK_URL")

URL_CAMARADE = "https://www.virtuafoot.com/#club?uid=689237&view=niv"

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

        with open("virtuafoot_effectif.csv", mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data_perso)
        print(f"Fichier virtuafoot_effectif.csv généré ({len(data_perso)} lignes).")

        # ====================================================
        # 2. EXTRACTION DE L'EFFECTIF DU CAMARADE
        # ====================================================
        print("\n--- Accès et extraction de l'effectif du camarade ---")
        page.goto(URL_CAMARADE)
        page.wait_for_timeout(8000)  # Laisse le temps de charger

        print("Défilement de la page pour charger les données...")
        for _ in range(3):
            page.keyboard.press("PageDown")
            page.wait_for_timeout(1000)

        data_camarade = []
        
        # Ciblage direct des lignes de tableaux (tr) ou des cellules de la page club
        table_rows = page.locator("table tr, tr").all()
        print(f"Lignes de tableaux détectées sur la page du camarade : {len(table_rows)}")

        seen_camarade = set()
        for row in table_rows:
            try:
                text = row.inner_text().strip()
                if text:
                    cols = [c.strip() for c in text.split("\n") if c.strip()]
                    # On garde les lignes qui ont plusieurs colonnes (typiquement un joueur)
                    if len(cols) >= 3:
                        row_tuple = tuple(cols)
                        if row_tuple not in seen_camarade:
                            seen_camarade.add(row_tuple)
                            data_camarade.append(cols)
            except Exception:
                continue

        print(f"Fichier virtuafoot_effectif_camarade.csv généré ({len(data_camarade)} lignes valides).")

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
                    print("Synchronisation réussie !")
            except Exception as e:
                print(f"Erreur lors de la synchronisation Webhook : {e}")
        else:
            print("Aucun secret GOOGLE_WEBHOOK_URL détecté.")

        browser.close()

if __name__ == "__main__":
    run()
