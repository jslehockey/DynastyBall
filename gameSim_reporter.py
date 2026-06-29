# ==========================================
# gameSim_reporter.py
# ==========================================
# Handles all outgoing API pushes to Google Sheets, 
# including standings, box scores, and logs.
# ==========================================
import time
import gspread

def log_season_history(engine, SHEET, season_id):
    print(f"\n  > Archiving Season {season_id} transactional stats to 'StatLog'...")
    try:
        stat_log_ws = SHEET.worksheet("StatLog")
    except gspread.exceptions.WorksheetNotFound:
        print("  [ERROR] 'StatLog' tab not found in Google Sheets! Please create it.")
        return
    
    new_history_rows = []
    
    for team_name in engine.teams:
        current_tier = 1 
        
        for player in engine.rosters.get(team_name, []):
            pid = str(player["ID"])
            s = engine.player_stats.get(pid)
            
            if not s or (s.get("AB", 0) == 0 and s.get("IP", 0) == 0):
                continue 
            
            row = [
                season_id, pid, player["Name"], 
                engine.team_ids[team_name], team_name,
                current_tier, player["Pos"],
                s.get("G", 0), s.get("AB", 0), s.get("H", 0), s.get("HR", 0), s.get("RBI", 0), s.get("R", 0),
                s.get("IP", 0), s.get("ER", 0), s.get("K", 0), s.get("BB", 0),
                s.get("CG", 0), s.get("SHO", 0)
            ]
            new_history_rows.append(row)
            
    if new_history_rows:
        stat_log_ws.append_rows(new_history_rows)
        print(f"Successfully archived {len(new_history_rows)} player history entries.")

