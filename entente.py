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
            print(f"--- Inspection de l'onglet : {poste} ---")
            try:
                # Clic propre sur l'onglet du poste via son texte
                page.evaluate(f"""
                    const tabs = Array.from(document.querySelectorAll('div, span, a')).filter(el => el.textContent.trim().toUpperCase() === '{poste}');
                    if (tabs.length > 0) {{ tabs[0].click(); }}
                """)
                page.wait_for_timeout(3500)
            except Exception as e:
                print(f"Erreur onglet {poste}: {e}")
                continue

            # On récupère le nombre de joueurs dans cet onglet en cherchant les boutons radio de sélection
            player_count = page.evaluate("""
                () => {
                    const radios = document.querySelectorAll("input[type='radio']");
                    return radios.length;
                }
            """)

            print(f"Joueurs détectés pour {poste} : {player_count}")

            for i in range(player_count):
                try:
                    # On clique sur le bouton radio du joueur i pour charger ses stats
                    row_text = page.evaluate(f"""
                        () => {{
                            const radios = document.querySelectorAll("input[type='radio']");
                            if (radios[{i}]) {{
                                // On remonte au conteneur de la ligne pour cliquer dessus et récupérer tout le texte utile
                                let container = radios[{i}].closest("div[class*='css-']");
                                if (!container) container = radios[{i}].parentElement;
                                container.click();
                                return container.innerText.trim();
                            }}
                            return "";
                        }}
                    """)

                    # Pause pour laisser le temps à React de rafraîchir les données
                    page.wait_for_timeout(1000)

                    if row_text:
                        lines = [l.strip() for l in row_text.split("\n") if l.strip()]
                        
                        player_name = ""
                        percentage = ""
                        note = ""
                        
                        for line in lines:
                            if "%" in line and not percentage:
                                percentage = line
                            elif any(char.isdigit() for char in line) and len(line) <= 5 and not "%" in line:
                                try:
                                    val = float(line.replace(',', '.'))
                                    if val < 100 and not note:
                                        note = line
                                except ValueError:
                                    pass
                            elif len(line) > 2 and line not in ["GC", "LI", "DEF", "MD", "MO", "AS", "AT", "O", "SWEEPER", "GOALKEEPER", "DEFENDER"] and not line.endswith("°"):
                                if not player_name and "LA 7EME" not in line and "COMPAGNIE" not in line:
                                    player_name = line

                        if player_name and percentage and player_name not in seen_players:
                            seen_players.add(player_name)
                            player_info = [poste, player_name, percentage, note]
                            all_players_data.append(player_info)
                except Exception:
                    continue

        print(f"Total cumulé de joueurs récupérés avec clics : {len(all_players_data)}")

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
