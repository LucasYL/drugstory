import json
import random

import pytest

from drugstory.engine.game import new_game
from drugstory.engine.save import save
from drugstory.ui import cli as cli_module
from drugstory.ui.cli import CLI, main
from tests.test_game import check_invariants


class Player:
    """看提示答题的假玩家：先按剧本走，剧本用完就按默认的方式玩。"""

    def __init__(self, script=(), main_moves=40, main_answer="f"):
        self.script = list(script)
        self.main_moves = main_moves
        self.main_answer = main_answer
        self.transcript: list[str] = []

    def input(self, prompt: str) -> str:
        if self.script:
            answer = self.script.pop(0)
        elif prompt.strip() == ">":
            self.main_moves -= 1
            if self.main_moves < 0:
                raise EOFError
            answer = self.main_answer
        elif "签哪一位" in prompt or "怎么办" in prompt:
            answer = "1"
        elif "[y/N]" in prompt:
            answer = "y"
        else:
            answer = ""
        self.transcript.append(f"{prompt}{answer}")
        return answer

    def print(self, *args, **kwargs) -> None:
        self.transcript.append(" ".join(str(a) for a in args))

    @property
    def text(self) -> str:
        return "\n".join(self.transcript)


def play(content, player, seed=3, tmp_path=None):
    state = new_game(seed, content)
    ui = CLI(
        state,
        content,
        input_fn=player.input,
        print_fn=player.print,
        delay=0,
        autosave=(tmp_path / "autosave.json") if tmp_path else None,
    )
    ui.run()
    return state


def test_a_first_drug_from_start_to_launch(content, tmp_path):
    # 立项 EGFR × 小分子 → 在招聘网站招毒理 → 签第一位，并加进项目 → 之后一路快进
    player = Player(script=["n", "1", "1", "", "h", "1", "3"], main_moves=30)
    state = play(content, player, tmp_path=tmp_path)
    text = player.text
    assert "立项：EGFR × 小分子" in text
    assert "还没有毒理组，要把" in text
    assert "I 期结果" in text
    assert "获批上市" in text or "没过关" in text
    assert "第 1 年年报" in text
    assert (tmp_path / "autosave.json").exists()
    assert state.notebook["egfr|small_molecule"].tier == 2
    check_invariants(state, content)


def test_menus_can_be_opened_and_left(content):
    script = ["k", "d", "u", "0", "b", "n", "c", "0", "t", "0", "p", "?", "zzz"]
    player = Player(script=script, main_moves=0)
    play(content, player)
    text = player.text
    assert "笔记本还是空的" in text
    assert "还没有药上市" in text
    assert "下一级：研发中心" in text
    assert "不认识这个命令" in text
    assert "再见" in text


def test_bad_input_is_asked_again(content):
    player = Player(script=["n", "9", "abc", "1", "1", "7 7", "1"], main_moves=0)
    state = play(content, player)
    assert player.text.count("❌") >= 3
    assert state.projects and state.projects[0].team_ids == [state.teams[0].id]


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_random_input_never_crashes(content, tmp_path, monkeypatch, seed):
    monkeypatch.chdir(tmp_path)
    rng = random.Random(seed)
    commands = ["", "", "f", "n", "p", "t", "h", "c", "u", "b", "k", "d", "s", "?", "x"]
    answers = ["", "0", "1", "1", "2", "3", "4", "1 2", "y", "n", "abc", "99", "-1"]
    budget = {"left": 1500}
    state = new_game(seed, content)

    def fuzz(prompt: str) -> str:
        budget["left"] -= 1
        if budget["left"] < 0:
            raise EOFError
        check_invariants(state, content)
        return rng.choice(commands if prompt.strip() == ">" else answers)

    CLI(state, content, input_fn=fuzz, print_fn=lambda *a, **k: None, delay=0, autosave=None).run()
    check_invariants(state, content)


def test_main_loads_a_save(content, tmp_path, monkeypatch, capsys):
    state = new_game(42, content)
    path = tmp_path / "save.json"
    save(state, path)

    def no_more_input(prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", no_more_input)
    main(["--load", str(path), "--fast"])
    out = capsys.readouterr().out
    assert "第 1 年 1 月 第 1 周" in out and "再见" in out


def test_main_rejects_a_broken_save(tmp_path, capsys):
    path = tmp_path / "broken.json"
    path.write_text(json.dumps({"version": 99}), encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["--load", str(path)])
    assert "存档版本" in capsys.readouterr().out


def test_money_format():
    assert cli_module.money(4820.4) == "¥4,820 万"
