import os
import csv
import json
import urllib.request
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("VF_USERNAME")
PASSWORD = os.environ.get("VF_PASSWORD")
WEBHOOK_URL = os.environ.get("GOOGLE_WEBHOOK_URL")

# Les 27 URL exactes de l'effectif du camarade
URLS_CAMARADE = [
    "https://www.virtuafoot.com/#joueur?jid=584853",
    "https://www.virtuafoot.com/#joueur?jid=552785",
    "https://www.virtuafoot.com/#joueur?jid=635131",
    "https://www.virtuafoot.com/#joueur?jid=600076",
    "https://www.virtuafoot.com/#joueur?jid=557417",
    "https://www.virtuafoot.com/#joueur?jid=593718",
    "https://www.virtuafoot.com/#joueur?jid=612050",
    "https://www.virtuafoot.com/#joueur?jid=591503",
    "https://www.virtuafoot.com/#joueur?jid=594089",
    "https://www.virtuafoot.com/#joueur?jid=648691",
    "https://www.virtuafoot.com/#joueur?jid=562630",
    "https://www.virtuafoot.com/#joueur?jid=672684",
    "https://www.virtuafoot.com/#joueur?jid=647352",
    "https://www.virtuafoot.com/#joueur?jid=642931",
    "https://www.virtuafoot.com/#joueur?jid=599839",
    "https://www.virtuafoot.com/#joueur?jid=633740",
    "https://www.virtuafoot.com/#joueur?jid=643289",
    "https://www.virtuafoot.com/#joueur?jid=672333",
    "https://www.virtuafoot.com/#joueur?jid=581812",
    "https://www.virtuafoot.com/#joueur?jid=656073",
    "https://www.virtuafoot.com/#joueur?jid=644830",
    "https://www.virtuafoot.com/#joueur?jid=622252",
    "https://www.virtuafoot.com/#joueur?jid=649331",
    "https://www.virtuafoot.com/#joueur?jid=624501",
    "https://www.virtuafoot.com/#joueur?jid=664507",
    "https://www.virtuafoot.com/#joueur?jid=648968",
    "https://www.virtuafoot.com/#joueur?jid=637479"
]

def clean_player_data(raw_text_lines):
    """Nettoie et formate les lignes d'une fiche joueur pour garder uniquement les stats et infos utiles."""
    cleaned = []
    # Mots-clés parasites à ignorer s'ils apparaissent dans les lignes isolées
    ignore_words = ["Ouvrir des négociations", "Club formateur", "Palmarès", "Historique", "Matchs", "Buteurs"]
    
    for line in raw_text_lines:
        line_str = line.strip()
        if line_str and not any(w in line_str for w in ignore_words):
            cleaned.append(line_str)
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
        # 2. EXTRACTION DÉTAILLÉE DES 27 JOUEURS DU CAMARADE
        # ====================================================
        print(f"\n--- Extraction des {len(URLS_CAMARADE)} joueurs du camarade ---")
        data_camarade = []
        seen_camarade = set()

        for idx, url in enumerate(URLS_CAMARADE, 1):
            try:
                page.goto(url)
                # Attente active que le bloc de stats ou la fiche soit complètement chargé
                page.wait_for_selector("div[class*='css-g5y9jx']", timeout=12000)
                page.wait_for_timeout(1500)

                # Récupération de tous les blocs de texte structurés de la fiche du joueur
                blocks = page.locator("div[class*='css-g5y9jx']").all()
                player_raw_lines = []
                for block in blocks:
                    t = block.inner_text().strip()
                    if t:
                        sub_lines = [s.strip() for s in t.split("\n") if s.strip()]
                        player_raw_lines.extend(sub_lines)

                # Si les blocs ciblés sont vides, on prend le texte global de la page
                if not player_raw_lines:
                    body_text = page.locator("body").inner_text()
                    if body_text:
                        player_raw_lines = [l.strip() for l in body_text.split("\n") if l.strip()]

                formatted_player = clean_player_data(player_raw_lines)

                if formatted_player:
                    row_tuple = tuple(formatted_player)
                    if row_tuple not in seen_camarade:
                        seen_camarade.add(row_tuple)
                        data_camarade.append(formatted_player)
                print(f"Joueur {idx}/27 extrait ({len(formatted_player)} attributs).")
            except Exception as e:
                print(f"Erreur sur le joueur {idx} ({url}): {e}")

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
