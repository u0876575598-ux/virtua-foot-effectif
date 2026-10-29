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

        data = []
        
        # On cible uniquement les lignes de joueurs situées dans le contenu principal (on évite le header/footer)
        # Sur Virtuafoot, les lignes de joueurs ont une structure bien précise avec des pourcentages de forme ou des notes
        player_rows = page.locator("#mainbrowse div[class*='css-g5y9jx'], #content div[class*='css-g5y9jx']").all()
        print(f"Lignes de joueurs détectées : {len(player_rows)}")

        seen_players = set()

        for i in range(len(player_rows)):
            try:
                # Clic sur la ligne du joueur via JavaScript
                page.evaluate(f"""
                    const rows = document.querySelectorAll("#mainbrowse div[class*='css-g5y9jx'], #content div[class*='css-g5y9jx']");
                    if (rows[{i}]) {{
                        rows[{i}].click();
                    }}
                """)
                page.wait_for_timeout(1500)

                # Extraction du texte de la ligne active
                current_rows = page.locator("#mainbrowse div[class*='css-g5y9jx'], #content div[class*='css-g5y9jx']").all()
                if i < len(current_rows):
                    text = current_rows[i].inner_text().strip()
                    if text:
                        cols = [c.strip() for c in text.split("\n") if c.strip()]
                        # On filtre pour ne garder que les lignes de joueurs valides (présence d'un nom et d'une stat/pourcentage)
                        cols = [c for c in cols if len(c) < 40 and "POINTS" not in c and "CLUBS" not in c and "ONLINE" not in c]

                        if len(cols) >= 3:
                            player_name = cols[1] if len(cols) > 1 else cols[0]
                            if player_name not in seen_players:
                                seen_players.add(player_name)
                                data.append(cols)

            except Exception as e:
                print(f"Erreur sur la ligne {i+1}: {e}")
                continue

        print(f"Total de joueurs propres récupérés : {len(data)}")

        # Synchronisation vers la feuille "Sélection" via le Webhook
        if WEBHOOK_URL and data:
            print("Synchronisation vers la feuille 'Sélection'...")
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
                    print("Synchronisation réussie !")
            except Exception as e:
                print(f"Erreur lors de la synchronisation : {e}")
        else:
            print("Aucune donnée récupérée ou Webhook manquant.")

        browser.close()

if __name__ == "__main__":
    run()
