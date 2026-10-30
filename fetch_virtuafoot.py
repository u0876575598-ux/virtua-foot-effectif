import os
import csv
import json
import urllib.request
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("VF_USERNAME")
PASSWORD = os.environ.get("VF_PASSWORD")
WEBHOOK_URL = os.environ.get("GOOGLE_WEBHOOK_URL")

URL_CAMARADE_EFFECTIF = "https://www.virtuafoot.com/#club?uid=689237&view=niv"

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
                if 4 <= len(lines) <= 25:
                    row_tuple = tuple(lines)
                    if row_tuple not in seen_rows:
                        seen_rows.add(row_tuple)
                        data_perso.append(lines)

        with open("virtuafoot_effectif.csv", mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data_perso)
        print(f"Fichier virtuafoot_effectif.csv généré ({len(data_perso)} lignes).")

        # ====================================================
        # 2. EXTRACTION DE L'EFFECTIF DU CAMARADE (PARCOURS INDIVIDUEL)
        # ====================================================
        print("\n--- Accès et extraction détaillée de l'effectif du camarade ---")
        page.goto(URL_CAMARADE_EFFECTIF)
        page.wait_for_timeout(8000)

        print("Défilement pour charger tous les joueurs...")
        for _ in range(4):
            page.keyboard.press("PageDown")
            page.wait_for_timeout(1000)

        # Recherche élargie de tous les liens pointant vers des fiches de joueurs
        player_links = []
        links_locator = page.locator("a")
        count = links_locator.count()
        
        for i in range(count):
            try:
                href = links_locator.nth(i).get_attribute("href")
                if href and ("#joueur" in href or "joueur" in href) and href not in player_links:
                    player_links.append(href)
            except Exception:
                continue

        print(f"{len(player_links)} joueurs détectés chez le camarade. Extraction des fiches...")

        data_camarade = []
        seen_camarade = set()

        for link in player_links:
            try:
                full_url = f"https://www.virtuafoot.com/{link}" if not link.startswith("http") else link
                page.goto(full_url)
                page.wait_for_timeout(2000)

                # Extraction des informations de la fiche du joueur
                stat_blocks = page.locator("div[class*='css-g5y9jx'], div[class*='row']").all()
                player_data = []
                
                for block in stat_blocks:
                    t = block.inner_text().strip()
                    if t:
                        sub_lines = [s.strip() for s in t.split("\n") if s.strip()]
                        player_data.extend(sub_lines)

                # Nettoyage et formatage à plat pour la ligne du tableau
                flat_player = []
                for item in player_data:
                    flat_player.extend([sub.strip() for sub in item.split("\n") if sub.strip()])

                if len(flat_player) >= 4:
                    row_tuple = tuple(flat_player)
                    if row_tuple not in seen_camarade:
                        seen_camarade.add(row_tuple)
                        data_camarade.append(flat_player)
            except Exception as e:
                print(f"Erreur sur un joueur : {e}")
                continue

        with open("virtuafoot_effectif_camarade.csv", mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data_camarade)
        print(f"Fichier virtuafoot_effectif_camarade.csv généré ({len(data_camarade)} fiches détaillées).")

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
