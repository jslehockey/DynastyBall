import sqlite3
import random
from Pfactory import PlayerFactory
# Assuming model_player and others are imported within Pfactory if needed

DATABASE_NAME = "diamondbucs_test.db"

def build_full_roster(factory, is_expansion=True, is_minor=False, league_tier=1):
    """Generates a complete 26-man roster using PlayerFactory."""
    # 1. GENERATE HITTERS
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

    # 2. GENERATE PITCHERS
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
    
    pitcher_roles = ["SP1", "SP2", "SP3", "SP4", "SP5", "CL", "SU1", "SU2", "LR1", "LR2", "MR1", "MR2", "MR3"]
    
    for idx, player in enumerate(pitchers):
        player.assigned_pos = "P"
        player.dh_status = "No"
        player.role_order = pitcher_roles[idx]
        
    return hitters + pitchers

def map_player_to_db(player, player_id, team_id, league_level, season=1):
    """Maps the PlayerFactory object into SQLite database tuples."""
    attr = player.attributes
    is_pitcher = player.assigned_pos == "P"
    
    b = attr.get('batting', {})
    r = attr.get('baserunning', {})
    d = attr.get('defense', {}) 
    p = attr.get('pitching', {})
    dev = attr.get('development', {})
    
    # --- STAMINA FIX ---
    # Grab stamina from the pitching dictionary if they pitch, otherwise batting
    stamina = p.get('stamina') if is_pitcher else b.get('stamina')
    # Fallback to 50 if something goes terribly wrong
    if stamina is None: 
        stamina = 50
    
    # Name Parsing
    name_parts = player.name.split(' ', 1)
    fname = name_parts[0]
    lname = name_parts[1] if len(name_parts) > 1 else ""

    # Role Parsing for DB
    if is_pitcher:
        role = "Pitcher"
        assigned_role = player.role_order 
        batting_order = 99
        assigned_pos = None
    else:
        role = "Bench" if player.role_order == "Bench" else "Lineup"
        assigned_role = None
        batting_order = int(player.role_order) if player.role_order.isdigit() else 99
        assigned_pos = player.assigned_pos if role == "Lineup" else "BENCH"
        
        if player.dh_status == "Yes":
            assigned_pos = "DH"

    # Trait Parsing
    traits = getattr(player, 'traits', [])
    t1 = traits[0] if len(traits) > 0 else None
    t2 = traits[1] if len(traits) > 1 else None
    t3 = traits[2] if len(traits) > 2 else None

    base_record = (
        player_id, fname, lname, dev.get('peak_age', 27), dev.get('last_peak_age', 32), dev.get('archetype', 'Balanced')
    )

    ratings_record = (
        player_id, player_id, team_id, season, league_level, dev.get('age', 22), 
        player.assigned_pos, role, t1, t2, t3, len(traits), 0, 5, 
        assigned_pos, assigned_role, batting_order,
        
        b.get('timing', 0), b.get('barreling', 0),
        b.get('strength', 0), b.get('bat_speed', 0), b.get('elevation', 0),
        b.get('eye', 0), b.get('restraint', 0),
        
        r.get('sprint_speed', 0), r.get('instincts', 0),
        
        d.get('def.range', 0), d.get('def.reaction', 0), 
        d.get('def.glove', 0), d.get('def.ArmStr', 0), 
        d.get('def.ArmAcc', 0),
        
        # --- STAMINA FIXED ---
        stamina, stamina,
        
        p.get('arm_speed', 0), p.get('arm_speed', 0), p.get('deception', 0),
        p.get('accuracy', 0), p.get('accuracy', 0), p.get('command', 0),
        p.get('spin_rate', 0), p.get('spin_rate', 0), p.get('bite', 0)
    )

    return base_record, ratings_record

def main():
    factory = PlayerFactory(current_season=1)
    
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # 1. Fetch Active Teams from Database
        cursor.execute("SELECT team_id, nickname FROM teams WHERE status = 'active'")
        teams = cursor.fetchall()
        
        if not teams:
            print("No active teams found in the database. Did you run the team seed script?")
            return

        all_base_records = []
        all_ratings_records = []
        current_player_id = 1

        print("Beginning Franchise Generation...")

        # 2. Generate Players for Each Team
        for team_id, nickname in teams:
            print(f"Generating 52-man Franchise block for the {nickname}...")
            
            # Generate Majors
            majors_roster = build_full_roster(factory, is_expansion=False, is_minor=False, league_tier=1)
            for p in majors_roster:
                base, ratings = map_player_to_db(p, current_player_id, team_id, "MLB")
                all_base_records.append(base)
                all_ratings_records.append(ratings)
                current_player_id += 1
                
            # Generate Minors
            minors_roster = build_full_roster(factory, is_expansion=False, is_minor=True, league_tier=2)
            for p in minors_roster:
                base, ratings = map_player_to_db(p, current_player_id, team_id, "MiLB")
                all_base_records.append(base)
                all_ratings_records.append(ratings)
                current_player_id += 1

        # 3. Clear existing players to prevent duplicates on rerun
        cursor.execute("DELETE FROM player_ratings")
        cursor.execute("DELETE FROM players_base")

        # 4. Insert into Database
        cursor.executemany("""
            INSERT INTO players_base (
                player_id, first_name, last_name, peak_age, degrade_age, archetype
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, all_base_records)

        cursor.executemany("""
            INSERT INTO player_ratings (
                rating_id, player_id, team_id, season, league_level, age, position, role,
                trait_1, trait_2, trait_3, trait_count, recent_form, psyche_mod,
                assigned_pos, assigned_role, batting_order,
                con_timing, con_barrel, pow_str, pow_batspd, pow_elev, disc_eye, disc_restr,
                spd_sprint, spd_inst, def_range, def_react, def_glove, def_armstr, def_armacc,
                stam_max, stam_cur,
                pit_velo, pit_vel_armspd, pit_vel_decept, pit_ctrl, pit_ctrl_acc, pit_ctrl_cmd,
                pit_mov, pit_mov_spin, pit_mov_bite
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, all_ratings_records)

        conn.commit()
        print(f"\nFranchise Generation Complete! {len(all_base_records)} total players safely stored in the database.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()