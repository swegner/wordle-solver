import operator
from typing import List, Sequence

from absl import app

import solver_lib


# Convenience Aliases
_GameState = solver_lib.GameState


def rank_first_guesses(dictionary: List[str], possible_solutions: List[str]) -> None:
  state = _GameState(dictionary, possible_solutions=possible_solutions)
  guesses = state.calculate_guesses()
  guesses.sort(key=operator.attrgetter('information_gain'), reverse=True)
  num_solutions = len(possible_solutions)
  for i, guess in enumerate(guesses):
    print('{word}, rank={rank}, expected_remaining_words={expected_remaining_words}'.format(
      word=guess.word.upper(),
      rank=i+1,
      expected_remaining_words=num_solutions-guess.information_gain
    ))


def main(argv: Sequence[str]) -> None:
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')
  dictionary = solver_lib.load_words_file(solver_lib.DICTIONARY_FILE)
  possible_solutions = solver_lib.load_words_file(solver_lib.SOLUTIONS_FILE)
  rank_first_guesses(dictionary, possible_solutions)


if __name__ == '__main__':
  app.run(main)