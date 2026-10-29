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

        # Accès à la page de la sélection / entente
        print("Accès à la page de sélection...")
        page.goto("https://www.virtuafoot.com/#entente?selectionneur_selectionner")
        page.wait_for_timeout(5000)

        all_players_data = []
        
        # Liste des onglets de postes visibles sur l'interface
        postes = [
            "GARDIEN", 
            "LIBÉRO", 
            "DÉFENSEUR", 
            "MILIEU DÉFENSIF", 
            "MILIEU OFFENSIF", 
            "ATTAQUANT DE SOUTIEN", 
            "ATTAQUANT"
        ]

        for poste in postes:
            print(f"Inspection de l'onglet : {poste}")
            try:
                # Clic sur l'onglet du poste correspondant
                tab = page.locator(f"text={poste}").first
                if tab.is_visible():
                    tab.click()
                    page.wait_for_timeout(3000) # Laisse le temps au contenu de charger
                else:
                    continue
            except Exception as e:
                print(f"Impossible de cliquer sur l'onglet {poste}: {e}")
                continue

            # Récupération de tous les joueurs visibles dans cet onglet
            rows = page.locator("div[class*='css-g5y9jx']").all()
            
            for i in range(len(rows)):
                try:
                    # On recrée la liste des lignes à chaque tour pour éviter les erreurs de rechargement DOM
                    current_rows = page.locator("div[class*='css-g5y9jx']").all()
                    if i >= len(current_rows):
                        break
                    
                    row = current_rows[i]
                    text = row.inner_text().strip()
                    
                    if text:
                        # Si on souhaite cliquer sur le joueur pour ouvrir sa fiche / ses détails :
                        # row.click()
                        # page.wait_for_timeout(1000)
                        
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        if len(lines) >= 2:
                            # On ajoute le poste en première info pour structurer
                            player_info = [poste] + lines
                            if player_info not in all_players_data:
                                all_players_data.append(player_info)
                except Exception as row_err:
                    print(f"Erreur sur un joueur de l'onglet {poste}: {row_err}")
                    continue

        # Synchronisation vers la feuille "Sélection" via le Webhook
        if WEBHOOK_URL and all_players_data:
            print("Synchronisation globale vers la feuille 'Sélection'...")
            try:
                payload_dict = {
                    "sheetName": "Sélection",
                    "data": all_players_data
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
