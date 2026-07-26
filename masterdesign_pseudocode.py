"""
=========================================================
DYNASTYBALL MASTER LOGIC & RULES CONFIGURATION
STUDIO: Austin Rawl Labs LLC
=========================================================
"""

# ==========================================
# 1. ECONOMY & FINANCES (No Salary Cap)
# ==========================================
TICKET_PRICE = 30
STADIUM_TIERS = {
    "base": 25000, 
    "upgrades": [30000, 35000, 40000, 45000, 50000, 55000, 60000] # Costs scale exponentially
}

# Income distributed by Tier
MEDIA_DEAL = {
    "Tier_1": 40000000,
    "Tier_2": 20000000,
    "Tier_3": 10000000,
    "Tier_4": 5000000
}

# Performance Bonus (Paid end of regular season)
PERF_BONUS_TIER_1 = {
    "1st": 20000000,  # Plus media deal
    "2nd_to_4th": 15000000,
    "5th_to_10th": 10000000,
    "11th_to_15th": 5000000,
    "16th_to_20th": 10000000 # Corrected to 1M in text, setting to 1M
}
PERF_BONUS_TIER_1["16th_to_20th"] = 1000000

# FA Cup Gate Split
FA_CUP_GATE_SPLIT = 0.50 # 50% to home, 50% to away


# ==========================================
# 2. CONTRACTS & ROSTERS
# ==========================================
MINOR_LEAGUE_MINIMUM = 100000 # Flat rate for non-drafted minor leaguers (23 and under)
FA_MINIMUM_SALARY = 500000    # First-come, first-serve outside of offseason

# Draft Contracts (Guaranteed until Age 25)
DRAFT_SALARY_SCALE = {
    "Tier_1": {"Round_1": 1500000, "Round_2": 1200000, "Round_3": 900000, "Round_4": 600000},
    "Tier_2": {"Round_1": 1200000, "Round_2": 900000, "Round_3": 700000, "Round_4": 500000},
    "Tier_3": {"Round_1": 900000, "Round_2": 600000, "Round_3": 500000, "Round_4": 400000},
    "Tier_4_and_below": {"Round_1": 750000, "Round_2": 450000, "Round_3": 350000, "Round_4": 200000}
}

def execute_contract_buyout(player, contract):
    """Handles cutting a player and calculating dead money."""
    if contract.years_remaining == 1:
        team.dead_money += contract.salary_per_year # 100% stays on books
    else:
        team.dead_money += (contract.salary_per_year * 0.5) # 50% stays on books for remaining years
    player.release_to_fa_pool()


# ==========================================
# 3. TRADE VALIDATION
# ==========================================
def validate_trade_proposal(team_A_assets, team_B_assets, team_A_cash, team_B_cash):
    """Draft picks count as assets. Max 3 assets per side."""
    if len(team_A_assets) > 3 or len(team_B_assets) > 3:
        return "REJECTED: Exceeds 3 assets per side."
    
    total_assets_moving = len(team_A_assets) + len(team_B_assets)
    
    # Blockbuster Cash Limit
    if total_assets_moving > 3:
        if team_A_cash > 30000000 or team_B_cash > 30000000:
            return "REJECTED: Cash exceeds $30M blockbuster limit."
    # Standard Cash Limit
    else:
        if team_A_cash > 20000000 or team_B_cash > 20000000:
            return "REJECTED: Cash exceeds $20M standard limit."
            
    return "APPROVED"


# ==========================================
# 4. END OF SEASON ORDER OF OPERATIONS
# ==========================================
def run_end_of_season_logic():
    # STEP 1: The Purge
    dead_teams = delete_inactive_managers(days_inactive=30)
    tier_1_deficit = 80 - count_active_teams("Tier_1")
    
    # STEP 2: Auto Drops & Promotes (Assuming 4 Conf in T1, 8 Conf in T2)
    # T1 drops bottom 2 per conf (8 total). T2 promotes top 1 per conf (8 total).
    
    # STEP 3: Void Fill (Save the Condemned)
    if tier_1_deficit > 0:
        # Cancel relegation playoffs for the top X teams scheduled to play
        pardon_relegation_teams(count=tier_1_deficit)
        # Auto-promote the corresponding T2 teams without a playoff
        grant_playoff_byes_to_T2(count=tier_1_deficit)
        
    # STEP 4: Playoff Bracket (Survival Series)
    # 12 Teams total for remaining slots (8 from T2, 4 from T1)
    run_pro_rel_playoffs()


def run_pro_rel_playoffs():
    """Best of 3 series. Sweeps grant stamina recovery."""
    # Round 1: Tier 2 vs Tier 2 (8 teams -> 4 winners)
    # Round 2: Tier 2 Winners vs Tier 1 Condemned (4 teams vs 4 teams)
    
    for series in playoff_matchups:
        schedule = generate_floating_bye_schedule(games=4) 
        # Example output: [Game 1, Game 2, BYE, Game 3] or [BYE, Game 1, Game 2, Game 3]
        
        if series.score == "2-0":
            # SWEEP DETECTED
            cancel_game_3()
            award_extra_stamina_regeneration(series.winner)


# ==========================================
# 5. ASYNCHRONOUS DRAFT SYSTEM
# ==========================================
def generate_draft_order(tier="Tier_1"):
    """Creates the draft order after playoffs are complete."""
    # 1. Remove relegated teams (they draft in Tier 2 now)
    relegated_teams = get_relegated_teams()
    
    # 2. Build the Lottery Pool (9 Teams)
    # The 4 newly promoted teams + 5 worst surviving T1 teams
    lottery_teams = get_promoted_teams() + get_bottom_survivors(count=5)
    random.shuffle(lottery_teams) # Pure chaos, equal odds
    
    # 3. Build Reverse Standings (Remaining 71 Teams)
    remaining_teams = get_remaining_teams_sorted_by_worst_record()
    
    return lottery_teams + remaining_teams


def execute_async_draft(draft_order, draft_pool):
    """Runs automatically on draft day for all teams."""
    for team in draft_order:
        draft_board = get_team_priority_list(team.id) # 1 to 100 ranking
        dnd_list = get_team_do_not_draft_list(team.id)
        
        pick_made = False
        
        # 1. Check Priority List
        for prospect in draft_board:
            if prospect in draft_pool:
                draft_player(team, prospect)
                pick_made = True
                break
                
        # 2. Auto-Pick Fallback (If priority list is empty or exhausted)
        if not pick_made:
            available_players = [p for p in draft_pool if p not in dnd_list]
            
            if available_players:
                best_available = sort_by_overall(available_players)[0]
                draft_player(team, best_available)
            else:
                # 3. Last Resort (Only DND players remain)
                best_dnd = sort_by_overall(dnd_list)[0]
                draft_player(team, best_dnd)