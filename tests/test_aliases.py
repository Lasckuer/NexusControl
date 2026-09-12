from app.utils.aliases import prettify_name

def test_prettify_name_with_alias():
    assert prettify_name("my-dhczomw-container") == "Nexus Control"
    assert prettify_name("redis-n6welm1") == "Redis"
    assert prettify_name("nexus_control") == "Nexus Control"

def test_prettify_name_with_hashes():
    # Имя с compose хэшем на конце
    result = prettify_name("frontend-service-1234567890ab")
    assert result == "Frontend Service"

def test_prettify_name_clean():
    assert prettify_name("my_custom_service") == "My Custom Service"
    assert prettify_name("") == "Unknown"
