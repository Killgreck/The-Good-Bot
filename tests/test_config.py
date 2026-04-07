from antigravity import config


def test_default_safe_mode_is_dry_run():
    assert config.DRY_RUN is True


def test_core_contract_addresses_are_configured():
    assert config.CHAIN_ID == 137
    assert config.CTF_EXCHANGE.startswith("0x")
    assert config.NEGRISK_CTF_EXCHANGE.startswith("0x")
    assert config.CLOB_HOST == "https://clob.polymarket.com"


def test_abi_file_exists():
    assert config.CTF_EXCHANGE_ABI_PATH.exists()
