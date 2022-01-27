import collections
import dataclasses
import enum
import io
import textwrap
from typing import Dict, List, Sequence, Set

from absl import app
from absl import flags
from absl import logging

BEST_FIRST_GUESS = 'lares'  # cached from previous run
USE_CACHE = flags.DEFINE_bool(
    'use_cache', True,
    'Whether to use the best guess cached from previous runs.')

WORD_LENGTH = 5
NUM_GUESSES = 6

WORDS_FILE = 'dictionary.txt'


def load_word_dictionary(words_file: io.TextIOBase) -> List[str]:
  word_bank: List[str] = list()
  for line in words_file:
    word = line.strip()
    assert len(word) == WORD_LENGTH, word
    word_bank.append(word)
  logging.info('Loaded dictionary with %d words.', len(word_bank))
  return word_bank


class LetterOutcome(enum.Enum):
  CORRECT_IN_POSITION = 'G'  # green: letter in solution in correct position
  CORRECT_WRONG_POSITION = 'Y'  # yellow: letter in solution, wrong position
  INCORRECT = 'B'  # black: letter not in solution


@dataclasses.dataclass
class GuessOutcome:
  letters: Dict[str, LetterOutcome]


@dataclasses.dataclass
class GameState:

  def __init__(self, word_bank: List[str]) -> None:
    self._word_bank = word_bank
    self._known_letters: Set[str] = set()
    self._possible_letters = [
        'abcdefghijklmnopqrstuvwxyz' for _ in range(WORD_LENGTH)
    ]

  @property
  def word_bank(self) -> List[str]:
    return self._word_bank

  def __str__(self) -> str:
    return '\n'.join([
        f'Remaining words: {len(self._word_bank)}, ({self._word_bank[:5]})',
        f'Known letters:{"".join(self._known_letters)}',
        'Possible letters:',
    ] + [
        f'  {i}: {letters}' for i, letters in enumerate(self._possible_letters)
    ])

  def calculate_best_guess(self) -> str:
    best_word = ''
    max_gain = 0.0
    for i, word in enumerate(self._word_bank):
      logging.log_every_n_seconds(
          logging.INFO, 'Calcuating information gain from %dth word: %s', 1, i,
          word)
      gain = calculate_information_gain(word, self._word_bank)
      if gain > max_gain:
        best_word = word
        max_gain = gain
        logging.info('Highest information gain so far: %s (%f)', best_word,
                     max_gain)
    return best_word

  def update(self, guess: GuessOutcome) -> None:
    self._update_letters(guess)
    self._update_word_bank()

  def _update_letters(self, guess: GuessOutcome) -> None:
    for i, (letter, outcome) in enumerate(guess.letters.items()):
      if outcome == LetterOutcome.CORRECT_IN_POSITION:
        assert letter in self._possible_letters[i]
        self._known_letters.add(letter)
        self._possible_letters[i] = letter
      elif outcome == LetterOutcome.CORRECT_WRONG_POSITION:
        self._known_letters.add(letter)
        self._possible_letters[i] = self._possible_letters[i].replace(
            letter, '')
      else:
        assert outcome == LetterOutcome.INCORRECT
        for j in range(len(self._possible_letters)):
          self._possible_letters[j] = self._possible_letters[j].replace(
              letter, '')

  def _update_word_bank(self) -> None:
    self._word_bank = [w for w in self._word_bank if self._word_fits(w)]

  def _word_fits(self, word: str) -> bool:
    for known_letter in self._known_letters:
      if known_letter not in word:
        return False
    for i, letter in enumerate(word):
      if letter not in self._possible_letters[i]:
        return False
    return True


def parse_outcome(word: str, outcome_str: str) -> GuessOutcome:
  logging.debug('outcome_str: %s', outcome_str)
  return GuessOutcome(
      collections.OrderedDict(
          ((c, LetterOutcome(o)) for c, o in zip(word, outcome_str))))


def calculate_information_gain(word: str, word_bank: List[str]) -> float:
  outcomes: Dict[str, int] = collections.defaultdict(int)
  for possible_solution in word_bank:
    outcome = ''
    for word_char, solution_char in zip(word, possible_solution):
      if word_char == solution_char:
        outcome += str(LetterOutcome.CORRECT_IN_POSITION)
      elif word_char in possible_solution:
        outcome += str(LetterOutcome.CORRECT_WRONG_POSITION)
      else:
        outcome += str(LetterOutcome.INCORRECT)
    outcomes[outcome] += 1

  num_possibilities = len(word_bank)
  expected_information_gain = 0.0
  # logging.debug('Word %s has %d outcomes: %s', word, len(outcomes), outcomes)
  for num_outcome_solutions in outcomes.values():
    outcome_probability = float(num_outcome_solutions) / num_possibilities
    outcome_information_gain = ((num_possibilities - num_outcome_solutions) *
                                outcome_probability)
    expected_information_gain += outcome_information_gain

  return expected_information_gain


def prompt_guess(guess: str) -> GuessOutcome:
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


def main(argv: Sequence[str]) -> None:
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')

  with io.open(WORDS_FILE) as f:
    word_bank = load_word_dictionary(f)
    state = GameState(word_bank)

  for guess_num in range(NUM_GUESSES):
    suggested_guess = (
        BEST_FIRST_GUESS if guess_num == 0 and USE_CACHE.value else
        state.calculate_best_guess())

    outcome = prompt_guess(suggested_guess)
    state.update(outcome)
    logging.info('Game state:\n%s', state)


if __name__ == '__main__':
  app.run(main)
