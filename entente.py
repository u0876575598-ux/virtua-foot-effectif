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

        # Accès à la page de l'entente
        print("Accès à la page de sélection...")
        page.goto("https://www.virtuafoot.com/#entente?selectionneur_selectionner")
        page.wait_for_timeout(8000)

        data = []
        
        # On récupère le nombre total de lignes de joueurs
        player_rows = page.locator("div[class*='css-g5y9jx']").all()
        print(f"Nombre de joueurs détectés dans la liste : {len(player_rows)}")

        for i in range(len(player_rows)):
            try:
                # Clic JavaScript direct sur l'élément i pour contourner les interférences de pointeur
                page.evaluate(f"""
                    const rows = document.querySelectorAll("div[class*='css-g5y9jx']");
                    if (rows[{i}]) {{
                        rows[{i}].click();
                    }}
                """)
                
                # Pause pour laisser le panneau/stats du joueur s'ouvrir ou se mettre à jour
                page.wait_for_timeout(2000)

                # Récupération du texte de la ligne active
                current_rows = page.locator("div[class*='css-g5y9jx']").all()
                if i < len(current_rows):
                    active_text = current_rows[i].inner_text().strip()
                    cols = [c.strip() for c in active_text.split("\n") if c.strip()]
                    cols = [c for c in cols if len(c) < 50]

                    if cols and cols not in data:
                        data.append(cols)

            except Exception as e:
                print(f"Erreur lors du traitement du joueur {i+1}: {e}")
                continue

        print(f"Total de lignes de joueurs récupérées : {len(data)}")

        # Synchronisation vers la feuille "Sélection" via le Webhook
        if WEBHOOK_URL and data:
            print("Synchronisation vers la feuille 'Sélection'...")
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
