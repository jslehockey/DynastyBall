import sqlite3
import random

def randomize_contract_lengths():
    conn = sqlite3.connect('diamondbucs_test.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get all contracts
        cursor.execute("SELECT contract_id, year_start FROM Contracts")
        contracts = cursor.fetchall()
        
        updates = []
        for row in contracts:
            # Generate a random contract length from 1 to 4 years
            contract_length = random.randint(1, 4)
            
            # Calculate year_end (e.g., Start 1 + Length 1 - 1 = End 1)
            new_year_end = row['year_start'] + contract_length - 1
            
            updates.append((new_year_end, row['contract_id']))
            
        # Push the updates to the database
        cursor.executemany("""
            UPDATE Contracts 
            SET year_end = ? 
            WHERE contract_id = ?
        """, updates)
        
        conn.commit()
        print(f"Successfully randomized lengths for {len(updates)} contracts!")
        
        # Verify with a quick sample
        cursor.execute("SELECT player_id, year_start, year_end, cost_per_season FROM Contracts LIMIT 5")
        print("\n--- SAMPLE CONTRACTS ---")
        for r in cursor.fetchall():
            length = (r['year_end'] - r['year_start']) + 1
            print(f"Player {r['player_id']:<3} | Length: {length} years (End: {r['year_end']}) | ${r['cost_per_season']}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    randomize_contract_lengths()