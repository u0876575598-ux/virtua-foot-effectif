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
        
        # Pause plus longue pour garantir le rendu complet de l'interface React
        page.wait_for_timeout(8000)

        all_players_data = []
        
        # Mots-clés des onglets de postes
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
                # Recherche multi-sélecteurs pour cliquer sur l'onglet
                # 1. Par texte exact ou insensible à la casse
                # 2. Par élément cliquable contenant le texte
                tab_locator = page.locator(f"xpath=//*[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{poste}')]").first

                if tab_locator.is_visible():
                    tab_locator.click()
                    page.wait_for_timeout(3000)
                else:
                    # Essai de clic forcé en JavaScript si le ciblage standard échoue
                    page.evaluate(f"""
                        const el = Array.from(document.querySelectorAll('*')).find(e => e.textContent.trim().toUpperCase() === '{poste}');
                        if (el) el.click();
                    """)
                    page.wait_for_timeout(3000)

            except Exception as e:
                print(f"Erreur lors du clic sur l'onglet {poste}: {e}")

            # Récupération des lignes de joueurs affichées sous cet onglet
            rows = page.locator("div[class*='css-g5y9jx']").all()
            if not rows:
                rows = page.locator("div[class*='row'], tr").all()

            count_joueurs = 0
            for row in rows:
                try:
                    text = row.inner_text().strip()
                    if text:
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        # On vérifie que la ligne contient bien des données de joueurs
                        if len(lines) >= 3 and poste not in lines[0]:
                            player_info = [poste] + lines
                            if player_info not in all_players_data:
                                all_players_data.append(player_info)
                                count_joueurs += 1
                except Exception:
                    continue
                    
            print(f"-> {count_joueurs} joueurs récupérés pour {poste}.")

        print(f"Total cumulé des lignes trouvées : {len(all_players_data)}")

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