def export_all(engine, SHEET):
    print("Exporting updated rosters, stats, and standings back to Google Sheets...")
    
    # --- Roster Fatigue Sync ---
    for team_name, roster in engine.rosters.items():
        ws = SHEET.worksheet(team_name)
        if not roster: continue
        headers = list(roster[0].keys())
        grid = [headers]
        for player in roster:
            grid.append([player.get(h, "") for h in headers])
        ws.update('A1', grid)
        time.sleep(1.5)  

    # --- Standings Sync ---
    print("  > Updating Standings...")
    ws_standings = SHEET.worksheet("Standings")
    std_grid = [["Team ID", "Team", "W", "L", "RS", "RA"]]
    sorted_standings = sorted(engine.standings.items(), key=lambda x: x[1]["W"], reverse=True)
    for team, data in sorted_standings:
        std_grid.append([engine.team_ids.get(team, ""), team, data["W"], data["L"], data["RS"], data["RA"]])
    ws_standings.update('A1', std_grid)
    time.sleep(1.5)

    # --- GameLog Sync ---
    print("  > Updating GameLog...")
    ws_gamelog = SHEET.worksheet("GameLog")
    gl_grid = [["Away Team", "Away Score", "Away W/L", "Home Team", "Home Score", "Home W/L"]] + engine.game_log
    ws_gamelog.update('A1', gl_grid)
    time.sleep(1.5)

    # --- Boxscores Sync ---
    print("  > Updating Boxscores...")
    try:
        ws_box = SHEET.worksheet("BoxScores")
        if engine.boxscores:
            max_len = max(len(row) for row in engine.boxscores)
            uniform_boxscores = []
            for row in engine.boxscores:
                padded_row = row + [""] * (max_len - len(row))
                uniform_boxscores.append(padded_row)
            ws_box.append_rows(uniform_boxscores)
            engine.boxscores = []
        time.sleep(1.5)
    except Exception as e:
        print(f"  > [WARNING] Could not update 'Boxscores' tab. Error: {e}")

    # ==========================================
    # SABERMETRIC CALCULATORS & STAT EXPORTS
    # ==========================================
    print("  > Calculating Advanced Sabermetrics & Exporting Stats...")
    
    h_headers = ["ID", "Name", "Team", "Pos", "G", "PA", "AB", "R", "H", "1B", "2B", "3B", "HR", "RBI", "BB", "HBP", "K", "SB", "CS", "SF", "GIDP", "AVG", "OBP", "SLG", "OPS", "BABIP", "wOBA"]
    p_headers = ["ID", "Name", "Team", "Pos", "G", "W", "L", "SV", "HLD", "BS", "IP", "H", "R", "ER", "HR", "BB", "HBP", "K", "Pitches", "CG", "SHO", "ERA", "WHIP", "K/9", "BB/9", "HR/9", "FIP"]
    f_headers = ["ID", "Name", "Team", "Pos", "G", "PO", "A", "E", "TC", "FPCT"]
    
    h_grid = [h_headers]
    p_grid = [p_headers]
    f_grid = [f_headers]
    
    for pid, s in engine.player_stats.items():
        base_info = [s["ID"], s["Name"], s["Team"], s["Pos"], s["G"]]
        
        # --- HITTING MATH ---
        if s["PA"] > 0 or s["AB"] > 0:
            ab, hits = s["AB"], s["H"]
            bb, hbp, sf = s["BB"], s["HBP"], s["SF"]
            k_bat = s["K_bat"]
            
            # Basic Ratios
            avg = hits / ab if ab > 0 else 0.0
            obp = (hits + bb + hbp) / (ab + bb + hbp + sf) if (ab + bb + hbp + sf) > 0 else 0.0
            slg = (s["1B"] + (2 * s["2B"]) + (3 * s["3B"]) + (4 * s["HR"])) / ab if ab > 0 else 0.0
            ops = obp + slg
            
            # Advanced Sabermetrics
            babip_denom = ab - k_bat - s["HR"] + sf
            babip = (hits - s["HR"]) / babip_denom if babip_denom > 0 else 0.0
            
            woba_denom = ab + bb + hbp + sf
            # Using standard modern MLB wOBA weights
            woba = (0.69*bb + 0.72*hbp + 0.89*s["1B"] + 1.27*s["2B"] + 1.62*s["3B"] + 2.10*s["HR"]) / woba_denom if woba_denom > 0 else 0.0
            
            def fmt(val): 
                v = f"{val:.3f}".lstrip('0')
                return "1.000" if val == 1.0 else v

            h_row = base_info + [
                s["PA"], ab, s["R"], hits, s["1B"], s["2B"], s["3B"], s["HR"], s["RBI"], 
                bb, hbp, k_bat, s["SB"], s["CS"], sf, s["GIDP"], 
                fmt(avg), fmt(obp), fmt(slg), fmt(ops), fmt(babip), fmt(woba)
            ]
            h_grid.append(h_row)

        # --- PITCHING MATH ---
        outs = s.get("Outs_pit", 0)
        if outs > 0:
            ip_decimal = outs / 3.0
            ip_string = f"{outs // 3}.{outs % 3}" # This makes 14 outs = "4.2"
            
            bb_pit, hbp_pit, k_pit = s["BB_allowed"], s["HBP_allowed"], s["K_pit"]
            hr_pit, h_pit = s["HR_allowed"], s["H_allowed"]
            
            era = (s["ER"] * 9) / ip_decimal if ip_decimal > 0 else 0.0
            whip = (bb_pit + h_pit) / ip_decimal if ip_decimal > 0 else 0.0
            k9 = (k_pit * 9) / ip_decimal if ip_decimal > 0 else 0.0
            bb9 = (bb_pit * 9) / ip_decimal if ip_decimal > 0 else 0.0
            hr9 = (hr_pit * 9) / ip_decimal if ip_decimal > 0 else 0.0
            
            fip = ((13 * hr_pit) + (3 * (bb_pit + hbp_pit)) - (2 * k_pit)) / ip_decimal + 3.20 if ip_decimal > 0 else 0.0

            p_row = base_info + [
                s["W"], s["L"], s["SV"], s["HLD"], s["BS"], ip_string, h_pit, s["R_allowed"], s["ER"], 
                hr_pit, bb_pit, hbp_pit, k_pit, s["Pitches"], s["CG"], s["SHO"],
                f"{era:.2f}", f"{whip:.2f}", f"{k9:.1f}", f"{bb9:.1f}", f"{hr9:.1f}", f"{fip:.2f}"
            ]
            p_grid.append(p_row)

        # --- FIELDING MATH ---
        # FIXED: Changed from s["TC"] > 0 to s["G"] > 0 to capture everyone who plays!
        if s["G"] > 0 and s["Pos"] not in ["DH", "Bench", "Minors"]:
            fpct = (s["PO"] + s["A"]) / s["TC"] if s["TC"] > 0 else 0.0
            f_row = base_info + [s["PO"], s["A"], s["E"], s["TC"], f"{fpct:.3f}".lstrip('0') if fpct < 1.0 else "1.000"]
            f_grid.append(f_row)

    try:
        print("  > Syncing HStats...")
        ws_h = SHEET.worksheet("HStats")
        ws_h.clear()
        ws_h.update('A1', h_grid)
        time.sleep(1.5)
        
        print("  > Syncing PStats...")
        ws_p = SHEET.worksheet("PStats")
        ws_p.clear()
        ws_p.update('A1', p_grid)
        time.sleep(1.5)
        
        print("  > Syncing FStats...")
        ws_f = SHEET.worksheet("FStats")
        ws_f.clear()
        ws_f.update('A1', f_grid)
    except gspread.exceptions.WorksheetNotFound as e:
        print(f"  > [ERROR] Missing Stat Tab! Please create HStats, PStats, and FStats tabs in your Google Sheet. Error: {e}")
        
    print("Master Export complete! All tabs are synced.")

def export_playoff_bracket(engine, SHEET, a_scores, b_scores, f_scores):
    print("\nExporting Playoff Bracket to Google Sheets...")
    ws = SHEET.worksheet("Playoffs")
    ws.clear()
    
    grid = [
        ["🏆 SEMIFINALS (Best of 3)"],
        ["Team", "Game 1", "Game 2", "Game 3"]
    ]
    
    for series in [a_scores, b_scores]:
        for team_name, scores in series.items():
            row = [team_name] + scores
            while len(row) < 4: row.append("-")
            grid.append(row)
        grid.append([])
        
    grid.append(["🏆 CHAMPIONSHIP FINALS (Best of 3)"])
    grid.append(["Team", "Game 1", "Game 2", "Game 3"])
    for team_name, scores in f_scores.items():
        row = [team_name] + scores
        while len(row) < 4: row.append("-")
        grid.append(row)
        
    ws.append_rows(grid)