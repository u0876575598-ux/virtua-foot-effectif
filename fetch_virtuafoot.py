import os
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("VF_USERNAME")
PASSWORD = os.environ.get("VF_PASSWORD")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()

        print("Connexion à Virtuafoot...")
        page.goto("https://www.virtuafoot.com/")

        # Remplissage des identifiants dans le formulaire masqué
        page.fill("form#login input[type='text'], form#login input[name='login'], input[name='login']", USERNAME)
        page.fill("form#login input[type='password'], form#login input[name='pass'], input[name='pass']", PASSWORD)
        
        # Soumission et validation de la connexion
        page.locator("form#login button[type='submit'], form#login input[type='submit'], button:has-text('Connexion')").first.click()

        # Attente que la connexion soit effective (par exemple l'apparition de la section news ou home)
        page.wait_for_url("**/#news*", timeout=15000)
        print("Connecté avec succès !")

        # Navigation directe vers la page des joueurs demandée
        print("Récupération de l'effectif...")
        page.goto("https://www.virtuafoot.com/joueurs?view=niv")
        
        # --- Insérez ici votre logique de scraping du tableau et d'écriture dans le fichier CSV ---
        # Exemple de base :
        # html_content = page.content()
        # avec pandas ou BeautifulSoup pour extraire les données et générer 'virtuafoot_effectif.csv'

        browser.close()

if __name__ == "__main__":
    run()
