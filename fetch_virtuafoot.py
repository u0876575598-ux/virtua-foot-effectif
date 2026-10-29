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

        # Attente souple de la redirection post-connexion
        page.wait_for_url("**/#*", timeout=15000)
        print("Connecté avec succès !")

        # Accès à la page de l'effectif
        print("Accès à la page de l'effectif...")
        page.goto("https://www.virtuafoot.com/#joueurs?view=niv")
        
        # Pause pour laisser le rendu React s'exécuter complètement
        page.wait_for_timeout(7000)

        data = []
        
        # Ciblage plus précis : on cherche les lignes conteneurs principales de l'effectif 
        # en filtrant sur les divs qui contiennent une structure de joueur
        rows = page.locator("div[class*='css-g5y9jx'][style*='background-color']").all()
        
        if not rows:
            # Sélecteur élargi de secours si le style spécifique change
            rows = page.locator("div[class*='css-g5y9jx']").all()

        seen_rows = set()
        for row in rows:
            text = row.inner_text().strip()
            if text:
                # Nettoyage et découpage des informations de la ligne
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                
                # On ne garde que les blocs qui ont une taille cohérente pour une ligne de joueur 
                # (évite de capturer les micro-éléments ou les en-têtes dupliqués)
                if 5 <= len(lines) <= 25:
                    row_tuple = tuple(lines)
                    if row_tuple not in seen_rows:
                        seen_rows.add(row_tuple)
                        data.append(lines)

        # Si l'extraction par blocs ne donne rien, on bascule sur une analyse textuelle propre
        if not data:
            print("Utilisation de la méthode de secours textuelle...")
            content_text = page.locator("#content, #divbody").inner_text()
            for line in content_text.split("\n"):
                cleaned = line.strip()
                if cleaned:
                    data.append([cleaned])

        # Sauvegarde locale du fichier CSV
        csv_filename = "virtuafoot_effectif.csv"
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        print(f"Fichier {csv_filename} généré avec succès ({len(data)} lignes enregistrées) !")

        # Synchronisation automatique vers Google Sheets via Webhook
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
