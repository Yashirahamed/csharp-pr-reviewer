from src.services.diff.diff_parser import DiffParser

def test_parser_creation():

    parser = DiffParser()

    assert parser is not None