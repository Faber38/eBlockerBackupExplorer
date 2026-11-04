import pytest
from eblocker_backup_explorer.app_parser import AppDataError, WEBSITE_MODULE, parse_apps


def test_own_domains_unicode(module):
    app, = parse_apps({"modules": [module]})
    assert not app.builtin and app.enabled
    assert app.domains == ("one.example", "two.example", "192.0.2.1")
    assert app.matches("äöü") and app.matches("FREIGABE") and app.matches("TWO.EXAMPLE")
    assert app.matches("192.0.2") and not app.matches("missing.example")


def test_builtin_disabled_state_override(module):
    module["builtin"] = True
    app, = parse_apps({"modules": [module], "enabledStates": {"10001": False}})
    assert app.builtin and not app.enabled and app.status == "Deaktiviert"


def test_disabled_fallback(module):
    module["enabled"] = False
    assert not parse_apps({"modules": [module]})[0].enabled


def test_websites_only_allowlist_not_stale_labels(module):
    module.update(id=9998, name=WEBSITE_MODULE, builtin=True, hidden=True,
                  labels={"stale.example": "Ignorieren"})
    apps = parse_apps({"modules": [module]})
    assert len(apps) == 3
    assert all(a.website and not a.builtin for a in apps)
    assert all(a.name != "stale.example" for a in apps)


def test_single_domain_own_app_is_not_website(module):
    module["whitelistedDomains"] = ["one.example"]
    assert not parse_apps({"modules": [module]})[0].website


@pytest.mark.parametrize("field,value", [("enabled", "false"), ("builtin", 1), ("id", True),
    ("name", None), ("description", "text"), ("whitelistedDomains", [1]), ("whitelistedIPs", None)])
def test_invalid_fields(module, field, value):
    module[field] = value
    with pytest.raises(AppDataError):
        parse_apps({"modules": [module]})


@pytest.mark.parametrize("data", [None, [], {}, {"modules": [None]}, {"modules": [], "enabledStates": []}])
def test_invalid_shape(data):
    with pytest.raises(AppDataError):
        parse_apps(data)


def test_duplicate_ids(module):
    with pytest.raises(AppDataError):
        parse_apps({"modules": [module, module]})


def test_empty_modules():
    assert parse_apps({"modules": []}) == ()
