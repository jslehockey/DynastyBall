import random
import gspread
from model_player import Player
from model_team import Team
from model_league import LeagueEnvironment
from flow_fullGame import FullGame
from Pfactory import PlayerFactory

# --- CONFIGURATION ---
SPREADSHEET_ID = "1mC6-qF2_niu5756t5Q1yI-QJL_fZcvaF_KkOTrHX3Yc"
CLIENT = gspread.service_account(filename='credentials.json')
SHEET = CLIENT.open_by_key(SPREADSHEET_ID)

def build_full_roster(factory, team_name, is_expansion=True, is_minor=False, league_tier=1):
    """Generates a complete 26-man roster (13 Hitters, 13 Pitchers) and assigns positions/roles."""
    
    # --- 1. GENERATE HITTERS ---
    base_positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]
    extra_positions = random.sample(base_positions, 5)
    assigned_positions = base_positions + extra_positions
    random.shuffle(assigned_positions)
    
    hitters = []
    for pos in assigned_positions:
        player = factory.generate_inaugural_hitter(pos, is_expansion, is_minor, league_tier)
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
    majors_roster = build_full_roster(factory, team_name, is_expansion=False, is_minor=False, league_tier=1)
    minors_roster = build_full_roster(factory, team_name, is_expansion=False, is_minor=True, league_tier=2)
    
    for player in minors_roster:
        player.role_order = "Minors"
        
    return majors_roster + minors_roster

def flatten_player(player, team_name):
    """Extracts the generated player stats into a flat array for Google Sheets."""
    attr = player.attributes
    is_pitcher = player.assigned_pos == "P"
    stamina = attr['pitching'].get('stamina', 100) if is_pitcher else attr['batting'].get('stamina', 100)
    
    b = attr.get('batting', {})
    r = attr.get('baserunning', {})
    d = attr.get('defense', {}) 
    p = attr.get('pitching', {})
    dev = attr.get('development', {})
    
    # --- NEW: Extracting Traits ---
    traits = getattr(player, 'traits', [])
    t1 = traits[0] if len(traits) > 0 else "-"
    t2 = traits[1] if len(traits) > 1 else "-"
    t3 = traits[2] if len(traits) > 2 else "-"
    t_count = len(traits)
    
    return [
        player.player_id, 
        player.name, 
        team_name,
        player.assigned_pos, 
        player.role_order, 
        player.dh_status,
        dev.get('age', 18), 
        dev.get('archetype', 'Unknown'),
        
        # --- NEW: Trait Columns inserted here ---
        t1, t2, t3, t_count,
        
        # Batting
        player.contact, b.get('timing', 0), b.get('barreling', 0),
        player.power, b.get('strength', 0), b.get('bat_speed', 0), b.get('elevation', 0),
        player.discipline, b.get('eye', 0), b.get('restraint', 0),
        
        # Baserunning
        player.speed, r.get('sprint_speed', 0), r.get('instincts', 0),
        
        # Defense (Flattened into individual values)
        player.defense['overall'], 
        player.defense['range'], 
        player.defense['reaction'], 
        player.defense['glove'], 
        player.defense['arm_str'], 
        player.defense['arm_acc'],
        
        # Stamina
        stamina, 
        stamina, 
        
        # Pitching
        player.velocity, p.get('arm_speed', 0), p.get('deception', 0),
        player.control, p.get('accuracy', 0), p.get('command', 0),
        player.movement, p.get('spin_rate', 0), p.get('bite', 0),

        0, 0, 0, 0, 0, 0, ""  # HitStrk, MaxHit, OBPStrk, MaxOBP, Scoreless, MaxScoreless, RecentForm
    ]   

def main():
    factory = PlayerFactory(current_season=2026)
    
    # --- NEW: Added Trait Headers to match extraction ---
    headers = [
        "ID", "Name", "Team", "Pos", "Role/Order", "DH", "Age", "Arch", 
        "Trait1", "Trait2", "Trait3", "TraitCount",
        
        "Contact", "Con.Timing", "Con.Barrel", 
        "Power", "Pow.Str", "Pow.BatSpd", "Pow.Elev", 
        "Disc", "Disc.Eye", "Disc.Restr", 
        
        "Speed", "Spd.Sprint", "Spd.Inst", 
        
        "Defense", "def.Range", "def.reaction", "def.glove", "def.ArmStr", "def.ArmAcc", 
        
        "Max Stam", "Cur Stam", 
        
        "Velo", "Vel.ArmSpd", "Vel.Decept", 
        "Control", "Ctrl.Acc", "Ctrl.Cmd", 
        "Move", "Mov.Spin", "Mov.Bite",
        
        "Cur Hit Strk", "Max Hit Strk", "Cur OBP Strk", "Max OBP Strk", "Cur Scoreless Outs", "Max Scoreless Outs", "Recent Form"
    ]
    
    all_players_data = [headers]
    
    print("Beginning Franchise Generation...")
    
    for i in range(1, 9):
        team_name = f"Team{i}"
        
        franchise_roster = build_franchise(factory, team_name)
        print(f"Generated 52-man Franchise block for {team_name}...")
        
        team_rows = []
        for player in franchise_roster:
            row = flatten_player(player, team_name)
            team_rows.append(row)
            all_players_data.append(row)
            
        ws = SHEET.worksheet(team_name)
        ws.clear()
        ws.append_row(headers)
        ws.append_rows(team_rows)
        print(f"Successfully exported {team_name} to Sheets.")
        
    all_players_ws = SHEET.worksheet("All")
    all_players_ws.clear()
    all_players_ws.append_rows(all_players_data)
    print("\nFranchise Generation Complete! Master database updated.")

if __name__ == "__main__":
    main()