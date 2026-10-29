import os
import json
import urllib.request
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("VF_USERNAME")
PASSWORD = os.environ.get("VF_PASSWORD")
WEBHOOK_URL = os.environ.get("GOOGLE_WEBHOOK_URL")

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

        # Accès direct à la page de sélection de l'entente
        print("Accès à la page de sélection...")
        page.goto("https://www.virtuafoot.com/#entente?selectionneur_selectionner")
        
        # Pause pour laisser le rendu React charger tous les éléments de la page
        page.wait_for_timeout(8000)

        data = []
        seen_players = set()

        # On cible les lignes de blocs de joueurs de manière stricte
        rows = page.locator("div[class*='css-g5y9jx']").all()

        for row in rows:
            text = row.inner_text().strip()
            if text:
                # On découpe chaque ligne par saut de ligne pour obtenir les cellules individuelles
                cols = [c.strip() for c in text.split("\n") if c.strip()]
                
                # Filtrage rigoureux : on ne garde que les lignes qui correspondent à un vrai joueur 
                # (doit contenir un pourcentage de forme/intégration et un nom, soit au moins 4 à 15 éléments)
                if 4 <= len(cols) <= 20:
                    # Utilisation du nom du joueur (souvent en 2ème ou 3ème position) pour éviter les doublons
                    player_identifier = cols[1] if len(cols) > 1 else cols[0]
                    
                    if player_identifier not in seen_players and "GOALKEEPER" not in player_identifier and "DEFENDER" not in player_identifier:
                        seen_players.add(player_identifier)
                        data.append(cols)

        print(f"Nombre de joueurs uniques extraits : {len(data)}")

        # Synchronisation vers la feuille "Sélection" via le Webhook
        if WEBHOOK_URL and data:
            print("Synchronisation propre vers la feuille 'Sélection'...")
            try:
                payload_dict = {
                    "sheetName": "Sélection",
                    "data": data
                }
                payload = json.dumps(payload_dict).encode("utf-8")
                
                req = urllib.request.Request(
                    WEBHOOK_URL,
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req) as response:
                    print("Synchronisation réussie !")
            except Exception as e:
                print(f"Erreur lors de la synchronisation : {e}")
        else:
            print("Aucune donnée récupérée ou Webhook manquant.")

        browser.close()

if __name__ == "__main__":
    run()
