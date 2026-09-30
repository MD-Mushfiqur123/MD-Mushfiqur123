import json
import os
import math
import urllib.request
from datetime import datetime

def fetch_contributions(username="MD-Mushfiqur123"):
    # Method 1: Public API
    try:
        url = f"https://github-contributions-api.jogruber.de/v4/{username}?y=last"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            contribs = data.get('contributions', [])
            if contribs:
                return contribs
    except Exception as e:
        print(f"API notice: {e}")

    # Method 2: Direct GitHub contribution calendar scrape
    try:
        import re
        url = f"https://github.com/users/{username}/contributions"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')
            days = []
            date_matches = re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*id="([^"]+)"', html)
            for d, elem_id in date_matches:
                tip_match = re.search(r'for="' + re.escape(elem_id) + r'"[^>]*>(.*?)</tool-tip>', html, re.DOTALL)
                count = 0
                if tip_match:
                    tip_text = tip_match.group(1).strip()
                    num_match = re.search(r'(\d+)\s+contribution', tip_text)
                    if num_match:
                        count = int(num_match.group(1))
                days.append({"date": d, "count": count})
            if days:
                return days
    except Exception as e:
        print(f"Scrape notice: {e}")

    return []

def generate_svg():
    all_data = fetch_contributions("MD-Mushfiqur123")
    if not all_data:
        # Fallback to cached data if network unavailable
        cache_file = os.path.join(os.path.dirname(__file__), "cached_contributions.json")
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                all_data = json.load(f)
        else:
            return

    # Cache latest
    try:
        cache_file = os.path.join(os.path.dirname(__file__), "cached_contributions.json")
        with open(cache_file, "w") as f:
            json.dump(all_data, f, indent=2)
    except Exception:
        pass

    recent = all_data[-31:]
    days_data = []
    max_val = max(d.get("count", 0) for d in recent)

    for d in recent:
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        day_str = str(dt.day)
        count = d.get("count", 0)
        days_data.append((day_str, count, d["date"]))

    # Dynamic scaling for Y axis
    if max_val <= 30:
        max_y = 35.0
        y_ticks = [0, 5, 10, 15, 20, 25, 30, 35]
    elif max_val <= 50:
        max_y = 50.0
        y_ticks = [0, 10, 20, 30, 40, 50]
    elif max_val <= 70:
        max_y = 70.0
        y_ticks = [0, 10, 20, 30, 40, 50, 60, 70]
    else:
        max_y = math.ceil(max_val / 10.0) * 10.0
        step = max(5, int(max_y / 7))
        y_ticks = list(range(0, int(max_y) + step, step))

    width = 870
    height = 360
    margin_left = 75
    margin_right = 35
    margin_top = 58
    margin_bottom = 54

    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    baseline_y = margin_top + plot_h

    n_points = len(days_data)
    coords = []
    for i, (day, val, date_str) in enumerate(days_data):
        x = margin_left + (i / (n_points - 1)) * plot_w
        y = margin_top + plot_h - (val / max_y) * plot_h
        coords.append((x, y, day, val, date_str))

    # Monotone Cubic Hermite Interpolation
    n = len(coords)
    x = [c[0] for c in coords]
    y = [c[1] for c in coords]

    dx = [x[i+1] - x[i] for i in range(n-1)]
    dy = [y[i+1] - y[i] for i in range(n-1)]
    m = [dy[i] / dx[i] for i in range(n-1)]

    tangents = [0.0] * n
    tangents[0] = m[0]
    tangents[-1] = m[-1]
    for i in range(1, n-1):
        if m[i-1] * m[i] <= 0:
            tangents[i] = 0.0
        else:
            tangents[i] = (m[i-1] + m[i]) / 2.0

    path_segments = [f"M {x[0]:.2f} {y[0]:.2f}"]
    for i in range(n-1):
        h = dx[i]
        cp1x = x[i] + h / 3.0
        cp1y = y[i] + tangents[i] * h / 3.0
        cp2x = x[i+1] - h / 3.0
        cp2y = y[i+1] - tangents[i+1] * h / 3.0

        if coords[i][3] == 0 and coords[i+1][3] == 0:
            cp1y = baseline_y
            cp2y = baseline_y
        else:
            cp1y = min(cp1y, baseline_y)
            cp2y = min(cp2y, baseline_y)

        path_segments.append(f"C {cp1x:.2f} {cp1y:.2f}, {cp2x:.2f} {cp2y:.2f}, {x[i+1]:.2f} {y[i+1]:.2f}")

    line_path = " ".join(path_segments)
    area_path = f"{line_path} L {x[-1]:.2f} {baseline_y:.2f} L {x[0]:.2f} {baseline_y:.2f} Z"

    # Grid Lines (Dotted)
    h_grid = []
    for val in y_ticks:
        grid_y = margin_top + plot_h - (val / max_y) * plot_h
        h_grid.append(f'''
      <line x1="{margin_left}" y1="{grid_y:.1f}" x2="{width - margin_right}" y2="{grid_y:.1f}" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1" stroke-dasharray="2 3"/>
      <text x="{margin_left - 10}" y="{grid_y + 3.5:.1f}" fill="#CBD5E1" font-size="11" font-family="'JetBrains Mono', 'Segoe UI', monospace" font-weight="500" text-anchor="end">{val}</text>''')

    v_grid = []
    for i, (px, py, day, val, date_str) in enumerate(coords):
        v_grid.append(f'''
      <line x1="{px:.1f}" y1="{margin_top}" x2="{px:.1f}" y2="{baseline_y:.1f}" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1" stroke-dasharray="2 3"/>
      <text x="{px:.1f}" y="{baseline_y + 17}" fill="#CBD5E1" font-size="11" font-family="'JetBrains Mono', 'Segoe UI', monospace" font-weight="500" text-anchor="middle">{day}</text>''')

    # Data Point Markers
    dots = []
    for px, py, day, val, date_str in coords:
        is_peak = val == max_val and val > 0
        dots.append(f'''
      <g class="data-point {'peak-node' if is_peak else ''}">
        <circle cx="{px:.1f}" cy="{py:.1f}" r="4.0" fill="#FFFFFF" stroke="#00F0FF" stroke-width="1.8"/>
        {'<circle cx="' + f"{px:.1f}" + '" cy="' + f"{py:.1f}" + '" r="6.5" fill="none" stroke="#00F0FF" stroke-width="1" opacity="0.6" class="radar-ping"/>' if is_peak else ''}
      </g>''')

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@400;500;700&amp;display=swap');
      
      .title {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 15px;
        font-weight: 600;
        fill: #FFFFFF;
        letter-spacing: 0.02em;
      }}
      .axis-title {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 11px;
        font-weight: 500;
        fill: #FFFFFF;
        letter-spacing: 0.03em;
      }}
      
      .line-curve {{
        stroke-dasharray: 2400;
        stroke-dashoffset: 2400;
        animation: drawLine 2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      }}
      
      .area-fill {{
        opacity: 0;
        animation: fadeInArea 1.5s ease 0.4s forwards;
      }}
      
      .data-point {{
        opacity: 0;
        animation: fadeInPoints 0.6s ease 1s forwards;
      }}
      
      .radar-ping {{
        animation: ping 2.2s cubic-bezier(0, 0, 0.2, 1) infinite;
        transform-origin: center;
      }}
      
      @keyframes drawLine {{
        to {{
          stroke-dashoffset: 0;
        }}
      }}
      
      @keyframes fadeInArea {{
        to {{
          opacity: 1;
        }}
      }}
      
      @keyframes fadeInPoints {{
        to {{
          opacity: 1;
        }}
      }}
      
      @keyframes ping {{
        0% {{
          r: 4;
          opacity: 0.9;
        }}
        75%, 100% {{
          r: 11;
          opacity: 0;
        }}
      }}
    </style>
    
    <!-- Neon Glow Filter for Line Curve -->
    <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2.5" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>

    <!-- Shaded Fill Gradient -->
    <linearGradient id="area-gradient" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#00F0FF" stop-opacity="0.28" />
      <stop offset="50%" stop-color="#38BDF8" stop-opacity="0.14" />
      <stop offset="85%" stop-color="#1E1B4B" stop-opacity="0.06" />
      <stop offset="100%" stop-color="#000000" stop-opacity="0.0" />
    </linearGradient>
  </defs>

  <!-- Outer Main Container Box -->
  <rect width="{width}" height="{height}" fill="#000000" rx="4" ry="4" stroke="rgba(255, 255, 255, 0.25)" stroke-width="1"/>

  <!-- Top Title -->
  <text x="{width / 2}" y="32" class="title" text-anchor="middle">My Contributions</text>

  <!-- Y-Axis Label (Rotated) -->
  <text x="{-height / 2 + 5}" y="24" class="axis-title" text-anchor="middle" transform="rotate(-90)">Contributions</text>

  <!-- X-Axis Label -->
  <text x="{width / 2}" y="{height - 10}" class="axis-title" text-anchor="middle">Days</text>

  <!-- Inner Plot Area Frame -->
  <rect x="{margin_left}" y="{margin_top}" width="{plot_w}" height="{plot_h}" fill="transparent" stroke="rgba(255, 255, 255, 0.2)" stroke-width="1"/>

  <!-- Horizontal Grid Lines & Y Ticks -->
  <g class="grid-lines">
    {''.join(h_grid)}
  </g>

  <!-- Vertical Grid Lines & X Ticks -->
  <g class="grid-lines">
    {''.join(v_grid)}
  </g>

  <!-- Area Gradient Fill -->
  <path d="{area_path}" fill="url(#area-gradient)" class="area-fill"/>

  <!-- Glowing Line Curve -->
  <path d="{line_path}" fill="none" stroke="#00F0FF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" filter="url(#neon-glow)" class="line-curve"/>

  <!-- Data Points -->
  <g class="data-points">
    {''.join(dots)}
  </g>
</svg>
'''
    return svg_content

if __name__ == '__main__':
    svg = generate_svg()
    if svg:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        out_file = os.path.join(base_dir, "assets", "contribution-pulse-graph.svg")
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"Generated REAL live SVG: {out_file} ({len(svg)} bytes)")
