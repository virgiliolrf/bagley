from bagley.agent.parser import extract, strip_tool_calls


def test_single_tool_call():
    text = 'Recon first.\n<tool_call>{"name": "shell", "arguments": {"cmd": "nmap -sV 10.10.10.5"}}</tool_call>'
    calls = extract(text)
    assert len(calls) == 1
    assert calls[0].name == "shell"
    assert calls[0].arguments == {"cmd": "nmap -sV 10.10.10.5"}


def test_multiple_tool_calls():
    text = '<tool_call>{"name":"shell","arguments":{"cmd":"id"}}</tool_call>\nand\n<tool_call>{"name":"shell","arguments":{"cmd":"whoami"}}</tool_call>'
    calls = extract(text)
    assert len(calls) == 2
    assert calls[0].arguments["cmd"] == "id"
    assert calls[1].arguments["cmd"] == "whoami"


def test_malformed_json_skipped():
    text = '<tool_call>{name: invalid}</tool_call> <tool_call>{"name":"shell","arguments":{"cmd":"ls"}}</tool_call>'
    calls = extract(text)
    assert len(calls) == 1
    assert calls[0].arguments["cmd"] == "ls"


def test_no_tool_call():
    assert extract("Just plain text, nothing to see here.") == []


def test_strip_keeps_prose():
    text = 'Right, scan time.\n<tool_call>{"name":"shell","arguments":{"cmd":"nmap 10.10.10.5"}}</tool_call>\nThat should do it.'
    assert strip_tool_calls(text) == "Right, scan time.\n\nThat should do it."


def test_multiline_arguments():
    text = '<tool_call>{"name":"shell","arguments":{"cmd":"echo one\\nsecond line"}}</tool_call>'
    calls = extract(text)
    assert len(calls) == 1
    assert "\n" in calls[0].arguments["cmd"]
