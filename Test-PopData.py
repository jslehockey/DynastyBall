import openpyxl
import random
import os
import sqlite3
import pandas as pd

def populate_dummy_data(file_path):
    print("--- Step 1: Checking Excel Data ---")
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Run the schema builder first.")
        return False

    wb = openpyxl.load_workbook(file_path)
    data_added = False

    # --- 1. Worlds ---
    if "Worlds" in wb.sheetnames and wb["Worlds"].cell(row=2, column=1).value is None:
        wb["Worlds"].append(["Alpha", "Alpha Universe", "Yes"])
        data_added = True

    # --- 2. Teams ---
    teams_data = [
        ("Alpha-0001", "Washington", "DiamondBucs", "Jim", "Active"),
        ("Alpha-0002", "Boston", "Minutemen", "Jake", "Active"),
        ("Alpha-0003", "Miami", "Stormers", "Rafael", "Active"),
        ("Alpha-0004", "Vaduz", "Mountaineers", "ETR", "Active"),
        ("Alpha-0005", "Anchorage", "Aces", "JCW", "Active"),
        ("Alpha-0006", "New York", "Team6", "Manager6", "Active"),
        ("Alpha-0007", "Athens", "Bobcats", "Jackson", "Active"),
        ("Alpha-0008", "Long Island", "Team8", "Manager8", "Active")
    ]
    
    team_ids = []
    if "Teams" in wb.sheetnames:
        ws = wb["Teams"]
        if ws.cell(row=2, column=1).value is None:
            for t in teams_data:
                team_ids.append(t[0])
                ws.append([t[0], "Alpha", t[1], t[2], t[3], t[4], f"{t[3]}@test.com", "pw123", "Active", "#000000", "#FFFFFF", 50])
            data_added = True
        else:
            for row in ws.iter_rows(min_row=2, max_col=1, values_only=True):
                if row[0]: team_ids.append(row[0])

    # --- 3. Parks & Financials ---
    if "Parks" in wb.sheetnames and wb["Parks"].cell(row=2, column=1).value is None:
        for idx, t_id in enumerate(team_ids):
            wb["Parks"].append([f"Park-{idx+1}", t_id, f"Stadium {idx+1}", 5, 200, 150, 1000000] + [random.randint(12, 400) for _ in range(14)])
        data_added = True

    if "Team_Financials" in wb.sheetnames and wb["Team_Financials"].cell(row=2, column=1).value is None:
        for t_id in team_ids:
            wb["Team_Financials"].append([t_id, 2026, 15000000, 25, 4500000, 0, 2000000, 500000, 8000000])
        data_added = True

    # --- 4. Players, Ratings, Contracts & STATS ---
    if "Players_Base" in wb.sheetnames and wb["Players_Base"].cell(row=2, column=1).value is None:
        ws_base = wb["Players_Base"]
        ws_ratings = wb["Player_Ratings"]
        ws_contracts = wb["Contracts"]
        ws_hit_stats = wb["Stats_Hitting"]
        ws_pit_stats = wb["Stats_Pitching"]
        
        first_names = ["James", "David", "Chris", "Mike", "Alex", "Jim", "Cy", "Hank", "Brian", "Jackie"]
        last_names = ["Johnson", "Gehrig", "Walker", "Thomas", "Jones", "Ramirez", "Anderson", "Griffey", "Moore"]
        positions = ["P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]
        
        hit_archs = ["Jeter", "Schmidt", "Molina", "Kent", "Rickey", "Gwynn", "Zobrist", "Gehrig", "Mauer", "Mays", "Ichiro"]
        pit_archs = ["Ryan", "Wakefield", "Buehrle", "Pedro", "Rivera", "Gagne", "Hader", "Fingers", "Lincecum", "Gibson"]
        
        all_traits = ["Platoon Punisher", "Speed Demon", "Launch Angle God", "Unfazed", "Gold Glover", "Pitch to Contact", "Escape Artist", "Lights Out", "Marathon Man", "Rubber Arm", "Putaway Pitcher", "Groundball Guru", "Table Setter", "Clutch"]

        player_counter = 1
        
        for t_id in team_ids:
            for _ in range(15):
                p_id = f"2026{str(player_counter).zfill(8)}"
                fname = random.choice(first_names)
                lname = random.choice(last_names)
                pos = random.choice(positions)
                age = random.randint(19, 35)
                
                arch = random.choice(pit_archs) if pos == "P" else random.choice(hit_archs)
                
                # 1. Base Data
                ws_base.append([p_id, fname, lname, 27, 32, arch])
                
                # 2. Ratings & Psyche
                t_count = random.choices([0, 1, 2, 3], weights=[40, 30, 20, 10])[0]
                p_traits = random.sample(all_traits, t_count)
                t1 = p_traits[0] if t_count > 0 else ""
                t2 = p_traits[1] if t_count > 1 else ""
                t3 = p_traits[2] if t_count > 2 else ""

                recent_array = [random.randint(-4, 4) for _ in range(5)]
                recent_str = ", ".join(map(str, recent_array))
                psyche_mod = sum(recent_array)
                
                ratings = [random.randint(40, 99) for _ in range(14)]
                ws_ratings.append([p_id, 2026, t_id, age, pos, "Starter", t1, t2, t3, t_count, recent_str, psyche_mod] + ratings)
                
                # 3. Contracts
                c_id = f"C-{player_counter}"
                ws_contracts.append([c_id, p_id, t_id, 2025, 2028, random.randint(50000, 2000000), "Active"])
                
                # 4. STATS GENERATION
                if pos == "P":
                    ip = random.randint(50, 200)
                    er = int(ip * (random.uniform(2.5, 5.5) / 9))
                    k = int(ip * random.uniform(0.7, 1.2))
                    ws_pit_stats.append([p_id, 2026, "Regular Season", 30, random.randint(5, 20), random.randint(5, 15), 0, 0, 0, ip, int(ip*0.9), er+random.randint(0,5), er, random.randint(5, 25), random.randint(15, 60), random.randint(0, 5), k, ip*15, 1, 0, round((er*9)/ip, 2), 1.25, 3.85])
                else:
                    ab = random.randint(300, 600)
                    h = int(ab * random.uniform(0.220, 0.330))
                    hr = random.randint(5, 40)
                    ws_hit_stats.append([p_id, 2026, "Regular Season", 150, ab+50, ab, random.randint(40, 100), h, h-(hr+25), 20, 5, hr, random.randint(30, 100), random.randint(20, 80), random.randint(0, 10), random.randint(50, 150), random.randint(0, 30), random.randint(0, 10), round(h/ab, 3), 0.350, 0.450, 0.800])

                player_counter += 1
                
        data_added = True

    if data_added:
        wb.save(file_path)
        print("[+] Dummy data generated and saved to Excel.")
    else:
        print("[*] Excel file already populated. Skipping generation.")
        
    return True

def convert_excel_to_sqlite(excel_file, db_file):
    print("\n--- Step 2: Building SQLite Database ---")
    conn = sqlite3.connect(db_file)
    excel_data = pd.ExcelFile(excel_file)
    
    for sheet_name in excel_data.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        if len(df.columns) == 0 or "Unnamed" in str(df.columns[0]):
            print(f"[*] Skipping tab '{sheet_name}' (Blank or missing headers)")
            continue
            
        print(f"[*] Importing tab: {sheet_name}...")
        df.to_sql(sheet_name, conn, if_exists='replace', index=False)
        
    conn.close()
    print(f"\nSuccess! {db_file} is fully built and ready to query.")

if __name__ == "__main__":
    excel_filename = "DynastyBaseballSim.xlsx"
    db_filename = "diamondbucs_test.db"
    
    if populate_dummy_data(excel_filename):
        convert_excel_to_sqlite(excel_filename, db_filename)