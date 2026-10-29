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

            # On récupère uniquement les lignes qui se trouvent dans la liste des joueurs de l'entente 
            # (en évitant les widgets du stade, le VF Index, etc.)
            rows_data = page.evaluate("""
                () => {
                    // On cherche les lignes qui ressemblent à un joueur (présence d'un nom et d'une stat de forme)
                    const elements = Array.from(document.querySelectorAll("div[class*='css-g5y9jx']"));
                    return elements
                        .map(el => el.innerText.trim())
                        .filter(text => {
                            // Filtre strict pour exclure les menus du stade et les bruits de l'interface
                            if (!text.includes("%")) return false;
                            if (text.includes("STADIUM") || text.includes("VF Index") || text.includes("Seat distribution") || text.includes("Bridgestone")) return false;
                            if (text.length > 150) return false;
                            return true;
                        });
                }
            """)

            print(f"Joueurs valides trouvés pour {poste} : {len(rows_data)}")

            for row_text in rows_data:
                try:
                    lines = [l.strip() for l in row_text.split("\n") if l.strip()]
                    
                    if any("%" in l for l in lines):
                        filtered = [l for l in lines if l not in ["GC", "LI", "DEF", "MD", "MO", "AS", "AT", "O"] and not l.endswith("°")]
                        
                        if len(filtered) >= 2:
                            player_name = filtered[0] if not "%" in filtered[0] else filtered[1]
                            percentage = next((l for l in lines if "%" in l), "")
                            note = next((l for l in lines if l.replace('.', '').isdigit() and float(l.replace(',', '.')) < 100), "")
                            
                            if player_name and player_name not in seen_players and len(player_name) > 2 and "GOALKEEPER" not in player_name:
                                seen_players.add(player_name)
                                
                                player_info = [poste, player_name, percentage, note]
                                all_players_data.append(player_info)
                except Exception:
                    continue

        print(f"Total cumulé de joueurs récupérés : {len(all_players_data)}")

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
