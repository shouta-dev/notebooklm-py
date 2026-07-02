"""Tests for GET_NOTEBOOK payload shape."""

from notebooklm import _core, _notebooks, _sources


def test_get_notebook_params_include_live_tail_slot():
    """GET_NOTEBOOK should use the live six-slot payload shape."""
    expected = [
        "nb_123",
        None,
        [2, None, None, [1, None, None, None, None, None, None, None, None, None, [1]]],
        None,
        0,
        [[None, None, []]],
    ]

    assert _core._get_notebook_params("nb_123") == expected
    assert _notebooks._get_notebook_params("nb_123") == expected
    assert _sources._get_notebook_params("nb_123") == expected
