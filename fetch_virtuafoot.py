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

        print("Navigation vers l'effectif via le menu...")
        # Simulation d'un clic réel sur le menu "Joueurs" pour déclencher le chargement AJAX
        try:
            page.locator("a:has-text('Joueurs'), a[href*='joueurs']").first.click()
        except Exception:
            # Fallback si le lien direct par texte échoue
            page.goto("https://www.virtuafoot.com/#joueurs")

        # Pause pour laisser le temps au contenu AJAX de s'injecter dans la page
        page.wait_for_timeout(5000)

        # Recherche des tableaux présents sur la page
        tables = page.locator("table").all()
        print(f"Nombre de tableaux détectés : {len(tables)}")

        data = []
        if tables:
            # Extraction du premier tableau trouvé (l'effectif)
            rows = tables[0].locator("tr").all()
            for row in rows:
                cells = row.locator("th, td").all_text_contents()
                cleaned_cells = [cell.strip().replace("\n", " ") for cell in cells if cell.strip()]
                if cleaned_cells:
                    data.append(cleaned_cells)

        # Si le premier tableau est vide, on récupère toutes les lignes de la page
        if not data:
            print("Tentative de récupération globale des lignes...")
            rows = page.locator("tr").all()
            for row in rows:
                cells = row.locator("th, td").all_text_contents()
                cleaned_cells = [cell.strip().replace("\n", " ") for cell in cells if cell.strip()]
                if cleaned_cells:
                    data.append(cleaned_cells)

        # Sauvegarde du fichier CSV pour GitHub Actions
        csv_filename = "virtuafoot_effectif.csv"
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        print(f"Fichier {csv_filename} généré avec succès ({len(data)} lignes enregistrées) !")
        browser.close()

if __name__ == "__main__":
    run()
    
