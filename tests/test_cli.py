from fin_assist.cli import main


def test_check_exit_codes_and_output(capsys):
    assert main(["check", "For 2026 the IRA limit is $7,000.", "--year", "2026"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("REVIEW") and "that's the 2025 figure; 2026 is 7,500" in out
    assert main(["check", "For 2026 the IRA limit is $7,500.", "--year", "2026"]) == 0


def test_facts_filter(capsys):
    main(["facts", "taxable_maximum"])
    assert "184,500" in capsys.readouterr().out
