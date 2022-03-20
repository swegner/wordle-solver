"""Benchmark to measure the performance of the solver."""

from typing import List

from absl import logging
from absl.testing import absltest

import simulation
import solver_lib


class GameStateTests(absltest.TestCase):
    def test_all_solutions(self):
      dictionary = solver_lib.load_words_file(solver_lib.DICTIONARY_FILE)
      solutions = solver_lib.load_words_file(solver_lib.SOLUTIONS_FILE)
      logging.info('Testing with %d dictionary words and %d solutions', len(dictionary), len(solutions))

      histogram = {x+1: 0 for x in range(solver_lib.NUM_GUESSES)}
      histogram[-1] = 0

      for solution_word in solutions:
        num_guesses = simulation.simulate_game(dictionary, solutions, solution_word)
        logging.log_every_n_seconds(logging.INFO, 
          'Found solution for `%s` in %d guesses', 1, solution_word, num_guesses)
        histogram[num_guesses] += 1

      # FIXME: Do something other than fail?
      self.fail(f'Benchmark results: {histogram}')



if __name__ == '__main__':
  absltest.main()
