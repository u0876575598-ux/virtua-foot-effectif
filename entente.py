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
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        
                        # On ne garde que les lignes qui contiennent un pourcentage (signature d'un joueur)
                        if any("%" in l for l in lines) and len(lines) >= 2:
                            # Extraction propre : on filtre les bruits et on garde les vraies valeurs utiles
                            clean_lines = [l for l in lines if l not in ["GC", "LI", "DEF", "MD", "MO", "AS", "AT", "O", ""] and not l.endswith("°")]
                            
                            if clean_lines:
                                player_name = clean_lines[0] if not any(c.endswith("%") for c in clean_lines[0]) else clean_lines[1] if len(clean_lines) > 1 else "Inconnu"
                                
                                if player_name not in seen_players and len(player_name) > 2 and "LA 7EME" not in player_name:
                                    seen_players.add(player_name)
                                    
                                    # Construction d'une ligne propre : [Poste, Nom, et toutes les stats détectées]
                                    player_info = [poste] + clean_lines
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
