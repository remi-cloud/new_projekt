"""Axiom desk helpers (no network)."""

from app.axiom.client import axiom_auth_configured, tracked_wallets


def test_tracked_wallets_parse(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "axiom_wallets", "abc123, def456;abc123")
    assert tracked_wallets() == ["abc123", "def456"]


def test_kar_digital_wallet_merged(monkeypatch):
    from app.config import settings
    from app.axiom.client import kar_digital_wallet, tracked_wallets, wallet_owner_kind

    monkeypatch.setattr(settings, "axiom_wallets", "other111")
    monkeypatch.setattr(settings, "kar_digital_wallet", "KarWallet999")
    assert kar_digital_wallet() == "KarWallet999"
    assert tracked_wallets()[0] == "KarWallet999"
    assert wallet_owner_kind("KarWallet999") == "kar_digital"
    assert wallet_owner_kind("other111") == "wallet"


def test_terminal_url_solana():
    from app.launch_scout.terminal_url import axiom_meme_url, ensure_candidate_urls, terminal_url

    mint = "DezX7iJ4W8VqRXPpWLNq6YYr5ky2nrSR1GvSa8L7pump"
    url = terminal_url(mint=mint, chain="solana")
    assert "axiom.trade/meme/" in url
    assert "chain=sol" in url
    assert "pulseChains=sol" in url
    rh = terminal_url(mint="0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF", chain="robinhood")
    assert "chain=robinhood" in rh
    assert axiom_meme_url(mint, "bsc").endswith("chain=bnb&pulseChains=bnb")
    c = ensure_candidate_urls({"mint": "0x1", "chain": "bsc", "symbol": "X", "source": "4meme", "tags": ["4meme", "bonding"]})
    assert "four.meme" in (c.get("url") or "") or "dexscreener.com/bsc/" in (c.get("url") or "")
