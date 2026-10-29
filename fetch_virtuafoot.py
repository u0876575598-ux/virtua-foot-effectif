import os
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("VF_USERNAME")
PASSWORD = os.environ.get("VF_PASSWORD")

def run():
    with sync_playwright() as p:
        # Lancement du navigateur
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()

        print("Connexion à Virtuafoot...")
        page.goto("https://www.virtuafoot.com/")

        # Attente du formulaire de connexion
        page.wait_for_selector("form", timeout=10000)
        
        # Remplissage des champs avec des sélecteurs génériques robustes
        page.locator("input[type='text'], input[type='email']").first.fill(USERNAME)
        page.locator("input[type='password']").first.fill(PASSWORD)
        
        # Validation
        page.locator("button[type='submit'], input[type='submit']").first.click()

        # Attente post-connexion (ajustez selon votre redirection, par ex. 'joueurs')
        page.wait_for_url("**/joueurs*", timeout=15000)
        print("Connecté avec succès !")
        
        # --- Insérez ici la suite de votre code pour extraire les données et générer le CSV ---

        browser.close()

if __name__ == "__main__":
    run()
