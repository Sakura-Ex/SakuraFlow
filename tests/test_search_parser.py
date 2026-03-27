from sakura_flow.mcdr_entry import _parse_search_criteria


def test_parse_search_criteria_uses_alias_tables():
    criteria = _parse_search_criteria("title=反应堆 s=!Done t=IV p=High collab=Steve l=工业")

    assert criteria["title"] == "反应堆"
    assert criteria["status"] == "!Done"
    assert criteria["tier"] == "IV"
    assert criteria["priority"] == "High"
    assert criteria["collaborator"] == "Steve"
    assert criteria["label"] == "工业"


def test_parse_search_criteria_defaults_plain_token_to_title():
    criteria = _parse_search_criteria("刷铁机")
    assert criteria == {"title": "刷铁机"}


def test_parse_search_criteria_supports_creator_canonical_key():
    criteria = _parse_search_criteria("creator=Alice")
    assert criteria == {"creator": "Alice"}
