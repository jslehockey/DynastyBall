# ==========================================
# model_stadium.py
# ==========================================
# Handles all physical park dimensions, wall heights, 
# and environmental factors for the simulation.
# ==========================================

DEFAULT_DIMENSIONS = {
    "Left Field Line": 340, 
    "Dead Left Field": 360, 
    "Left Center Gap": 380,
    "Dead Center": 400, 
    "Right Center Gap": 380, 
    "Dead Right Field": 360, 
    "Right Field Line": 340
}

class Stadium:
    def __init__(self, name="Generic Park", custom_dimensions=None, custom_heights=None):
        self.name = name
        self.dimensions = DEFAULT_DIMENSIONS.copy()
        
        # --- PARK DIMENSIONS & PHYSICS ---
        # Default all wall heights to a standard 10 feet
        self.heights = {sector: 10 for sector in DEFAULT_DIMENSIONS.keys()}
        
        # Process Custom Dimensions
        if custom_dimensions and isinstance(custom_dimensions, dict):
            for sector, distance in custom_dimensions.items():
                if distance and int(distance) > 0:
                    self.dimensions[sector] = int(distance)
                    
        # Process Custom Heights
        if custom_heights and isinstance(custom_heights, dict):
            for sector, height in custom_heights.items():
                if height and int(height) > 0:
                    self.heights[sector] = int(height)