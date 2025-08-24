from datetime import datetime

def calculate_fine(days_late, rate_per_day=5):
    return days_late * rate_per_day