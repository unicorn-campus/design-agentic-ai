from pathlib import Path


def test_unselected_path_files_are_absent() -> None:
    package = Path(__file__).parents[1] / "help_desk_knowledge"
    absent = {
        "recursive_sql.py",
        "separate_search_cluster.py",
        "portal_search.py",
        "vector_glossary.py",
        "rewriting.py",
        "multi_query.py",
        "hyde.py",
        "step_back.py",
        "reranker.py",
        "compression.py",
        "fusion.py",
    }
    assert not ({path.name for path in package.iterdir()} & absent)
