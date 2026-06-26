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
    
    for team_name, roster in engine.rosters.items():
        ws = SHEET.worksheet(team_name)
        if not roster: 
            continue
            
        headers = list(roster[0].keys())
        grid = [headers]
        for player in roster:
            row = [player.get(h, "") for h in headers]
            grid.append(row)
            
        ws.update('A1', grid)
        print(f"  > Updated {team_name} fatigue levels.")
        time.sleep(1.5)  

    print("  > Updating Standings...")
    ws_standings = SHEET.worksheet("Standings")
    std_grid = [["Team ID", "Team", "W", "L", "RS", "RA"]]
    
    sorted_standings = sorted(engine.standings.items(), key=lambda x: x[1]["W"], reverse=True)
    for team, data in sorted_standings:
        team_id = engine.team_ids.get(team, "")
        std_grid.append([team_id, team, data["W"], data["L"], data["RS"], data["RA"]])
        
    ws_standings.update('A1', std_grid)
    time.sleep(1.5)

    print("  > Updating GameLog...")
    ws_gamelog = SHEET.worksheet("GameLog")
    gl_grid = [["Away Team", "Away Score", "Away W/L", "Home Team", "Home Score", "Home W/L"]] + engine.game_log
    ws_gamelog.update('A1', gl_grid)
    time.sleep(1.5)

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
        print(f"  > [WARNING] Could not update 'Boxscores' tab. Did you create it? Error: {e}")

    print("  > Updating Player Stats...")
    ws_stats = SHEET.worksheet("Stats")
    stat_headers = ["ID", "Name", "Team", "Pos", "G", "AB", "H", "HR", "RBI", "R", "AVG", "IP", "ER", "K", "BB", "ERA", "CG", "SHO"]
    stat_grid = [stat_headers]
    
    for pid, s in engine.player_stats.items():
        if s.get("G", 0) == 0 and s.get("AB", 0) == 0 and s.get("IP", 0) == 0:
            continue 

        if s["AB"] > 0:
            avg = s["H"] / s["AB"]
            avg_str = f"{avg:.3f}".lstrip('0')
            if avg == 1.0: avg_str = "1.000"
        else:
            avg_str = ".000"
        s["AVG"] = avg_str
        
        era = (s["ER"] * 9) / s["IP"] if s["IP"] > 0 else 0.0
        s["ERA"] = f"{era:.2f}"
        
        stat_grid.append([
            s["ID"], s["Name"], s["Team"], s["Pos"], s["G"], s["AB"], s["H"], s["HR"], 
            s["RBI"], s["R"], s["AVG"], round(s["IP"], 1), s["ER"], s["K"], s["BB"], s["ERA"],
            s.get("CG", 0), s.get("SHO", 0)
        ])
        
    ws_stats.clear()
    ws_stats.update('A1', stat_grid)
    
    print("✅ Master Export complete! All tabs are synced.")

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