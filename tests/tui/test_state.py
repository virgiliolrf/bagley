from bagley.tui.state import AppState, TabState, OsInfo, detect_os


def test_detect_os_returns_fields():
    info = detect_os()
    assert info.system in {"Windows", "Linux", "Darwin"}
    assert isinstance(info.release, str)
    assert isinstance(info.distro, str)           # "" when not Linux
    assert info.eof in {"Ctrl+D", "Ctrl+Z, Enter"}
    assert isinstance(info.pty_stream, bool)


def test_tabstate_defaults():
    t = TabState(id="recon", kind="recon")
    assert t.chat == []
    assert t.react_history == []
    assert t.cmd_history == []
    assert t.killchain_stage == 0
    assert t.creds == []
    assert t.notes_md == ""


def test_appstate_starts_with_recon_tab():
    os_info = detect_os()
    st = AppState(os_info=os_info)
    assert len(st.tabs) == 1
    assert st.tabs[0].id == "recon"
    assert st.tabs[0].kind == "recon"
    assert st.active_tab == 0
