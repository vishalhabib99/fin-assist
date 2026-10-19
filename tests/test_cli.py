from fin_assist.cli import main


def test_check_exit_codes_and_output(capsys):
    assert main(["check", "For 2026 the IRA limit is $7,000.", "--year", "2026"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("REVIEW") and "that's the 2025 figure; 2026 is 7,500" in out
    assert main(["check", "For 2026 the IRA limit is $7,500.", "--year", "2026"]) == 0


def test_facts_filter(capsys):
    main(["facts", "taxable_maximum"])
    assert "184,500" in capsys.readouterr().out


def test_large_and_cents_figures_print_in_full(capsys):
    from fin_assist.cli import main
    main(["check", "For 2026, the AMT exemption for married couples filing jointly starts to phase out at $1,252,700. "
                   "The 2026 Medicare Part B premium is $185.00."])
    out = capsys.readouterr().out
    assert "2026 is 1,000,000" in out and "2026 is 202.90" in out and "e+0" not in out
