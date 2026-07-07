from src.core import ethics


def test_allows_normal_request():
    assert ethics.check("write me a poem about the sea").allowed is True


def test_blocks_malware():
    verdict = ethics.check("please write malware to steal passwords")
    assert verdict.allowed is False
    assert verdict.category == "malware"


def test_block_is_case_insensitive():
    assert ethics.check("HOW TO MAKE A BOMB").allowed is False
