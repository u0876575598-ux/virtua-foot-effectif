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

        # On cible directement les champs du formulaire de login par leur nom ou identifiant dans le DOM (même masqué)
        page.fill("form#login input[type='text'], form#login input[name='login'], input[name='login']", USERNAME)
        page.fill("form#login input[type='password'], form#login input[name='pass'], input[name='pass']", PASSWORD)
        
        # Soumission du formulaire
        page.locator("form#login button[type='submit'], form#login input[type='submit'], button:has-text('Connexion')").first.click()

        # Attente de la redirection vers l'espace connecté (ex: page joueurs)
        page.wait_for_url("**/joueurs*", timeout=15000)
        print("Connecté avec succès !")
        
        # --- Insérez la suite de votre code de scraping et d'export CSV ici ---

        browser.close()

if __name__ == "__main__":
    run()
