"""xworld_v1 checkpoint choice: the best held + style step and a second one at least 500 steps away."""
from explainer_engine.training.pods import xworld_v1_pick as pk


def test_two_best_steps_never_neighbours():
    s = {250: {"held": .7, "style": .6}, 1500: {"held": .8, "style": .7}, 1750: {"held": .8, "style": .69},
         2500: {"held": .78, "style": .7}}
    assert pk.rank(s) == [1500, 2500]


def test_held_samples_map_to_the_build_samples():
    assert pk.HELD == {0: (0, 0), 1: (1, 0), 3: (0, 1)}
