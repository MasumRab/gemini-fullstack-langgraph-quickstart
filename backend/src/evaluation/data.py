import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BENCHMARK_URLS = {
    "criteria": "https://huggingface.co/datasets/muset-ai/DeepResearch-Bench/resolve/main/criteria.jsonl",
    "reference": "https://huggingface.co/datasets/muset-ai/DeepResearch-Bench/resolve/main/reference.jsonl",
    # "test_queries": "https://huggingface.co/datasets/muset-ai/DeepResearch-Bench/resolve/main/test.jsonl"
}

def download_benchmark_data(output_dir: str = "data/benchmark"):
    """Download DeepResearch-Bench evaluation data, fallback to mock"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Check if requests is available
    try:
        import requests
        has_requests = True
    except ImportError:
        has_requests = False
        logger.warning("Requests library not found, skipping download and creating mock data.")

    for name, url in BENCHMARK_URLS.items():
        file_path = output_path / f"{name}.jsonl"
        if file_path.exists():
            logger.info(f"{name} already exists at {file_path}")
            continue

        downloaded = False
        if has_requests:
            logger.info(f"Downloading {name}...")
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    with open(file_path, 'w') as f:
                        f.write(response.text)
                    logger.info(f"✓ Saved to {file_path}")
                    downloaded = True
                else:
                    logger.warning(f"✗ Failed to download {name}: {response.status_code}")
            except Exception as e:
                logger.warning(f"Error downloading {name}: {e}")

        if not downloaded:
            create_mock_data(name, output_path)

def create_mock_data(dataset_name: str, output_path: Path):
    """Create small mock dataset for testing"""
    if dataset_name == "criteria":
        mock_data = [
            {
                "query_id": "mock_001",
                "query": "Impact of AI on healthcare diagnostics",
                "subgoals": [
                    "Current AI diagnostic tools in use",
                    "Accuracy improvements vs human doctors",
                    "Regulatory challenges and FDA approvals"
                ],
                "expected_evidence_types": ["clinical_studies", "news", "regulatory_docs"],
                "difficulty": "medium",
                "domain": "healthcare"
            },
            {
                "query_id": "mock_002",
                "query": "Latest trends in renewable energy storage",
                "subgoals": [
                    "Battery technology advances",
                    "Grid-scale storage solutions",
                    "Cost reduction trajectories"
                ],
                "expected_evidence_types": ["research_papers", "industry_reports"],
                "difficulty": "hard",
                "domain": "energy"
            }
        ]
    elif dataset_name == "reference":
        mock_data = [
            {
                "query_id": "mock_001",
                "reference_answer": "AI has significantly improved healthcare diagnostics by providing higher accuracy in image recognition and pattern detection. FDA has approved numerous AI tools.",
                "key_facts": [
                    {"fact": "AI diagnostic accuracy exceeds 90% in radiology", "source": "nejm.org"},
                    {"fact": "FDA approved 50+ AI diagnostic tools since 2020", "source": "fda.gov"}
                ],
                "required_sources": ["nejm.org", "fda.gov", "nature.com"],
                "min_evidence_count": 4
            },
            {
                "query_id": "mock_002",
                "reference_answer": "Renewable energy storage has advanced through lithium-ion improvements and new grid-scale solutions. Costs have dropped significantly.",
                "key_facts": [
                    {"fact": "Lithium-ion costs dropped 90% since 2010", "source": "bloomberg.com"},
                    {"fact": "Grid-scale storage capacity reached 20GW globally", "source": "iea.org"}
                ],
                "required_sources": ["iea.org", "bloomberg.com"],
                "min_evidence_count": 3
            }
        ]
    else:
        mock_data = []

    # Write mock data
    file_path = output_path / f"{dataset_name}.jsonl"
    with open(file_path, 'w') as f:
        for item in mock_data:
            f.write(json.dumps(item) + '\n')
    logger.info(f"✓ Created mock {dataset_name} data at {file_path}")
