"""APIs for simulating a Wordle game."""

from typing import List

from absl import logging

import solver_lib


# Convenience Aliases
_GameState = solver_lib.GameState


def simulate_game(
    dictionary: List[str], 
    possible_solutions: List[str],
    solution_word: str) -> int:
  try:
    return _simulate_internal(dictionary, possible_solutions, solution_word)
  except Exception as e:
    raise RuntimeError(f'Failed while simulating game for solution: {solution_word}') from e


def _simulate_internal(
    dictionary: List[str], 
    possible_solutions: List[str],
    solution_word: str) -> int:
  state = _GameState(dictionary, possible_solutions)

  logging.debug('Simulating Wordle game for solution: %s', solution_word)
  for guess_num in range(1, solver_lib.NUM_GUESSES+1):
    # DO NOT SUBMIT: Move this internal
    # DO NOT SUBMIT: Remove or refactor
    # guess = ('lares' if guess_num == 1 else state.calculate_best_guess())
    guess = state.calculate_best_guess()
    outcome = solver_lib.evaluate_guess(guess=guess, solution=solution_word)
    logging.debug('Guess #%d: %s; Outcome: %s', guess_num, guess, outcome)

    if outcome.is_win:
      return guess_num
    state.update(outcome)

  # If we get here, we didn't find the solution in time
  return -1
