from pipeline import config


def test_uk_filters_cover_each_set_once():
    groups = [g for gs, _ in config.UK_CATEGORY_BOARDS.values() for g in gs]
    assert len(groups) == len(set(groups))
    assert set(groups) <= {g for g, _ in config.CATEGORY_BOARDS.values()} | {"search_tech"}
