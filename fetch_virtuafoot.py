import os
import csv
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

        # Attente souple de la redirection post-connexion (quel que soit le hash #news, #home, etc.)
        page.wait_for_url("**/#*", timeout=15000)
        print("Connecté avec succès !")

        # Accès à la page de l'effectif
        print("Accès à la page de l'effectif...")
        page.goto("https://www.virtuafoot.com/#joueurs?view=niv")
        
        # Pause pour laisser le rendu React/JavaScript s'exécuter complètement
        page.wait_for_timeout(7000)

        data = []
        
        # Récupération des blocs de lignes basés sur la structure React de l'interface
        rows = page.locator("div[class*='css-g5y9jx']").all()
        
        for row in rows:
            text = row.inner_text().strip()
            if text:
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if len(lines) >= 2 and lines not in data:
                    data.append(lines)

        # Méthode de secours textuelle si les blocs sont insuffisants
        if len(data) < 2:
            print("Utilisation de la méthode de secours textuelle...")
            content_text = page.locator("#content, #divbody").inner_text()
            for line in content_text.split("\n"):
                cleaned = line.strip()
                if cleaned:
                    data.append([cleaned])

        # Sauvegarde locale du fichier CSV (utilisé par Git/GitHub Actions)
        csv_filename = "virtuafoot_effectif.csv"
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        print(f"Fichier {csv_filename} généré avec succès ({len(data)} lignes enregistrées) !")

        # Synchronisation automatique vers Google Sheets via Webhook (si configuré)
        if WEBHOOK_URL:
            print("Synchronisation avec Google Sheets...")
            try:
                payload = json.dumps(data).encode("utf-8")
                req = urllib.request.Request(
                    WEBHOOK_URL,
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req) as response:
                    print("Synchronisation Google Sheets réussie !")
            except Exception as e:
                print(f"Erreur lors de la synchronisation Google Sheets : {e}")
        else:
            print("Aucun secret GOOGLE_WEBHOOK_URL détecté, synchronisation Google Sheets ignorée.")

        browser.close()

if __name__ == "__main__":
    run()
