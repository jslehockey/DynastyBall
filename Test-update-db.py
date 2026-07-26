import sqlite3
import csv

def check_team_financials():
    # Connect to your database
    conn = sqlite3.connect('diamondbucs_test.db')
    cursor = conn.cursor()
    
    try:
        # Query everything from the table
        cursor.execute("SELECT * FROM Team_Financials")
        rows = cursor.fetchall()
        
        # Check if we actually have data
        if not rows:
            print("The 'Team_Financials' table exists, but it is currently EMPTY.")
            return
            
        # Get the column names automatically from the cursor
        headers = [description[0] for description in cursor.description]
        
        # Print a formatted table to the console
        print(f"\n--- Found {len(rows)} rows in Team_Financials ---\n")
        
        header_str = " | ".join(f"{str(h):<15}" for h in headers)
        print(header_str)
        print("-" * len(header_str))
        
        for row in rows:
            row_str = " | ".join(f"{str(item):<15}" for item in row)
            print(row_str)
            
        # Ask to export to CSV
        print("\n")
        export = input("Would you like to export this to a CSV file? (y/n): ")
        if export.lower() == 'y':
            with open('team_financials_export.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
            print("Successfully exported to 'team_financials_export.csv'!")
            
    except sqlite3.OperationalError as e:
        print(f"Database error (Did you create the table yet?): {e}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    check_team_financials()