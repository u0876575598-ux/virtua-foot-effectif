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

        # Accès à la page de sélection de l'entente
        print("Accès à la page de sélection...")
        page.goto("https://www.virtuafoot.com/#entente?selectionneur_selectionner")
        page.wait_for_timeout(8000)

        all_players_data = []
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
                # Clic sur l'onglet du poste
                page.evaluate(f"""
                    const tabs = Array.from(document.querySelectorAll('div, span, a')).filter(el => el.textContent.trim().toUpperCase() === '{poste}');
                    if (tabs.length > 0) {{ tabs[0].click(); }}
                """)
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"Erreur onglet {poste}: {e}")
                continue

            rows = page.locator("div[class*='css-g5y9jx']").all()
            
            for row in rows:
                try:
                    text = row.inner_text().strip()
                    if text:
                        # On nettoie et on fusionne les sauts de lignes parasites pour ne garder que le texte utile
                        lines = [l.strip() for l in text.split("\n") if l.strip() and l != "O"]
                        
                        # On cherche une ligne qui ressemble à un joueur (présence d'un pourcentage)
                        if any("%" in l for l in lines) and len(lines) >= 2:
                            # Extraction du nom du joueur (généralement le premier élément textuel non numérique)
                            valid_items = [l for l in lines if not l.endswith("°") and l not in ["GC", "LI", "DEF", "MD", "MO", "AS", "AT"]]
                            
                            if len(valid_items) >= 2:
                                player_name = valid_items[0] if not "%" in valid_items[0] else valid_items[1]
                                
                                if player_name not in seen_players and len(player_name) > 2 and "LA 7EME" not in player_name and "GOALKEEPER" not in player_name:
                                    seen_players.add(player_name)
                                    
                                    # On isole proprement : [Poste, Nom, Pourcentage, Note]
                                    percentage = next((l for l in lines if "%" in l), "")
                                    note = next((l for l in lines if l.replace('.', '').isdigit() and float(l.replace(',', '.')) < 100), "")
                                    
                                    player_info = [poste, player_name, percentage, note]
                                    all_players_data.append(player_info)
                except Exception:
                    continue

        print(f"Total de joueurs uniques propres : {len(all_players_data)}")

        # Synchronisation vers la feuille "Sélection" via le Webhook
        if WEBHOOK_URL and all_players_data:
            print("Synchronisation vers la feuille 'Sélection'...")
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
                    print("Synchronisation réussie !")
            except Exception as e:
                print(f"Erreur lors de la synchronisation : {e}")
        else:
            print("Aucune donnée récupérée ou Webhook manquant.")

        browser.close()

if __name__ == "__main__":
    run()
