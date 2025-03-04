import pandas as pd
import random
import nltk
import re
from nltk.tokenize import word_tokenize
from nltk.tokenize.treebank import TreebankWordDetokenizer

# Download necessary NLTK resources (if not already available)
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

# Function to generate a light (pastel) color
def generate_light_color():
    # Generate values in a higher range to ensure lightness
    r = random.randint(200, 255)
    g = random.randint(200, 255)
    b = random.randint(200, 255)
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)

# 1. Read CSV and remove duplicate contexts
file_path = "/Users/daiyu/Documents/github_mac/colloquium3/csv_output/locations_henry-david-thoreau_walden.csv"
df = pd.read_csv(file_path)
contexts = df["Context"].drop_duplicates().tolist()

# Set of adjectives to ignore (case-insensitive)
ignored_adjs = {"ok", "such", "other", "own", "many", "few", "more", "most", "less", "least"}

# 2. Compute adjective frequencies (case-insensitive) across all contexts.
#    Only adjectives (tags starting with 'JJ') are considered, ignoring those in ignored_adjs.
adj_freq = {}
for text in contexts:
    tokens = word_tokenize(text)
    tags = nltk.pos_tag(tokens)
    for token, tag in tags:
        if tag.startswith('JJ'):
            lower_token = token.lower()
            if lower_token in ignored_adjs:
                continue
            adj_freq[lower_token] = adj_freq.get(lower_token, 0) + 1

# Filter to adjectives that are repeated (frequency > 1)
repeated_candidates = {adj: freq for adj, freq in adj_freq.items() if freq > 1}

# 3. Sort the repeated adjectives by frequency (highest first) and take the top 15.
top15 = sorted(repeated_candidates.items(), key=lambda x: x[1], reverse=True)[:15]
# Create a dictionary for the top 15 adjectives with an assigned light color.
repeated_adjs = {adj: generate_light_color() for adj, freq in top15}

# 4. Function to process text:
#    - Non-adjective tokens are wrapped in a span with 30% opacity.
#    - Adjectives that are among the top 15 (in repeated_adjs) are highlighted with full opacity.
#    - Adjectives not in the top 15 or in ignored_adjs are removed.
def highlight_text(text):
    tokens = word_tokenize(text)
    tags = nltk.pos_tag(tokens)
    new_tokens = []
    for token, tag in tags:
        lower_token = token.lower()
        if tag.startswith('JJ'):
            if lower_token in ignored_adjs:
                continue
            if lower_token in repeated_adjs:
                color = repeated_adjs[lower_token]
                new_tokens.append(
                    f'<span class="highlight" data-word="{lower_token}" data-color="{color}" style="background-color: {color}; opacity: 1;">{token}</span>'
                )
            else:
                continue
        else:
            new_tokens.append(
                f'<span class="non-highlight" style="opacity: 0.3;">{token}</span>'
            )
    joined = " ".join(new_tokens)
    joined = re.sub(r'\s+([,.!?;:])', r'\1', joined)
    return joined

# Process each context using the highlight_text function.
highlighted_contexts = [highlight_text(text) for text in contexts]

# 5. Build HTML content.
# Note: We do not set random positions in Python.
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Full Screen Layout with Top 15 Repeated Highlighted Adjectives</title>
  <style>
    html, body {{
      margin: 0;
      padding: 0;
      overflow: hidden; /* Disable scrolling */
      width: 100vw;
      height: 100vh;
    }}
    .container {{
      position: relative;
      width: 100vw;
      height: 100vh;
      border: 1px solid #000;
    }}
    .context-box {{
      position: absolute;
      width: 200px;
      height: 150px;
      overflow: auto;
      border: 1px solid #ccc;
      padding: 5px;
      border-radius: 4px;
      font-family: Arial, sans-serif;
      font-size: 12px;
    }}
    .highlight {{
      font-weight: bold;
      padding: 1px;
      border-radius: 3px;
    }}
    #connections {{
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: none;
    }}
  </style>
</head>
<body>
  <div class="container" id="container">
    <!-- SVG element to draw connection lines -->
    <svg id="connections" width="100vw" height="100vh"></svg>
"""

# Output each processed context box without random positioning.
for index, context in enumerate(highlighted_contexts, start=1):
    html_content += f"""
    <div class="context-box" id="context-{index}">
      <p>{context}</p>
    </div>
    """

html_content += """
  </div>
  <script>
    // Position each context-box randomly within the full-screen container.
    window.onload = function() {
      var container = document.getElementById('container');
      var boxes = document.querySelectorAll('.context-box');
      var containerRect = container.getBoundingClientRect();
      boxes.forEach(function(box) {
        var maxLeft = containerRect.width - box.offsetWidth;
        var maxTop = containerRect.height - box.offsetHeight;
        var left = Math.floor(Math.random() * maxLeft);
        var top = Math.floor(Math.random() * maxTop);
        box.style.left = left + 'px';
        box.style.top = top + 'px';
      });
      
      // Draw SVG lines connecting identical highlighted adjectives.
      var svg = document.getElementById('connections');
      var highlightElements = document.querySelectorAll('.highlight');
      var groups = {};
      highlightElements.forEach(function(el) {
        var word = el.getAttribute('data-word').toLowerCase();
        if (!groups[word]) groups[word] = [];
        groups[word].push(el);
      });
      for (var word in groups) {
        var group = groups[word];
        if (group.length > 1) {
          for (var i = 0; i < group.length - 1; i++) {
            var rect1 = group[i].getBoundingClientRect();
            var rect2 = group[i+1].getBoundingClientRect();
            var containerRect = container.getBoundingClientRect();
            var x1 = rect1.left + rect1.width / 2 - containerRect.left;
            var y1 = rect1.top + rect1.height / 2 - containerRect.top;
            var x2 = rect2.left + rect2.width / 2 - containerRect.left;
            var y2 = rect2.top + rect2.height / 2 - containerRect.top;
            var line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.setAttribute("x1", x1);
            line.setAttribute("y1", y1);
            line.setAttribute("x2", x2);
            line.setAttribute("y2", y2);
            line.setAttribute("stroke", group[i].getAttribute('data-color'));
            line.setAttribute("stroke-width", "2");
            svg.appendChild(line);
          }
        }
      }
    };
  </script>
</body>
</html>
"""

# 7. Write the HTML content to a file.
output_file = "output.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"HTML file generated: {output_file}")