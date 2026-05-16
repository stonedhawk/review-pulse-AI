from core.analyzer import ReviewAnalyzer

def print_markdown_table(cluster_stats):
    if not cluster_stats:
        print("No stats to display.")
        return

    # Sort by priority score descending
    sorted_stats = sorted(cluster_stats.items(), key=lambda x: x[1]['priority_score'], reverse=True)

    print("\n### Review Clusters & Priority Report")
    print("| Cluster ID | Cluster Name | Count | Avg Rating | Priority Score |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    for c_id, stats in sorted_stats:
        name = stats.get('name', 'Unknown').replace('|', '-') # sanitize for markdown
        count = stats.get('count', 0)
        avg_rating = stats.get('avg_rating', 0.0)
        score = stats.get('priority_score', 0.0)
        print(f"| {c_id} | {name} | {count} | {avg_rating} | **{score}** |")
    print("\n")

def main():
    print("Starting Analysis & Prioritization Process...")
    analyzer = ReviewAnalyzer()
    stats = analyzer.run_analysis()
    
    if stats:
        print_markdown_table(stats)
        print("Analysis completed successfully.")
    else:
        print("Analysis completed, but no clusters were generated or updated.")

if __name__ == "__main__":
    main()
