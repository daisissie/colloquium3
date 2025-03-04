import pandas as pd
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx

# Path to your CSV file
csv_path = '/Users/daiyu/Documents/github_mac/colloquium3/csv_output/locations_henry-david-thoreau_walden.csv'

# Load the CSV file
df = pd.read_csv(csv_path)

if __name__ == '__main__':
    app.run(debug=False)

# Check if the 'context' column exists
if 'context' not in df.columns:
    raise ValueError("CSV file does not contain a 'context' column.")
    
# Convert the 'context' column to a list of strings
texts = df['context'].astype(str).tolist()

# Create TF-IDF matrix for the texts
vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = vectorizer.fit_transform(texts)

# Compute cosine similarity matrix between texts
cosine_sim = cosine_similarity(tfidf_matrix)

# Set a similarity threshold to decide if texts are "overlapping"
threshold = 0.2  # adjust this value as needed

# Build the network graph
G = nx.Graph()

# Add nodes to the graph (using index as identifier and a truncated text as label)
for i, text in enumerate(texts):
    short_label = text[:40] + ('...' if len(text) > 40 else '')
    G.add_node(i, label=short_label)

# Add edges for pairs of texts with similarity above the threshold
num_texts = len(texts)
for i in range(num_texts):
    for j in range(i+1, num_texts):
        if cosine_sim[i][j] >= threshold:
            G.add_edge(i, j, weight=cosine_sim[i][j])

# Visualize the graph
pos = nx.spring_layout(G, seed=42)  # positions for all nodes
plt.figure(figsize=(12, 8))
nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=500)
labels = nx.get_node_attributes(G, 'label')
nx.draw_networkx_labels(G, pos, labels, font_size=8)

# Draw edges with width proportional to similarity weight
edges = G.edges(data=True)
edge_widths = [d['weight'] * 5 for (_, _, d) in edges]
nx.draw_networkx_edges(G, pos, width=edge_widths)

plt.title("Text Overlap and Relationship Network")
plt.axis('off')
plt.show()