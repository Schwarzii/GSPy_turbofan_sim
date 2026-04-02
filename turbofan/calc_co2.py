def parse_fuel_string(fuel_str):
    parts = {}
    total_shares = 0.0
    
    # Split by comma for multiple components
    components = fuel_str.split(',')
    
    for item in components:
        # Split by colon to get name and ratio/part
        name, value = item.split(':')
        name = name.strip().upper()
        share = float(value.strip())
        parts[name] = share
        total_shares += share
        
    # Convert shares to fractions (0.0 to 1.0)
    return {name: share / total_shares for name, share in parts.items()}

def co2_rate(composition):
    composition = parse_fuel_string(composition)
    # Emission Indices (kg CO2 produced per 1 kg of specific component)
    EMISSION_INDICES = {
        'H2': 0.0,
        'CH4': 2.744,
        'JET_A': 3.159,
        'N2': 0.0
    }
    
    total_co2_rate = 0.0
    
    for component, fraction in composition.items():
        ei = EMISSION_INDICES.get(component.upper(), 0.0)
        # CO2 = (Total Flow) * (Fraction of component) * (Emission Index)
        total_co2_rate += fraction * ei
        
    return total_co2_rate

if __name__ == "__main__":
    print(co2_rate(0.4, "CH4:9, N2:1"))