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

        # Accès à la page de sélection / entente
        print("Accès à la page de sélection...")
        page.goto("https://www.virtuafoot.com/#entente?selectionneur_selectionner")
        page.wait_for_timeout(8000)

        all_players_data = []
        
        # Liste exacte des onglets de postes visibles sur l'interface
        postes = [
            "GARDIEN", 
            "LIBÉRO", 
            "DÉFENSEUR", 
            "MILIEU DÉFENSIF", 
            "MILIEU OFFENSIF", 
            "ATTAQUANT DE SOUTIEN", 
            "ATTAQUANT"
        ]

        seen_players = set()

        for poste in postes:
            print(f"Inspection de l'onglet : {poste}")
            try:
                # Clic sur l'onglet du poste correspondant via JavaScript pour éviter les interférences
                page.evaluate(f"""
                    const tabs = Array.from(document.querySelectorAll('div, span, a')).filter(el => el.textContent.trim().toUpperCase() === '{poste}');
                    if (tabs.length > 0) {{
                        tabs[0].click();
                    }}
                """)
                page.wait_for_timeout(3500) # Laisse le temps au contenu de charger
            except Exception as e:
                print(f"Impossible de cliquer sur l'onglet {poste}: {e}")
                continue

            # Récupération des lignes de joueurs pour ce poste précis
            rows = page.locator("div[class*='css-g5y9jx']").all()
            
            count_joueurs = 0
            for row in rows:
                try:
                    text = row.inner_text().strip()
                    if text:
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        
                        # Filtrage rigoureux : on ne garde que les lignes contenant un pourcentage de forme/intégration 
                        # et excluant les menus généraux
                        if any("%" in l for l in lines) and len(lines) >= 2:
                            player_name = lines[1] if len(lines) > 1 else lines[0]
                            
                            if player_name not in seen_players:
                                seen_players.add(player_name)
                                # On structure la ligne en y ajoutant le poste en premier élément
                                player_info = [poste] + lines
                                all_players_data.append(player_info)
                                count_joueurs += 1
                except Exception:
                    continue
                    
            print(f"-> {count_joueurs} joueurs récupérés pour {poste}.")

        print(f"Total cumulé des joueurs uniques : {len(all_players_data)}")

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
