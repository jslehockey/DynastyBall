import random
import gspread
from models import Player, Team, LeagueEnvironment
from game_flow import FullGame
from Pfactory import PlayerFactory

# --- CONFIGURATION ---
SPREADSHEET_ID = "1mC6-qF2_niu5756t5Q1yI-QJL_fZcvaF_KkOTrHX3Yc"
CLIENT = gspread.service_account(filename='credentials.json')
SHEET = CLIENT.open_by_key(SPREADSHEET_ID)

def build_full_roster(factory, team_name, is_expansion=True, is_minor=False, league_tier=1):
    """Generates a complete 26-man roster (13 Hitters, 13 Pitchers) and assigns positions/roles."""
    
    # --- 1. GENERATE HITTERS ---
    # Determine the 13 positions first
    base_positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]
    extra_positions = random.sample(base_positions, 5) # 5 duplicates for the bench/DH
    assigned_positions = base_positions + extra_positions
    random.shuffle(assigned_positions)
    
    hitters = []
    for pos in assigned_positions:
        # Pass the exact position into the factory to trigger the correct archetype!
        player = factory.generate_inaugural_hitter(pos, is_expansion, is_minor, league_tier)
        
        # The new factory already sets player.assigned_pos inside the generation
        player.dh_status = "No"
        player.role_order = "Bench"
        hitters.append(player)

    # Separate Starters vs Bench
    starters = []
    seen_positions = set()
    bench = []
    
    for player in hitters:
        if player.assigned_pos not in seen_positions:
            starters.append(player)
            seen_positions.add(player.assigned_pos)
        else:
            bench.append(player)
            
    # Assign DH
    dh_player = bench.pop(0)
    dh_player.dh_status = "Yes"
    starters.append(dh_player)
    
    # Assign Batting Order (1-9)
    batting_orders = list(range(1, 10))
    random.shuffle(batting_orders)
    for idx, player in enumerate(starters):
        player.role_order = str(batting_orders[idx])

    # --- 2. GENERATE PITCHERS ---
    # Your pitcher generation was already perfect because you were passing the role string!
    pitchers = [
        factory.generate_inaugural_pitcher("SP", is_expansion, is_minor, league_tier) for _ in range(5)
    ] + [
        factory.generate_inaugural_pitcher("CL", is_expansion, is_minor, league_tier),
        factory.generate_inaugural_pitcher("SU", is_expansion, is_minor, league_tier),
        factory.generate_inaugural_pitcher("SU", is_expansion, is_minor, league_tier),
        factory.generate_inaugural_pitcher("LR", is_expansion, is_minor, league_tier),
        factory.generate_inaugural_pitcher("LR", is_expansion, is_minor, league_tier)
    ] + [
        factory.generate_inaugural_pitcher("MR", is_expansion, is_minor, league_tier) for _ in range(3)
    ]
    
    pitcher_roles = ["SP1", "SP2", "SP3", "SP4", "SP5", "CL", "SU", "SU", "LR", "LR", "MR", "MR", "MR"]
    
    for idx, player in enumerate(pitchers):
        player.assigned_pos = "P"
        player.dh_status = "No"
        player.role_order = pitcher_roles[idx]
        
    return hitters + pitchers

def build_franchise(factory, team_name):
    """Builds a 52-man franchise block: 26 Majors, 26 Minors."""
    
    # 1. Generate the Major League Squad
    majors_roster = build_full_roster(factory, team_name, is_expansion=False, is_minor=False, league_tier=1)
    
    # 2. Generate the Minor League Squad
    minors_roster = build_full_roster(factory, team_name, is_expansion=False, is_minor=True, league_tier=2)
    
    # 3. Override the Role/Order for all minor leaguers to say "Minors"
    for player in minors_roster:
        player.role_order = "Minors"
        
    # Merge them together (Majors first, then Minors)
    return majors_roster + minors_roster

def flatten_player(player, team_name):
    """Extracts the generated player attributes into a flat array for Google Sheets."""
    attr = player.attributes
    is_pitcher = player.assigned_pos == "P"
    stamina = attr['pitching'].get('stamina', 100) if is_pitcher else attr['batting'].get('stamina', 100)
    
    return [
        player.player_id, 
        player.name, 
        team_name,
        player.assigned_pos, 
        player.role_order, 
        player.dh_status,
        attr['development']['age'], 
        attr['development']['archetype'],
        attr['batting'].get('contact', 0), 
        attr['batting'].get('power', 0), 
        attr['batting'].get('discipline', 0),
        attr['fielding'].get('range', 0), 
        attr['fielding'].get('glove', 0), 
        attr['fielding'].get('arm', 0),
        stamina, 
        stamina, 
        attr['pitching'].get('velocity', 0), 
        attr['pitching'].get('control', 0), 
        attr['pitching'].get('movement', 0)
    ]

def main():
    factory = PlayerFactory(current_season=2026)
    
    headers = ["ID", "Name", "Team", "Pos", "Role/Order", "DH", "Age", "Arch", 
               "Contact", "Power", "Disc", "Range", "Glove", "Arm", 
               "Max Stam", "Cur Stam", "Velo", "Control", "Move"]
    
    all_players_data = [headers]
    
    print("Beginning Franchise Generation...")
    
    # Only loop 1 to 8 now, because every team is a full Franchise
    for i in range(1, 9):
        team_name = f"Team{i}"
        
        # Build the 52-man mega-roster
        franchise_roster = build_franchise(factory, team_name)
        print(f"Generated 52-man Franchise block for {team_name}...")
        
        team_rows = []
        for player in franchise_roster:
            row = flatten_player(player, team_name)
            team_rows.append(row)
            all_players_data.append(row)
            
        # Update Individual Team Tab
        ws = SHEET.worksheet(team_name)
        ws.clear()
        ws.append_row(headers)
        ws.append_rows(team_rows)
        print(f"Successfully exported {team_name} to Sheets.")
        
    # Update Master "All" Tab
    all_players_ws = SHEET.worksheet("All")
    all_players_ws.clear()
    all_players_ws.append_rows(all_players_data)
    print("\nFranchise Generation Complete! Master database updated.")

if __name__ == "__main__":
    main()