import collections
import textwrap
from typing import Dict, List, Sequence, Set

from absl import app
from absl import logging

import solver_lib


# Convenience Aliases
_GameState = solver_lib.GameState
_GuessOutcome = solver_lib.GuessOutcome
_LetterOutcome = solver_lib.LetterOutcome


def play_wordle(dictionary: List[str], possible_solutions: List[str]) -> None:
  state = _GameState(dictionary, possible_solutions=possible_solutions)

  for _ in range(solver_lib.NUM_GUESSES):
    suggested_guess = state.calculate_best_guess()
    outcome = prompt_guess(suggested_guess)
    if outcome.is_win:
      print('You win!')
      return
    state.update(outcome)
    logging.info('Game state:\n%s', state)


def prompt_guess(guess: str) -> _GuessOutcome:
  print(f'Enter guess: `{guess.upper()}`')
  while True:
    outcome_str = input(
        textwrap.dedent("""
      Enter the outcome, encoding each letter according to its color:
        B = black
        Y = yellow
        G = green
      """))
    try:
      return parse_outcome(guess, outcome_str)
    except ValueError as e:
      print(f'Invalid outcome string `{outcome_str}: {e}')


def parse_outcome(word: str, outcome_str: str) -> _GuessOutcome:
  logging.debug('outcome_str: %s', outcome_str)
  return _GuessOutcome([(c, _LetterOutcome(o)) for c, o in zip(word, outcome_str)])


def main(argv: Sequence[str]) -> None:
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')

  dictionary = solver_lib.load_words_file(solver_lib.DICTIONARY_FILE)
  possible_solutions = solver_lib.load_words_file(solver_lib.SOLUTIONS_FILE)
  play_wordle(dictionary, possible_solutions)


if __name__ == '__main__':
  app.run(main)
