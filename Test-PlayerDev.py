import random
from model_player import Player
from Pfactory import PlayerFactory 

# ==========================================
# DIAMONDBUCS DRAFT CLASS PARITY TESTER
# ==========================================

def display_player_state(player, year_label="Draft Day"):
    """Helper to format and print the player's current top-level stats."""
    pos = player.attributes.get("Primary Pos", "DH")
    
    if pos == "P":
        ratings = f"VEL: {player.velocity:02d} | CTRL: {player.control:02d} | MOVEMENT: {player.movement:02d}"
    else:
        ratings = f"CON: {player.contact:02d} | POW: {player.power:02d} | DIS: {player.discipline:02d} | SPD: {player.speed:02d} | DEF: {player.defense['overall']:02d}"
        
    return f"[{year_label}] Name: {player.name:<18} | Pos: {pos:<3} | Age: {player.age:02d} | Ratings -> {ratings}"


def simulate_diamondbucs_career(player, max_years=10, verbose=False):
    """Runs a player through development. Runs silently if verbose=False."""
    
    if verbose:
        print("=" * 95)
        print(f"SCOUTING REPORT: {player.name} (Traits: {', '.join(player.traits) if player.traits else 'None'})")
        print(f"Peak Age: {player.peak_age} | End Peak: {player.attributes['development'].get('last_peak_age', 32)}")
        print(display_player_state(player, "Draft Day"))
        print("-" * 95)
    
    player.draft_state_log = display_player_state(player, "Draft Day")
    
    for year in range(1, max_years + 1):
        if player.is_retired:
            if verbose:
                print(f"\n*** [RETIRED] {player.name} hangs up the cleats after {year-1} pro seasons. ***")
            break
            
        peak_age = player.attributes['development']['peak_age']
        
        # Apply Growth
        categories = ["batting", "pitching", "baserunning", "defense"]
        for cat in categories:
            for stat_name, current_val in player.attributes.get(cat, {}).items():
                if stat_name in ["stamina", "max_stamina"]: 
                    continue
                    
                new_val = player.attempt_stat_growth(current_val, player.age, peak_age)
                player.attributes[cat][stat_name] = new_val
                
        # Apply Aging
        player.process_offseason_aging()
        
        if verbose and not player.is_retired:
            print(display_player_state(player, f"Year {year:02d}   "))
            
    # Store final state
    status = "RETIRED" if player.is_retired else f"YEAR {max_years}"
    player.final_state_log = display_player_state(player, status)
    
    return player

def evaluate_tier(player):
    """Categorizes a player into 5-point bins based on their primary attributes."""
    pos = player.attributes.get("Primary Pos", "DH")
    
    if pos == "P":
        # Assumes velocity, control, movement are available as properties on the Player object
        primary_avg = (player.velocity + player.control + player.movement) / 3
    else:
        primary_avg = (player.contact + player.power + player.discipline) / 3
        
    if primary_avg >= 85: return "85+"
    if primary_avg >= 80: return "80-84"
    if primary_avg >= 75: return "75-79"
    if primary_avg >= 70: return "70-74"
    if primary_avg >= 65: return "65-69"
    if primary_avg >= 60: return "60-64"
    if primary_avg >= 55: return "55-59"
    if primary_avg >= 50: return "50-54"
    return "Sub 50"


# ==========================================
# EXECUTION
# ==========================================
if __name__ == "__main__":
    factory = PlayerFactory(current_season=2026)
    
    CLASS_SIZE = 500
    YEARS_TO_SIM = 10
    
    # Initialize tracking dictionaries
    bin_keys = ["85+", "80-84", "75-79", "70-74", "65-69", "60-64", "55-59", "50-54", "Sub 50"]
    draft_tiers = {key: [] for key in bin_keys}
    final_tiers = {key: [] for key in bin_keys}
    
    print(f"Generating and simulating a {CLASS_SIZE}-player draft class over {YEARS_TO_SIM} years...\n")
    
    # 1. Generate, Evaluate Initial, Sim, Evaluate Final
    for _ in range(CLASS_SIZE):
        if random.random() < 0.60:
            target_pos = random.choice(["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"])
            player = factory.generate_inaugural_hitter(target_pos=target_pos, is_minor=True)
        else:
            role = random.choice(["SP", "SP", "RP", "CL"])
            player = factory.generate_inaugural_pitcher(role=role, is_minor=True)
            
        # Force age to 18-22
        start_age = random.randint(18, 22)
        player.age = start_age
        player.attributes['development']['age'] = start_age
        
        # Evaluate BEFORE training
        initial_tier = evaluate_tier(player)
        draft_tiers[initial_tier].append(player)
        
        # Run silent simulation
        finished_player = simulate_diamondbucs_career(player, max_years=YEARS_TO_SIM, verbose=False)
        
        # Evaluate AFTER training
        final_tier = evaluate_tier(finished_player)
        final_tiers[final_tier].append(finished_player)

    # 2. Print the Side-by-Side Summary
    print("=" * 55)
    print(f" 10-YEAR DRAFT CLASS MACRO SUMMARY ({CLASS_SIZE} PLAYERS)")
    print("=" * 55)
    print(f"{'TIER':<10} | {'DRAFT DAY COUNT':<18} | {'YEAR 10 COUNT':<15}")
    print("-" * 55)
    
    for key in bin_keys:
        initial_count = len(draft_tiers[key])
        final_count = len(final_tiers[key])
        print(f"{key:<10} | {initial_count:<18} | {final_count:<15}")

    print("=" * 55)
    
    # Optional: Print the logs for the elite players to see their exact growth
    print("\n--- ELITE PLAYER LOGS (Finished 80+) ---")
    elite_players = final_tiers["85+"] + final_tiers["80-84"]
    if not elite_players:
        print("No players finished above an 80 average.")
    else:
        for p in elite_players:
            print(f"  {p.draft_state_log}")
            print(f"  {p.final_state_log}\n")