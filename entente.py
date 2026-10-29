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
                # Clic propre sur l'onglet du poste
                page.evaluate(f"""
                    const tabs = Array.from(document.querySelectorAll('div, span, a')).filter(el => el.textContent.trim().toUpperCase() === '{poste}');
                    if (tabs.length > 0) {{ tabs[0].click(); }}
                """)
                page.wait_for_timeout(3500)
            except Exception as e:
                print(f"Erreur onglet {poste}: {e}")
                continue

            # On extrait proprement les lignes en ciblant uniquement le tableau central des joueurs
            rows_data = page.evaluate("""
                () => {
                    const elements = Array.from(document.querySelectorAll("div[class*='css-g5y9jx']"));
                    let results = [];
                    elements.forEach(el => {
                        const text = el.innerText.trim();
                        // On cherche les blocs qui contiennent un nom de joueur et des stats sur plusieurs lignes
                        if (text && text.includes("%") && text.split("\\n").length >= 3) {
                            if (!text.includes("STADIUM") && !text.includes("VF Index") && !text.includes("Seat distribution")) {
                                results.push(text);
                            }
                        }
                    });
                    return results;
                }
            """)

            print(f"Joueurs valides trouvés pour {poste} : {len(rows_data)}")

            for row_text in rows_data:
                try:
                    lines = [l.strip() for l in row_text.split("\n") if l.strip()]
                    
                    # Extraction chirurgicale : on cherche le nom, le pourcentage et la note parmi les lignes du bloc
                    player_name = ""
                    percentage = ""
                    note = ""
                    
                    for line in lines:
                        if "%" in line:
                            percentage = line
                        elif any(char.isdigit() for char in line) and len(line) <= 5 and not "%" in line:
                            # La note est généralement un nombre court (ex: 93, 90, etc.)
                            if float(line.replace(',', '.')) < 100:
                                note = line
                        elif len(line) > 2 and not line in ["GC", "LI", "DEF", "MD", "MO", "AS", "AT", "O"] and not line.endswith("°"):
                            if not player_name and "LA 7EME" not in line and "GOALKEEPER" not in line:
                                player_name = line

                    if player_name and percentage and player_name not in seen_players:
                        seen_players.add(player_name)
                        player_info = [poste, player_name, percentage, note]
                        all_players_data.append(player_info)
                except Exception:
                    continue

        print(f"Total cumulé de joueurs propres récupérés : {len(all_players_data)}")

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
