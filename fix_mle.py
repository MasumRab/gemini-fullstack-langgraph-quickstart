with open("backend/src/evaluation/mle_bench.py", "r") as f:
    lines = f.readlines()
with open("backend/src/evaluation/mle_bench.py", "w") as f:
    for line in lines:
        if "for task in dataset:" in line or "pass" in line or "results = []" in line or "scores = []" in line:
            continue
        if line.strip().startswith("#"):
            if "TODO" not in line and "mle_bench" not in line and "See docs" not in line:
                continue
        f.write(line)

with open("backend/src/evaluation/deep_research_bench.py", "r") as f:
    lines = f.readlines()
with open("backend/src/evaluation/deep_research_bench.py", "w") as f:
    for line in lines:
        if "for task in dataset:" in line or "pass" in line or "results = []" in line or "scores = []" in line:
            continue
        if line.strip().startswith("#"):
            if "TODO" not in line and "deep_bench" not in line and "See docs" not in line:
                continue
        f.write(line)
