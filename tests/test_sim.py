from drugstory.sim.run import report, run, write_csv


def test_simulation_runs_and_reports(content, tmp_path):
    results = run(2, ["newbie", "steady", "aggressive"], content, years=3)
    assert len(results) == 6
    text = report(results)
    for name in ("新手", "稳健", "激进"):
        assert name in text
    path = tmp_path / "results.csv"
    write_csv(results, path)
    assert path.read_text(encoding="utf-8").count("\n") == 7
