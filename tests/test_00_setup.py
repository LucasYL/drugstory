from lemonade.hello import greeting


def test_greeting():
    assert greeting("小明") == "欢迎来到柠檬水摊，小明！"


def test_greeting_uses_the_name():
    assert greeting("Ada") == "欢迎来到柠檬水摊，Ada！"
