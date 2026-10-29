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

        # Accès à la page des joueurs via la navigation SPA interne
        print("Récupération de l'effectif...")
        
        # Navigation vers l'ancrage interne
        page.goto("https://www.virtuafoot.com/#joueurs?view=niv")
        
        # Attente active du chargement du contenu dans le DOM
        page.wait_for_timeout(4000) # Pause de 4s pour laisser le script AJAX remplir le tableau
        
        # Si la table n'apparaît pas, on essaie de forcer le clic sur le lien 'Joueurs' du menu
        if page.locator("tr").count() < 2:
            page.locator("a[href*='joueurs']").first.click()
            page.wait_for_timeout(3000)

        # Récupération de toutes les lignes du tableau
        rows = page.locator("tr").all()
        data = []

        for row in rows:
            cells = row.locator("th, td").all_text_contents()
            cleaned_cells = [cell.strip().replace("\n", " ") for cell in cells if cell.strip()]
            if cleaned_cells:
                data.append(cleaned_cells)

        # Sauvegarde dans le CSV
        csv_filename = "virtuafoot_effectif.csv"
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        print(f"Fichier {csv_filename} généré avec succès ({len(data)} lignes enregistrées) !")
        browser.close()

if __name__ == "__main__":
    run()
