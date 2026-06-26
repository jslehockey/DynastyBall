import random
from datetime import datetime, timedelta

def generate_initial_decision_time(fa_start_time):
    # Distributes initial decision times randomly across the first 48 hours of Free Agency in 15-minute intervals.
    total_intervals = 48 * 4
    random_interval = random.randint(1, total_intervals)
    return fa_start_time + timedelta(minutes=(random_interval * 15))

def reroll_decision_time(current_sim_time, fa_start_time):
    # Calculates the next time a player checks their offers if they had none, or if they rejected all lowball offers.
    hours_into_fa = (current_sim_time - fa_start_time).total_seconds() / 3600
    
    if hours_into_fa < 48:
        # First 2 days: Check back in 15 mins to 4 hours
        wait_intervals = random.randint(1, 16) 
        return current_sim_time + timedelta(minutes=(wait_intervals * 15))
    else:
        # After 48 hours: Check back in 1 to 6 hours
        wait_hours = random.randint(1, 6)
        return current_sim_time + timedelta(hours=wait_hours)


class FreeAgencySimulation:
    def __init__(self, free_agents, fa_start_time):
        self.free_agents = free_agents  # List of Player objects currently in FA
        self.fa_start_time = fa_start_time
        self.current_time = fa_start_time
        self.active = False

    def start_free_agency(self):
        #Initializes the FA period and sets everyone's first clock.
        self.active = True
        for player in self.free_agents:
            player.next_decision_time = generate_initial_decision_time(self.fa_start_time)
            player.offers = [] 
        print(f"Free Agency has officially opened at {self.fa_start_time.strftime('%Y-%m-%d %H:%M')}!")

    def tick(self, minutes_to_advance=15):
        # Advances the simulation clock by a set number of minutes.
        # Evaluates any players whose decision time has arrived.
        if not self.active:
            return

        self.current_time += timedelta(minutes=minutes_to_advance)
        print(f"--- Simulating to: {self.current_time.strftime('%Y-%m-%d %H:%M')} ---")

        # Iterate backward through the list so we can safely remove players who sign
        for i in range(len(self.free_agents) - 1, -1, -1):
            player = self.free_agents[i]

            # Has their decision time arrived?
            if self.current_time >= player.next_decision_time:
                
                if len(player.offers) > 0:
                    # Player has offers, evaluate them
                    winning_bid = player.evaluate_offers()
                    
                    if winning_bid:
                        # Contract accepted
                        announcement = player.sign_contract(winning_bid)
                        print(f"BREAKING: {announcement}")
                        
                        # Remove the player from the free agent pool
                        self.free_agents.pop(i)
                    else:
                        # Player rejected all offers (they were below their minimum)
                        player.offers = []
                        player.next_decision_time = reroll_decision_time(self.current_time, self.fa_start_time)
                        print(f"{player.name} rejected all current offers. Market value unmet.")
                else:
                    # No offers on the table, wait longer
                    player.next_decision_time = reroll_decision_time(self.current_time, self.fa_start_time)