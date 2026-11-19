"""``python -m explainer_engine.episode run|status <episode>``: the one runner of v4.3 (``episode/run.py``)."""
import sys

from explainer_engine.episode.run import main

sys.exit(main())
