"""
Demo mode: mock Play Store reviews and a local keyword clusterer, so the pipeline runs
end to end without Google Play or Gemini keys.

The clusterer has the same interface as GeminiClient.cluster_reviews_batch(), so the
demo exercises the real ReviewAnalyzer, priority scoring and database code.
"""
import datetime

from core.database import Review

# (review text, star rating, app version)
MOCK_REVIEWS = [
    ("Game crashes on startup every single time since the update.", 1, "2.4.0"),
    ("Crashes right after the splash screen. Can't even get to the menu.", 1, "2.4.0"),
    ("Was fine yesterday, now it crashes on launch. Pixel 7.", 1, "2.4.0"),
    ("Instant crash when I open it. Reinstalled twice, still crashing.", 1, "2.4.0"),
    ("Keeps crashing on startup after the latest patch. Please fix.", 2, "2.4.0"),
    ("App closes itself on the loading screen. Crash every time.", 1, "2.4.0"),
    ("Summon rates are a joke. 200 pulls and no featured hero.", 2, "2.4.0"),
    ("The gacha rates feel rigged. Pity is way too high.", 2, "2.3.2"),
    ("Spent money on the banner and got nothing. Rates are terrible.", 1, "2.4.0"),
    ("Pity system resets between banners, which feels unfair.", 3, "2.4.0"),
    ("Pull rates for the limited unit are way too low for the price.", 2, "2.4.0"),
    ("Can't log in. Stuck on connecting to server.", 1, "2.4.0"),
    ("Login keeps timing out, lost my daily rewards.", 2, "2.3.2"),
    ("Server error every evening during peak hours. Can't log in.", 1, "2.4.0"),
    ("Account login fails with Google sign in.", 2, "2.4.0"),
    ("Phone gets really hot after ten minutes of play.", 3, "2.4.0"),
    ("Drains my battery fast, even on low graphics.", 3, "2.3.2"),
    ("Battery drain is bad and the device heats up.", 3, "2.4.0"),
    ("Love the art style and the story. Great game!", 5, "2.4.0"),
    ("Best puzzle RPG I've played this year.", 5, "2.4.0"),
    ("Fun events, friendly community. Five stars.", 5, "2.3.2"),
    ("Great game, play it every day on the train.", 5, "2.4.0"),
    ("Really fun, the new chapter is great.", 5, "2.4.0"),
]

# First match wins, so the more specific clusters come first.
KEYWORD_CLUSTERS = [
    ("STARTUP_CRASH", "Crash on Startup", ["crash", "closes itself"]),
    ("LOGIN_SERVER", "Login / Server", ["log in", "login", "server", "sign in"]),
    ("GACHA_RATES", "Gacha Rates", ["rates", "pity", "pulls", "banner", "summon"]),
    ("BATTERY_HEAT", "Battery / Heat", ["battery", "hot", "heats"]),
]
GENERIC_CLUSTER = ("GENERIC_PRAISE", "Generic Praise")

TEMPLATE_DRAFTS = {
    "STARTUP_CRASH": "Sorry about the crashes on launch. We found the cause in 2.4.0 and a fix is in testing now. Thanks for the device details.",
    "LOGIN_SERVER": "Sorry you couldn't log in. We're adding server capacity for peak hours and will restore any missed daily rewards.",
    "GACHA_RATES": "Thanks for the honest feedback on summon rates. We're reviewing pity carry-over between banners with the team.",
    "BATTERY_HEAT": "Thanks for flagging the battery drain. We're profiling heat on mid-range devices and will ship a frame cap option.",
    "GENERIC_PRAISE": "Thank you for playing and for the kind words. See you in the next event!",
}


class KeywordClusterer:
    """Stand-in for GeminiClient: assigns each review to the first cluster whose keyword it contains."""

    label = "the local keyword clusterer (demo, no API calls)"

    def cluster_reviews_batch(self, reviews_data: list[dict]) -> list[dict]:
        results = []
        for review in reviews_data:
            text = review["review_text"].lower()
            cluster_id, cluster_name = GENERIC_CLUSTER
            justification = "No issue keyword found."
            for c_id, c_name, keywords in KEYWORD_CLUSTERS:
                hit = next((k for k in keywords if k in text), None)
                if hit:
                    cluster_id, cluster_name = c_id, c_name
                    justification = f"Mentions '{hit}'."
                    break
            results.append({
                "review_id": review["review_id"],
                "cluster_id": cluster_id,
                "cluster_name": cluster_name,
                "justification": justification,
            })
        return results


def template_draft(cluster_id: str) -> str:
    """Canned reply used in place of a Gemini draft when running without keys."""
    return TEMPLATE_DRAFTS.get(cluster_id, TEMPLATE_DRAFTS["GENERIC_PRAISE"])


def seed_mock_reviews(db) -> int:
    start = datetime.datetime(2026, 10, 1, 9, 0)
    for i, (text, rating, version) in enumerate(MOCK_REVIEWS):
        db.add(Review(
            review_id=f"demo-{i + 1:03d}",
            reviewer_name=f"Player {i + 1}",
            rating=rating,
            review_text=text,
            review_date=start + datetime.timedelta(hours=7 * i),
            app_version=version,
        ))
    db.commit()
    return len(MOCK_REVIEWS)


def print_summary(cluster_stats: dict) -> None:
    """Compact ranked view for the terminal. The full markdown goes to the report file."""
    ranked = sorted(cluster_stats.values(), key=lambda s: s["priority_score"], reverse=True)
    print("SCORE  REVIEWS  AVG  CLUSTER")
    for s in ranked:
        print(f"{s['priority_score']:>5.1f}  {s['count']:>7}  {s['avg_rating']:.1f}  {s['name']}")


def write_report(cluster_stats: dict, path: str) -> None:
    ranked = sorted(cluster_stats.items(), key=lambda item: item[1]["priority_score"], reverse=True)
    lines = ["# ReviewPulse demo report", ""]
    for c_id, stats in ranked:
        lines += [
            f"## {stats['name']} (Priority Score: {stats['priority_score']})",
            f"- Issues Count: {stats['count']}",
            f"- Average Rating: {stats['avg_rating']}/5",
            f"- Draft Response (template in demo mode): _{template_draft(c_id)}_",
            "",
        ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
