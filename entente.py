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
        
        # On cible chaque conteneur de ligne de joueur
        rows = page.locator("div[class*='css-g5y9jx']").all()

        seen_rows = set()
        for row in rows:
            # On cherche tous les sous-éléments ou cellules à l'intérieur de la ligne
            cells = row.locator("div, span").all()
            
            row_data = []
            for cell in cells:
                # On évite d'attraper les conteneurs imbriqués globaux pour ne garder que les valeurs textuelles finales
                sub_text = cell.inner_text().strip()
                if sub_text and "\n" not in sub_text: # On prend les textes unitaires
                    if sub_text not in row_data:
                        row_data.append(sub_text)

            # Si on a détecté plusieurs caractéristiques pour ce joueur
            if len(row_data) >= 3:
                row_tuple = tuple(row_data)
                if row_tuple not in seen_rows:
                    seen_rows.add(row_tuple)
                    data.append(row_data)

        # Si la méthode cellule par cellule est trop fine et ne renvoie rien, on bascule sur un découpage propre des lignes
        if not data:
            print("Méthode fine infructueuse, basculement sur le découpage structuré...")
            for row in rows:
                text = row.inner_text().strip()
                if text:
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    if 4 <= len(lines) <= 25:
                        data.append(lines)

        # Synchronisation vers la feuille "Sélection" via le Webhook
        if WEBHOOK_URL and data:
            print("Synchronisation vers la feuille 'Sélection' de Google Sheets...")
            try:
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
