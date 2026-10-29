import os
import time
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Récupération de vos identifiants depuis votre configuration existante
USERNAME = os.getenv("VF_USERNAME")
PASSWORD = os.getenv("VF_PASSWORD")

def run():
    with sync_playwright() as p:
        # Lancement du navigateur
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Connexion à Virtuafoot...")
        page.goto("https://www.virtuafoot.com/#login")

        # Remplissage automatique avec vos identifiants
        page.fill("input[name='username']", USERNAME)
        page.fill("input[name='password']", PASSWORD)
        page.click("button[type='submit']")

        # Attente de la connexion
        page.wait_for_timeout(3000)

        print("Accès à la page des niveaux du joueur...")
        page.goto("https://www.virtuafoot.com/#joueurs?view=niv")
        
        # Attente du chargement du tableau
        page.wait_for_selector("table")
        time.sleep(2)

        # Extraction du HTML
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Lecture du tableau
        table = soup.find("table")
        headers = [th.text.strip() for th in table.find_all("th")]
        
        rows = []
        for tr in table.find_all("tr")[1:]:  # Ignorer la ligne d'en-tête
            cols = [td.text.strip() for td in tr.find_all("td")]
            if cols:
                rows.append(cols)

        # Structuration dans un DataFrame Pandas
        df = pd.DataFrame(rows, columns=headers)

        # Nettoyage et conversion des statistiques en nombres
        stat_cols = [c for c in df.columns if c != "Nom"]
        for col in stat_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Calcul du Total des Points pour chaque joueur
        df['Total Points'] = df[stat_cols].sum(axis=1)

        # Export au format CSV
        output_file = "virtuafoot_effectif.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"Fichier généré avec succès : {output_file}")

        browser.close()

if __name__ == "__main__":
    run()
