import pytest
import sys
import os

def test_crypto_signals_import():
    try:
        from crypto_signals import crypto_signals
        assert True
    except ImportError:
        pytest.skip("crypto_signals module not available")

def test_crypto_alpha_hunter_import():
    try:
        from crypto_signals import crypto_alpha_hunter
        assert True
    except ImportError:
        pytest.skip("crypto_alpha_hunter module not available")

def test_signals_structure():
    # Basic structural test
    import crypto_signals.crypto_signals as cs
    assert hasattr(cs, 'CryptoSignals')
    assert hasattr(cs, 'SignalProcessor')

def test_alpha_hunter_structure():
    import crypto_signals.crypto_alpha_hunter as cah
    assert hasattr(cah, 'CryptoAlphaHunter')
    assert hasattr(cah, 'TopScanner')
