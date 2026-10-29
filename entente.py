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
                # Clic sur l'onglet du poste
                page.evaluate(f"""
                    const tabs = Array.from(document.querySelectorAll('div, span, a')).filter(el => el.textContent.trim().toUpperCase() === '{poste}');
                    if (tabs.length > 0) {{ tabs[0].click(); }}
                """)
                page.wait_for_timeout(3500)
            except Exception as e:
                print(f"Erreur onglet {poste}: {e}")
                continue

            # On récupère le nombre de joueurs dans la liste pour ce poste
            row_count = page.evaluate("""
                () => document.querySelectorAll("div[class*='css-g5y9jx']").length
            """)
            
            print(f"{row_count} lignes trouvées pour {poste}.")

            for i in range(row_count):
                try:
                    # Clic chirurgical par index sur chaque ligne de joueur pour ouvrir/charger ses stats
                    page.evaluate(f"""
                        () => {{
                            const rows = document.querySelectorAll("div[class*='css-g5y9jx']");
                            if (rows[{i}]) {{
                                rows[{i}].click();
                            }}
                        }}
                    """)
                    # Petite pause pour laisser l'interface React réagir au clic du joueur
                    page.wait_for_timeout(1500)

                    # Récupération du texte de la ligne active après le clic
                    row_data = page.evaluate(f"""
                        () => {{
                            const rows = document.querySelectorAll("div[class*='css-g5y9jx']");
                            if (rows[{i}]) {{
                                return rows[{i}].innerText.trim();
                            }}
                            return "";
                        }}
                    """)

                    if row_data:
                        lines = [l.strip() for l in row_data.split("\n") if l.strip()]
                        
                        # Filtrage pour valider que c'est bien une ligne de joueur (contient un '%')
                        if any("%" in l for l in lines):
                            filtered = [l for l in lines if l not in ["GC", "LI", "DEF", "MD", "MO", "AS", "AT", "O"] and not l.endswith("°")]
                            
                            if len(filtered) >= 2:
                                player_name = filtered[0] if not "%" in filtered[0] else (filtered[1] if len(filtered) > 1 else "")
                                percentage = next((l for l in lines if "%" in l), "")
                                note = next((l for l in lines if l.replace('.', '').isdigit() and float(l.replace(',', '.')) < 100), "")
                                
                                if player_name and player_name not in seen_players and len(player_name) > 2 and "GOALKEEPER" not in player_name:
                                    seen_players.add(player_name)
                                    
                                    # Ligne propre : [Poste, Nom, Pourcentage, Note]
                                    player_info = [poste, player_name, percentage, note]
                                    all_players_data.append(player_info)
                except Exception as e:
                    print(f"Erreur sur la ligne {i}: {e}")
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
