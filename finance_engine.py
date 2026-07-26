# finance_engine.py
import sqlite3

def validate_bid(bid, team_finances, player_age):
    """
    Checks if a submitted Bid object is financially legal.
    """
    # Establish League Minimums
    league_minimum = 100000 if player_age <= 23 else 500000
    
    # The "Negative Bank" Rule
    if team_finances < 0:
        if bid.yearly_value > league_minimum:
            return False, f"Team is in debt. Maximum offer is ${league_minimum:,.0f}."
        
        if bid.duration > 1:
            return False, "Teams in debt can only offer 1-year deals."

    return True, "Offer is valid."

def get_available_fa_money(team_id):
    """
    Calculates available Free Agency money by checking the latest season's ledger.
    Formula: Max Season ID Balance - Current Contracts.
    """
    conn = sqlite3.connect('diamondbucs.db')
    cursor = conn.cursor()
    
    # ORDER BY season DESC LIMIT 1 ensures we always grab the most recent season (Max Season ID)
    cursor.execute("""
        SELECT balance, cost_players 
        FROM Team_Financials 
        WHERE team_id = ? 
        ORDER BY season DESC 
        LIMIT 1
    """, (team_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return 0 # Fallback if the team has no financial records yet
        
    balance, cost_players = row
    available_money = balance - cost_players
    
    return available_money