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
                        data.append(lines)

        # Synchronisation vers la feuille "Sélection" via le Webhook
        if WEBHOOK_URL and data:
            print("Synchronisation vers la feuille 'Sélection' de Google Sheets...")
            try:
                # On encapsule les données avec le nom exact de la feuille cible
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
