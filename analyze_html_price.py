
import re

def analyze_price_context():
    try:
        with open('debug_grid_inn.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Search for the problematic price
        target_price = "118,674"
        target_price_clean = "118674"
        
        indices = [m.start() for m in re.finditer(target_price, content)]
        if not indices:
            indices = [m.start() for m in re.finditer(target_price_clean, content)]
            
        print(f"Found {len(indices)} occurrences of {target_price}")
        
        for i, idx in enumerate(indices):
            start = max(0, idx - 200)
            end = min(len(content), idx + 200)
            context = content[start:end]
            print(f"\n--- Occurrence {i+1} ---")
            print(context)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_price_context()
