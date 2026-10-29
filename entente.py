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
        
        # On récupère tous les éléments cliquables représentant les joueurs dans la liste
        # Sur Virtuafoot, chaque ligne de joueur permet un clic pour voir le profil/stats
        player_rows = page.locator("div[class*='css-g5y9jx']").all()
        print(f"Nombre de joueurs détectés dans la liste : {len(player_rows)}")

        for i in range(len(player_rows)):
            try:
                # On recharge la liste à chaque tour pour éviter les erreurs de DOM obsolète
                current_rows = page.locator("div[class*='css-g5y9jx']").all()
                if i >= len(current_rows):
                    break
                
                row = current_rows[i]
                
                # Récupération du texte de base de la ligne avant le clic
                base_text = row.inner_text().strip()
                if not base_text:
                    continue

                # CLIC sur le joueur pour charger ses stats détaillées
                row.click()
                # Pause pour laisser le panneau ou les stats du joueur s'actualiser à l'écran
                page.wait_for_timeout(2500)

                # Extraction des données textuelles de la ligne (ou de la zone active mise à jour)
                # On capture les éléments visibles de la ligne active
                active_text = row.inner_text().strip()
                cols = [c.strip() for c in active_text.split("\n") if c.strip()]
                
                # Nettoyage pour garder un format de ligne propre
                cols = [c for c in cols if len(c) < 50]

                if cols and cols not in data:
                    data.append(cols)

            except Exception as e:
                print(f"Erreur lors du clic sur le joueur {i+1}: {e}")
                continue

        print(f"Total de lignes de joueurs récupérées avec clics : {len(data)}")

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
