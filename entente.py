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
        print("Accès à la page de l'entente...")
        page.goto("https://www.virtuafoot.com/#entente?selectionneur_selectionner")
        
        # Pause pour laisser le rendu React charger les données
        page.wait_for_timeout(7000)

        data = []
        
        # Ciblage strict des lignes de tableaux (tr) et de leurs cellules (td/th) pour structurer proprement les colonnes
        rows = page.locator("table tr").all()
        if not rows:
            rows = page.locator("tr").all()

        for row in rows:
            cells = row.locator("td, th").all()
            if cells:
                row_data = [cell.inner_text().strip() for cell in cells]
                # On ne garde que les lignes qui contiennent des données exploitables
                if len(row_data) >= 2:
                    data.append(row_data)

        # Synchronisation vers la feuille "Sélection" via le Webhook
        if WEBHOOK_URL and data:
            print("Synchronisation vers la feuille 'Sélection' de Google Sheets...")
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
                    print("Synchronisation de la feuille 'Sélection' réussie !")
            except Exception as e:
                print(f"Erreur lors de la synchronisation : {e}")
        else:
            print("Aucune donnée récupérée ou Webhook manquant.")

        browser.close()

if __name__ == "__main__":
    run()
