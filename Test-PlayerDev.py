import random
from model_player import Player
from Pfactory import PlayerFactory 

# ==========================================
# DIAMONDBUCS CAREER SIMULATION SCRIPT
# ==========================================

def display_player_state(player, year_label="Draft Day"):
    """Helper to format and print the player's current top-level stats."""
    
    # Grab the position using the exact key from PlayerFactory
    pos = player.attributes.get("Primary Pos", "DH")
    
    # Dynamically grab the main stats based on position
    if pos == "P":
        ratings = f"VEL: {player.velocity:02d} | CTRL: {player.control:02d} | MOVEMENT: {player.movement:02d}"
    else:
        ratings = f"CON: {player.contact:02d} | POW: {player.power:02d} | DIS: {player.discipline:02d} | SPD: {player.speed:02d} | DEF: {player.defense['overall']:02d}"
        
    print(f"[{year_label}] Name: {player.name:<18} | Pos: {pos:<3} | Age: {player.age:02d} | Ratings -> {ratings}")


def simulate_diamondbucs_career(player, max_years=20):
    """Runs a player through up to 'max_years' of development or until retirement."""
    
    print("=" * 95)
    print(f"SCOUTING REPORT: {player.name} (Traits: {', '.join(player.traits) if player.traits else 'None'})")
    print(f"Peak Age: {player.peak_age} | End Peak: {player.attributes['development'].get('last_peak_age', 32)} | Archetype: {player.attributes['development'].get('archetype', 'Unknown')}")
    print("=" * 95)
    
    # 1. Show Initial Draft State
    display_player_state(player, "Draft Day")
    print("-" * 95)
    
    # 2. Run the Career Loop
    for year in range(1, max_years + 1):
        if player.is_retired:
            print(f"\n*** [RETIRED] {player.name} hangs up the cleats after {year-1} pro seasons. ***")
            break
            
        peak_age = player.attributes['development']['peak_age']
        
        # Step A: Apply Growth to all sub-stats
        categories = ["batting", "pitching", "baserunning", "defense"]
        for cat in categories:
            for stat_name, current_val in player.attributes.get(cat, {}).items():
                if stat_name in ["stamina", "max_stamina"]: 
                    continue
                    
                new_val = player.attempt_stat_growth(current_val, player.age, peak_age)
                player.attributes[cat][stat_name] = new_val
                
        # Step B: Apply Aging and Degradation 
        player.process_offseason_aging()
        
        # Step C: Output the new state (unless they retired this exact offseason)
        if not player.is_retired:
            display_player_state(player, f"Year {year:02d}   ")
            
    # Fallback if they manage to play all 20 years without retiring
    if not player.is_retired:
        print(f"\n*** [SIM END] {player.name} reached the {max_years}-year simulation limit! ***")
        
    print("=" * 95)


# ==========================================
# EXECUTION
# ==========================================
if __name__ == "__main__":
    factory = PlayerFactory(current_season=2026)
    
    # --- TEST 1: Generate a Draft Hitter ---
    draft_hitter = factory.generate_inaugural_hitter(target_pos="CF", is_minor=True)
    
    # Force age to be strictly between 18-22
    starting_age_hitter = random.randint(18, 22)
    draft_hitter.age = starting_age_hitter
    draft_hitter.attributes['development']['age'] = starting_age_hitter
    
    simulate_diamondbucs_career(draft_hitter, max_years=20)
    
    print("\n\n")
    
    # --- TEST 2: Generate a Draft Pitcher ---
    draft_pitcher = factory.generate_inaugural_pitcher(role="SP", is_minor=True)
    
    # Force age to be strictly between 18-22
    starting_age_pitcher = random.randint(18, 22)
    draft_pitcher.age = starting_age_pitcher
    draft_pitcher.attributes['development']['age'] = starting_age_pitcher
    
    simulate_diamondbucs_career(draft_pitcher, max_years=20)