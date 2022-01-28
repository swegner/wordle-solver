import contextlib

from absl.testing import absltest

import simulation
import solver_lib

# Convenience Aliases
_GameState = solver_lib.GameState
_GuessOutcome = solver_lib.GuessOutcome
_LetterOutcome = solver_lib.LetterOutcome


class GameStateTests(absltest.TestCase):
  def test_update_all_unrelated_letters_incorrect_noop(self):
    state = _GameState(dictionary=['foo'], possible_solutions=['foo'])
    state.update(_GuessOutcome(letters=[
      ('b', _LetterOutcome.ABSENT),
      ('a', _LetterOutcome.ABSENT),
      ('r', _LetterOutcome.ABSENT)
    ]))
    
    self.assertIn('foo', state.potential_solutions)

  def test_update_containing_letter_incorrect_word_removed(self):
    state = _GameState(dictionary=['foo'], possible_solutions=['foo'])
    state.update(_GuessOutcome(letters=[
      # 'f' is in `foo`; other letters are unrelated
      ('f', _LetterOutcome.ABSENT),
      ('a', _LetterOutcome.ABSENT),
      ('r', _LetterOutcome.ABSENT)
    ]))
    
    self.assertNotIn('foo', state.potential_solutions)


class RegressionTests(absltest.TestCase):

  @contextlib.contextmanager

  def assertNotRaises(self):
    try:
      yield
    except Exception as e:
      raise AssertionError('Raised unexpected exception.') from e

  """Test cases based on previous seen bugs."""
  def test_abate(self):
    dictionary = solver_lib.load_words_file(solver_lib.DICTIONARY_FILE)
    possible_solutions = solver_lib.load_words_file(solver_lib.SOLUTIONS_FILE)

    with self.assertNotRaises():
      num_guesses = simulation.simulate_game(
        dictionary, possible_solutions, solution_word='abate')

    self.assertGreater(num_guesses, 0)


if __name__ == '__main__':
  absltest.main()
