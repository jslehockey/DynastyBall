import sqlite3
import random

# Import YOUR exact PlayerFactory
from Pfactory import PlayerFactory 

DATABASE_NAME = "diamondbucs_test.db"

def seed_pfactory_free_agents():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # 1. Safely find the next available Player ID
        cursor.execute("SELECT MAX(player_id) FROM players_base")
        max_id_result = cursor.fetchone()[0]
        next_player_id = (max_id_result or 100000000) + 1

        # 2. Instantiate your factory for Season 1
        factory = PlayerFactory(current_season=1)

        base_inserts = []
        rating_inserts = []

        hit_pool = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]
        pit_pool = ["SP", "MR", "LR", "SU", "CL"]

        # 3. Generate 100 Players (25 MLB Hitters, 25 MLB Pitchers, 25 MiLB Hitters, 25 MiLB Pitchers)
        generated_players = []

        print("Spinning up PFactory to generate 100 Free Agents...")

        # MLB Hitters & Pitchers
        for _ in range(25):
            generated_players.append((factory.generate_inaugural_hitter(random.choice(hit_pool), is_minor=False), "FA"))
            generated_players.append((factory.generate_inaugural_pitcher(random.choice(pit_pool), is_minor=False), "FA"))
        
        # MiLB Hitters & Pitchers
        for _ in range(25):
            generated_players.append((factory.generate_inaugural_hitter(random.choice(hit_pool), is_minor=True), "FA_MiLB"))
            generated_players.append((factory.generate_inaugural_pitcher(random.choice(pit_pool), is_minor=True), "FA_MiLB"))

        # 4. Map the PFactory objects to your SQL Schema
        for i, (p, league_level) in enumerate(generated_players):
            p_id = next_player_id + i
            attrs = p.attributes

            # Extract Name
            first_name = p.name.split()[0]
            last_name = " ".join(p.name.split()[1:])

            # --- PLAYERS_BASE TABLE ---
            base_inserts.append((
                p_id, first_name, last_name, 
                attrs["development"]["peak_age"], 
                attrs["development"]["last_peak_age"], 
                attrs["development"]["archetype"]
            ))

            # Traits
            t1 = p.traits[0] if len(p.traits) > 0 else None
            t2 = p.traits[1] if len(p.traits) > 1 else None
            t3 = p.traits[2] if len(p.traits) > 2 else None

            is_pitcher = attrs["Primary Pos"] == "P"
            stam = attrs["pitching"]["stamina"] if is_pitcher else attrs["batting"]["stamina"]
            role = attrs.get("role", "Lineup")

            # Averages for composite pitching stats since your schema asks for them
            pit_ctrl = (attrs["pitching"]["accuracy"] + attrs["pitching"]["command"]) // 2
            pit_mov = (attrs["pitching"]["spin_rate"] + attrs["pitching"]["bite"]) // 2

            # --- PLAYER_RATINGS TABLE ---
            rating_inserts.append((
                None, # rating_id (SQLite will auto-increment)
                p_id, 
                None, # team_id is NULL for Free Agents
                1, # season
                league_level, 
                attrs["development"]["age"], 
                attrs["Primary Pos"], 
                role,
                t1, t2, t3, len(p.traits),
                50, # recent_form
                50, # psyche_mod
                None, None, None, # assigned_pos, assigned_role, batting_order

                # Batting
                attrs["batting"]["timing"], attrs["batting"]["barreling"],
                attrs["batting"]["strength"], attrs["batting"]["bat_speed"], attrs["batting"]["elevation"],
                attrs["batting"]["eye"], attrs["batting"]["restraint"],
                
                # Baserunning & Defense
                attrs["baserunning"]["sprint_speed"], attrs["baserunning"]["instincts"],
                attrs["defense"]["def.range"], attrs["defense"]["def.reaction"], attrs["defense"]["def.glove"],
                attrs["defense"]["def.ArmStr"], attrs["defense"]["def.ArmAcc"],
                
                # Stamina
                stam, stam, 

                # Pitching
                attrs["pitching"]["arm_speed"], attrs["pitching"]["arm_speed"], attrs["pitching"]["deception"],
                pit_ctrl, attrs["pitching"]["accuracy"], attrs["pitching"]["command"],
                pit_mov, attrs["pitching"]["spin_rate"], attrs["pitching"]["bite"]
            ))

        # 5. Execute Inserts
        cursor.executemany("""
            INSERT INTO players_base (player_id, first_name, last_name, peak_age, degrade_age, archetype)
            VALUES (?, ?, ?, ?, ?, ?)
        """, base_inserts)

        cursor.executemany("""
            INSERT INTO player_ratings (
                rating_id, player_id, team_id, season, league_level, age, position, role,
                trait_1, trait_2, trait_3, trait_count, recent_form, psyche_mod, assigned_pos, assigned_role, batting_order,
                con_timing, con_barrel, pow_str, pow_batspd, pow_elev, disc_eye, disc_restr,
                spd_sprint, spd_inst, def_range, def_react, def_glove, def_armstr, def_armacc,
                stam_max, stam_cur,
                pit_velo, pit_vel_armspd, pit_vel_decept, pit_ctrl, pit_ctrl_acc, pit_ctrl_cmd, pit_mov, pit_mov_spin, pit_mov_bite
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, 
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, 
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, rating_inserts)

        conn.commit()
        print(f"Success! {len(base_inserts)} perfectly balanced PFactory Free Agents added to the database.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except ImportError as e:
        print(f"Import error: Make sure this script is in the same folder as PFactory.py and model_player.py. ({e})")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    seed_pfactory_free_agents()