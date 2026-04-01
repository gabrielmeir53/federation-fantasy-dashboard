"""One-time script to save NFL prior season matchup scores extracted from browser."""
import json

with open("data/fed_fl_prev.json", "r", encoding="utf-8") as f:
    prev = json.load(f)

ABBR_TO_NAME = {
    "ECR": "Echo Rangers", "AFC": "Alpha FC",
    "BRU": "Bravo United", "JSC": "Juliet SC",
    "INU": "India United", "CSC": "Charlie SC",
    "GLT": "Golf Town", "DAT": "Delta Athletic",
    "HFC": "Hotel FC", "FXC": "Foxtrot City",
    "LMR": "Lima Rovers", "KAT": "Kilo Athletic",
}

NAME_TO_FED = {
    "Echo Rangers": "team_05", "Alpha FC": "team_01",
    "Bravo United": "team_02", "Juliet SC": "team_10",
    "India United": "team_09", "Charlie SC": "team_03",
    "Golf Town": "team_07", "Delta Athletic": "team_04",
    "Hotel FC": "team_08", "Foxtrot City": "team_06",
    "Lima Rovers": "team_12", "Kilo Athletic": "team_11",
}

# [period, away_abbr, away_score, home_abbr, home_score, is_playoff]
raw = [
    [1,"ECR",83.42,"AFC",94.62,0],[1,"BRU",103.58,"JSC",118.66,0],[1,"INU",77.72,"CSC",95.62,0],
    [1,"GLT",79.18,"DAT",117.22,0],[1,"HFC",70.44,"FXC",103.62,0],[1,"LMR",105.66,"KAT",91.1,0],
    [2,"AFC",75.28,"GLT",103.1,0],[2,"FXC",91.38,"BRU",91.74,0],[2,"KAT",95.08,"CSC",87.88,0],
    [2,"DAT",108.3,"ECR",127.94,0],[2,"JSC",108,"HFC",83.04,0],[2,"LMR",116.22,"INU",117,0],
    [3,"DAT",101.02,"AFC",98.76,0],[3,"BRU",121.64,"HFC",83.42,0],[3,"CSC",103.66,"LMR",124.52,0],
    [3,"GLT",84.82,"ECR",108.12,0],[3,"KAT",103.72,"INU",94.52,0],[3,"FXC",97.6,"JSC",162.22,0],
    [4,"AFC",93.72,"CSC",150,0],[4,"BRU",103.1,"DAT",128.56,0],[4,"ECR",119.98,"FXC",127.82,0],
    [4,"INU",111.18,"GLT",95.92,0],[4,"HFC",91.54,"KAT",78.98,0],[4,"LMR",95.46,"JSC",95.98,0],
    [5,"AFC",97.16,"KAT",68.12,0],[5,"CSC",134.72,"BRU",106.2,0],[5,"JSC",127.18,"DAT",138.16,0],
    [5,"ECR",95.28,"LMR",101.02,0],[5,"FXC",125.74,"GLT",93.12,0],[5,"INU",120.96,"HFC",97.48,0],
    [6,"AFC",64.3,"INU",106.34,0],[6,"KAT",77.28,"BRU",77.12,0],[6,"CSC",148.08,"JSC",99.94,0],
    [6,"FXC",63.86,"DAT",97.14,0],[6,"ECR",142.88,"HFC",81.26,0],[6,"GLT",108.14,"LMR",155.5,0],
    [7,"FXC",108.5,"AFC",115.62,0],[7,"BRU",76.04,"LMR",155.24,0],[7,"DAT",99.72,"CSC",130.74,0],
    [7,"ECR",113.54,"INU",83.74,0],[7,"HFC",136.46,"GLT",63.58,0],[7,"JSC",133.26,"KAT",62.78,0],
    [8,"HFC",102.88,"AFC",77.32,0],[8,"GLT",141.24,"BRU",112.66,0],[8,"ECR",168.48,"CSC",96.86,0],
    [8,"KAT",121.3,"DAT",62.28,0],[8,"LMR",103.12,"FXC",85.78,0],[8,"JSC",94.62,"INU",63.6,0],
    [9,"AFC",98.34,"LMR",116.82,0],[9,"INU",66.02,"BRU",97.8,0],[9,"CSC",117.7,"FXC",100.5,0],
    [9,"DAT",148.5,"HFC",73.12,0],[9,"KAT",120.3,"ECR",110.18,0],[9,"GLT",73.56,"JSC",86.66,0],
    [10,"JSC",131.74,"AFC",99.48,0],[10,"BRU",114.02,"ECR",126.2,0],[10,"CSC",92.7,"GLT",103.9,0],
    [10,"INU",74.44,"DAT",139.62,0],[10,"FXC",130.6,"KAT",99.1,0],[10,"LMR",105.44,"HFC",86.3,0],
    [11,"AFC",82.92,"GLT",86.44,0],[11,"HFC",75.5,"BRU",105,0],[11,"CSC",101.14,"KAT",77.92,0],
    [11,"DAT",107.12,"LMR",128.58,0],[11,"ECR",69.34,"JSC",83.32,0],[11,"INU",71.46,"FXC",96.64,0],
    [12,"DAT",112.94,"AFC",124.8,0],[12,"BRU",87.46,"FXC",93.52,0],[12,"CSC",106.58,"INU",61.76,0],
    [12,"GLT",79.76,"ECR",114.74,0],[12,"JSC",102.52,"HFC",80.88,0],[12,"LMR",96.02,"KAT",75.66,0],
    [13,"BRU",76.2,"AFC",54.26,0],[13,"HFC",84.8,"CSC",108.04,0],[13,"ECR",144.14,"DAT",91.76,0],
    [13,"FXC",90.04,"JSC",99.54,0],[13,"KAT",95.36,"GLT",66.58,0],[13,"LMR",124.92,"INU",93.76,0],
    [14,"AFC",64.92,"ECR",102.3,0],[14,"JSC",99.86,"BRU",105.9,0],[14,"CSC",71.7,"LMR",119.04,0],
    [14,"GLT",89.94,"DAT",107.58,0],[14,"HFC",93.58,"FXC",83.04,0],[14,"KAT",102.04,"INU",103.22,0],
    [15,"None/Bye",0,"LMR",0,1],[15,"DAT",107.18,"CSC",100.86,1],
    [15,"None/Bye",0,"JSC",0,1],[15,"FXC",122.4,"ECR",129.5,1],
    [16,"DAT",145.6,"LMR",104.7,1],[16,"ECR",110.26,"JSC",109.44,1],
    [17,"DAT",111.62,"ECR",86.8,1],
]

