# database/generate_dataset.py
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# Create datasets directory if not exists
os.makedirs('datasets', exist_ok=True)

# Seed for reproducibility
np.random.seed(42)

# Generate 10,000 records
num_records = 10000

buses = ['NS-B01', 'NS-B02', 'NS-B03', 'NS-B04']
routes = ['Route 1', 'Route 2', 'Route 3', 'Route 4']
stops = ['Central Station', 'Oak Avenue', 'Maple Road', 'Aisle Street', 'City Center', 'Tech Park', 'South Gate', 'East Airport']
weathers = ['Sunny', 'Rainy', 'Cloudy', 'Windy']
traffic_levels = ['Low', 'Medium', 'High']

# Generate random components
bus_col = np.random.choice(buses, size=num_records)
route_col = np.random.choice(routes, size=num_records)
weather_col = np.random.choice(weathers, size=num_records)
traffic_col = np.random.choice(traffic_levels, size=num_records)

# Generate source and destination stops
source_col = []
dest_col = []
curr_col = []

for r in route_col:
    # Pick source and destination stops
    s_idx = np.random.randint(0, len(stops) - 2)
    d_idx = np.random.randint(s_idx + 1, len(stops))
    c_idx = np.random.randint(s_idx, d_idx)
    source_col.append(stops[s_idx])
    dest_col.append(stops[d_idx])
    curr_col.append(stops[c_idx])

travel_time_col = np.random.randint(10, 90, size=num_records)
passenger_count_col = np.random.randint(1, 6, size=num_records)

# Dates over the last 30 days
start_date = datetime(2026, 6, 25)
dates = [start_date + timedelta(days=int(np.random.randint(0, 30)),
                                hours=int(np.random.randint(6, 22)),
                                minutes=int(np.random.randint(0, 60))) 
         for _ in range(num_records)]

date_strings = [d.strftime('%Y-%m-%d') for d in dates]
time_strings = [d.strftime('%H:%M') for d in dates]

# Generate occupancy based on time of day (rush hour peaks), weather and traffic
occupancies = []
for d, traffic, weather, count in zip(dates, traffic_col, weather_col, passenger_count_col):
    hour = d.hour
    base_occupancy = 10
    
    # Peak hours: 8-10 AM, 5-7 PM
    if 8 <= hour <= 10 or 17 <= hour <= 19:
        base_occupancy += np.random.randint(30, 50)
    else:
        base_occupancy += np.random.randint(5, 20)
        
    if traffic == 'High':
        base_occupancy += np.random.randint(5, 10)
    if weather == 'Rainy':
        base_occupancy += np.random.randint(3, 8)
        
    # Cap at bus total capacity (80)
    occupancy = min(80, base_occupancy + count)
    occupancies.append(occupancy)

df = pd.DataFrame({
    'Bus Number': bus_col,
    'Route': route_col,
    'Source Stop': source_col,
    'Destination Stop': dest_col,
    'Current Stop': curr_col,
    'Weather': weather_col,
    'Traffic Level': traffic_col,
    'Travel Time': travel_time_col,
    'Date': date_strings,
    'Time': time_strings,
    'Passenger Count': passenger_count_col,
    'Current Occupancy': occupancies
})

output_path = os.path.join('datasets', 'NextStop_10000_Records_Dataset.xlsx')
df.to_excel(output_path, index=False)
print(f"[+] Dataset successfully generated at {output_path} with {len(df)} records.")
