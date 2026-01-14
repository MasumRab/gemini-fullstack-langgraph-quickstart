import time
import random
import string

# Original Implementation
def original_insert_citation_markers(text, citations_list):
    sorted_citations = sorted(
        citations_list,
        key=lambda c: (c["end_index"], c.get("start_index", 0)),
        reverse=True,
    )
    modified_text = text
    for citation_info in sorted_citations:
        end_idx = citation_info["end_index"]
        marker_to_insert = ""
        for segment in citation_info["segments"]:
            marker_to_insert += f" [{segment['label']}]({segment['short_url']})"
        modified_text = (
            modified_text[:end_idx] + marker_to_insert + modified_text[end_idx:]
        )
    return modified_text

# Optimized Implementation
def optimized_insert_citation_markers(text, citations_list):
    # Sort by end_index ascending, then start_index ascending
    sorted_citations = sorted(
        citations_list,
        key=lambda c: (c["end_index"], c.get("start_index", 0))
    )

    parts = []
    last_idx = 0

    for citation in sorted_citations:
        end_idx = citation["end_index"]

        # Append text chunk from last position to current citation position
        if end_idx > last_idx:
            parts.append(text[last_idx:end_idx])
            last_idx = end_idx
        elif end_idx < last_idx:
             # This should not happen if sorted correctly by end_index
             pass

        # Build marker
        marker_to_insert = ""
        for segment in citation["segments"]:
            marker_to_insert += f" [{segment['label']}]({segment['short_url']})"

        parts.append(marker_to_insert)

    # Append remaining text
    if last_idx < len(text):
        parts.append(text[last_idx:])

    return "".join(parts)

def generate_data():
    print("Generating random data...")
    text = "".join(random.choices(string.ascii_letters + " ", k=100000))
    citations = []
    for i in range(1000):
        idx = random.randint(0, len(text))
        citations.append({
            "end_index": idx,
            "start_index": max(0, idx - 5),
            "segments": [{"label": f"Ref{i}", "short_url": "http://google.com"}]
        })
    return text, citations

def generate_non_colliding_data():
    print("Generating non-colliding data...")
    text = "a" * 20000
    citations = []
    for i in range(500):
        idx = i * 20 # Spaced out
        if idx > len(text): break
        citations.append({
            "end_index": idx,
            "start_index": idx,
            "segments": [{"label": "R", "short_url": "u"}]
        })
    return text, citations

if __name__ == "__main__":
    # Test 1: Random (Collision likely)
    text, citations = generate_data()
    print(f"Text Length: {len(text)}, Citations: {len(citations)}")

    start = time.time()
    res_orig = original_insert_citation_markers(text, citations)
    orig_time = time.time() - start
    print(f"Original Time: {orig_time:.4f}s")

    start = time.time()
    res_opt = optimized_insert_citation_markers(text, citations)
    opt_time = time.time() - start
    print(f"Optimized Time: {opt_time:.4f}s")

    if opt_time > 0:
        print(f"Speedup: {orig_time / opt_time:.2f}x")

    # Test 2: Non-Colliding (Exact Match Required)
    text_nc, citations_nc = generate_non_colliding_data()
    res_orig_nc = original_insert_citation_markers(text_nc, citations_nc)
    res_opt_nc = optimized_insert_citation_markers(text_nc, citations_nc)

    if res_orig_nc == res_opt_nc:
        print("Non-colliding exact match: PASSED")
    else:
        print("Non-colliding exact match: FAILED")
        print(f"Orig: {res_orig_nc[:100]}")
        print(f"Opt:  {res_opt_nc[:100]}")
