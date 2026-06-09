from src.services.diff.csharp_filter import CSharpFilter

def test_csharp_file_detection():
    file_name = "LoginService.cs"

    assert file_name.endswith(".cs")