meta_periods = {
    "1": ["2025-09-04","2025-09-10",0,"Week 1"],
    "2": ["2025-09-11","2025-09-17",0,"Week 2"],
    "3": ["2025-09-18","2025-09-24",0,"Week 3"],
    "4": ["2025-09-25","2025-10-01",0,"Week 4"],
    "5": ["2025-10-02","2025-10-08",0,"Week 5"],
    "6": ["2025-10-09","2025-10-15",0,"Week 6"],
    "7": ["2025-10-16","2025-10-22",0,"Week 7"],
    "8": ["2025-10-23","2025-10-29",0,"Week 8"],
    "9": ["2025-10-30","2025-11-05",0,"Week 9"],
    "10": ["2025-11-06","2025-11-12",0,"Week 10"],
    "11": ["2025-11-13","2025-11-19",0,"Week 11"],
    "12": ["2025-11-20","2025-11-26",0,"Week 12"],
    "13": ["2025-11-27","2025-12-03",0,"Week 13"],
    "14": ["2025-12-04","2025-12-10",0,"Week 14"],
    "15": ["2025-12-11","2025-12-17",1,"Playoffs - Round 1 (Week 15)"],
    "16": ["2025-12-18","2025-12-24",1,"Playoffs - Round 2 (Week 16)"],
    "17": ["2025-12-25","2025-12-31",1,"Playoffs - Round 3 (Week 17)"],
}

# Build matchups list
matchups = []
for r in raw:
    period, away_abbr, away_score, home_abbr, home_score, is_playoff = r
    away_name = ABBR_TO_NAME.get(away_abbr, away_abbr)
    home_name = ABBR_TO_NAME.get(home_abbr, home_abbr)
    matchups.append({
        "period": period,
        "away_name": away_name, "away_fed_id": NAME_TO_FED.get(away_name),
        "away_score": away_score,
        "home_name": home_name, "home_fed_id": NAME_TO_FED.get(home_name),
        "home_score": home_score,
        "complete": True, "is_playoff": bool(is_playoff),
    })

# Build schedule_meta
schedule_meta = {"periods": {}, "last_completed": 17}
for k, v in meta_periods.items():
    schedule_meta["periods"][k] = {
        "start": v[0], "end": v[1],
        "complete": True, "current": False,
        "is_playoff": bool(v[2]), "name": v[3],
    }

prev["matchups"] = matchups
prev["schedule_meta"] = schedule_meta

with open("data/fed_fl_prev.json", "w", encoding="utf-8") as f:
    json.dump(prev, f, indent=2, default=str)

reg = [m for m in matchups if not m["is_playoff"]]
po = [m for m in matchups if m["is_playoff"]]
print(f"Saved {len(matchups)} matchups + {len(schedule_meta['periods'])} periods")
print(f"Regular: {len(reg)} ({len(reg)//6} weeks), Playoffs: {len(po)}")
print(f"Sample Wk1: {matchups[0]['away_name']} ({matchups[0]['away_score']}) vs {matchups[0]['home_name']} ({matchups[0]['home_score']})")
print(f"Finals: {matchups[-1]['away_name']} ({matchups[-1]['away_score']}) vs {matchups[-1]['home_name']} ({matchups[-1]['home_score']})")
