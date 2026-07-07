from src.agent.intent import Intent, classify


def test_bare_url_is_scrape():
    assert classify("https://example.com") is Intent.SCRAPE


def test_scrape_keyword():
    assert classify("scrape this page for me") is Intent.SCRAPE


def test_content_keyword_thai():
    assert classify("เขียนแคปชั่นขายกาแฟ") is Intent.CONTENT


def test_analyze_keyword():
    assert classify("analyze last month's revenue") is Intent.ANALYZE


def test_support_keyword():
    assert classify("I need a refund for my order") is Intent.SUPPORT


def test_code_keyword():
    assert classify("fix this python bug for me") is Intent.CODE


def test_default_is_chat():
    assert classify("hello, how are you?") is Intent.CHAT
