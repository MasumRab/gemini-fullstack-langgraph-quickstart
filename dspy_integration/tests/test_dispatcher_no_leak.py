"""Order-dependent guard: the mocked ``dspy_helm`` package must not leak.

``test_dispatcher.py`` installs a fake ``dspy_helm`` package into
``sys.modules`` for the duration of each of its tests. This module is collected
afterwards (``test_dispatcher`` < ``test_dispatcher_no_leak``), so reaching it
with the name still in ``sys.modules`` means the fixture's teardown is leaking
mocks into every later test in the same process.

If ``dspy_helm`` ever becomes a real dependency, this assertion is the wrong
shape and should be replaced with a check that the real package is importable.
"""

import sys


def test_fake_dspy_helm_package_does_not_survive_teardown():
    assert "dspy_helm" not in sys.modules
