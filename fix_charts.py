"""Update chart BG from dark to light theme."""
with open("app/main.py", "r", encoding="utf-8") as f:
    c = f.read()

# Replace dark chart BG with light lavender
old = 'BG = "#100320"'
new = 'BG = "#f3eeff"'
count = c.count(old)
c = c.replace(old, new)

# Also update donut ring BG from dark to light
c = c.replace('RING_BG      = "#1e0a3c"', 'RING_BG      = "#e9d5ff"')
# And donut background
c = c.replace('facecolor="#1e0a3c"', 'facecolor="#e9d5ff"')
c = c.replace('facecolor="#2d2d44"', 'facecolor="#ede9fe"')
# Update legend box on trend chart
c = c.replace('facecolor="#1e0a3c", edgecolor="#5b00e0"', 'facecolor="#ede9fe", edgecolor="#8b5cf6"')
# Grid lines to lighter colour
c = c.replace('color="#2d1a4e", linewidth=0.8, linestyle="--"', 'color="#ddd6fe", linewidth=0.8, linestyle="--"')
c = c.replace('color="#2d1a4e", linewidth=0.7, linestyle="--"', 'color="#ddd6fe", linewidth=0.7, linestyle="--"')

with open("app/main.py", "w", encoding="utf-8") as f:
    f.write(c)

print(f"Done! Replaced {count} BG values.")
