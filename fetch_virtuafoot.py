import os
import csv
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("VF_USERNAME")
PASSWORD = os.environ.get("VF_PASSWORD")

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

        # Attente de la connexion
        page.wait_for_url("**/#news*", timeout=15000)
        print("Connecté avec succès !")

        # Accès à la page des joueurs
        print("Récupération de l'effectif...")
        page.goto("https://www.virtuafoot.com/joueurs?view=niv")
        
        # Attente de la présence du contenu du tableau (on élargit au conteneur ou à n'importe quel tableau présent)
        page.wait_for_load_selector = page.wait_for_selector("table, .tableau, div#content", timeout=15000)

        # Extraction des données du tableau principal de l'effectif
        rows = page.locator("table tr").all()
        data = []

        for row in rows:
            cells = row.locator("th, td").all_text_contents()
            cleaned_cells = [cell.strip().replace("\n", " ") for cell in cells if cell.strip()]
            if cleaned_cells:
                data.append(cleaned_cells)

        # Sauvegarde dans le CSV attendu par GitHub Actions
        csv_filename = "virtuafoot_effectif.csv"
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        print(f"Fichier {csv_filename} généré avec succès ({len(data)} lignes enregistrées) !")
        browser.close()

if __name__ == "__main__":
    run()
