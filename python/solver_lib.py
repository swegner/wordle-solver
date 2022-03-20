import collections
import dataclasses
import enum
import io
import itertools
from typing import Dict, List, Set, Tuple, Optional

from absl import logging
from absl import flags


DICTIONARY_FILE = 'dictionary.txt'
SOLUTIONS_FILE = 'solutions.txt'
WORD_LENGTH = 5

NUM_GUESSES = 6


BEST_FIRST_GUESS = 'ROATE'  # cached from previous run
USE_CACHE = flags.DEFINE_bool(
    'use_cache', True,
    'Whether to use the best guess cached from previous runs.')


def load_words_file(path: str) -> List[str]:
  with io.open(path) as words_file:
    word_bank: List[str] = list()
    for line in words_file:
      word = line.strip()
      assert len(word) == WORD_LENGTH, word
      word_bank.append(word.upper())
    logging.info('Loaded %s with %d words.', path, len(word_bank))
    return word_bank


class LetterOutcome(enum.Enum):
  CORRECT = 'G'  # green: letter in solution in correct position
  PRESENT = 'Y'  # yellow: letter in solution, wrong position
  ABSENT = 'B'  # black: letter not in solution

  def __str__(self) -> str:
    if self == LetterOutcome.CORRECT:
      return '🟩'
    elif self == LetterOutcome.PRESENT:
      return '🟨'
    else:
      assert self == LetterOutcome.ABSENT
      return '⬛'


@dataclasses.dataclass
class GuessOutcome:
  letters: List[Tuple[str, LetterOutcome]]

  def __str__(self) -> str:
    return ''.join((l.value for _, l in self.letters))

  @property
  def is_win(self):
    return all((o == LetterOutcome.CORRECT for _, o in self.letters))


@dataclasses.dataclass
class FrequencyPredicate:
  min_occurrences: Optional[int] = None
  max_occurrences: Optional[int] = None

  def __str__(self) -> str:
    return '[{min},{max}]'.format(
      min=self.min_occurrences if self.min_occurrences is not None else '?',
      max=self.max_occurrences if self.max_occurrences is not None else '?',
    )

  @property
  def is_empty(self) -> bool:
    return (self.min_occurrences is None and 
            self.max_occurrences is None)

  def update_min(self, new_min: int) -> None:
    if self.min_occurrences is None:
      self.min_occurrences = new_min
    else:
      self.min_occurrences = max(self.min_occurrences, new_min)

  def update_max(self, new_max: int) -> None:
    if self.max_occurrences is not None:
      assert self.max_occurrences == new_max
    else:
      self.max_occurrences = new_max

  def matches(self, num_occurences: int) -> bool:
    if self.min_occurrences is not None and num_occurences < self.min_occurrences:
      return False
    if self.max_occurrences is not None and num_occurences > self.max_occurrences:
      return False
    return True


LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


@dataclasses.dataclass
class SuggestedGuess:
  word: str
  information_gain: float


# Refactor this into a 'algorithm' base class + implementation?
@dataclasses.dataclass
class GameState:

  def __init__(self, dictionary: List[str], possible_solutions: List[str]) -> None:
    assert dictionary, 'Dictonary cannot be empty'
    assert possible_solutions, 'Initial solution word bank cannot be empty'
    self._dictionary = dictionary
    self._potential_solutions = possible_solutions
    self._word_length = len(dictionary[0])
    self._letter_frequencies = {l: FrequencyPredicate() for l in LETTERS}
    self._possible_letters = [
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for _ in range(self._word_length)
    ]
    self._is_initial_state = True

  @property
  def potential_solutions(self) -> List[str]:
    return self._potential_solutions

  def __str__(self) -> str:
    return '\n'.join([
        f'Remaining words: {len(self._potential_solutions)}, ({self._potential_solutions[:5]})',
        'Letter frequencies: {}'.format(', '.join(
          (f'{l}:{f}' for l, f in self._letter_frequencies.items() if not f.is_empty))),
        'Possible letters:',
    ] + [
        f'  {i}: {letters}' for i, letters in enumerate(self._possible_letters)
    ])

  # FIXME: Refactor to return a `SuggestedGuess`
  def calculate_best_guess(self) -> str:
    if self._is_initial_state and USE_CACHE.value:
      return BEST_FIRST_GUESS

    if len(self._potential_solutions) == 1:
      return self._potential_solutions[0]

    best_word = ''
    max_gain = -1
    for i, word in enumerate(self._dictionary):
      logging.log_every_n_seconds(
          logging.INFO, 'Calcuating information gain from %dth word: %s', 1, i,
          word)
      gain = calculate_information_gain(word, self._potential_solutions)
      if gain > max_gain:
        best_word = word
        max_gain = gain
        logging.debug('Highest information gain so far: %s (%f)', best_word,
                     max_gain)
    assert best_word
    return best_word

  def calculate_guesses(self) -> List[SuggestedGuess]:
    guesses: List[SuggestedGuess] = []
    for i, word in enumerate(self._dictionary):
      logging.log_every_n_seconds(
          logging.INFO, 'Calcuating information gain from %dth word: %s', 1, i,
          word)
      guesses.append(SuggestedGuess(
        word, 
        calculate_information_gain(word, self._potential_solutions)))
    return guesses

  def update(self, guess: GuessOutcome) -> None:
    assert isinstance(guess, GuessOutcome), type(guess)

    self._update_state(guess)
    self._update_potential_solutions()
    logging.debug('Updated game state:\n%s', self)

  def _update_state(self, guess: GuessOutcome) -> None:
    info_by_letter: Dict[str, List[Tuple[int, LetterOutcome]]] = collections.defaultdict(list)
    self._is_initial_state = False
    for i, (letter, outcome) in enumerate(guess.letters):
      info_by_letter[letter].append((i, outcome))

    for letter, letter_outcomes in info_by_letter.items():
      logging.debug('Guess outcomes for letter %s: %s', letter, letter_outcomes)
      has_absent = False
      non_absent_count = 0
      for i, outcome in letter_outcomes:
        if outcome == LetterOutcome.CORRECT:
          assert letter in self._possible_letters[i], (
            'Letter {letter} not in set of possible letters for position {i}: {possible_letters}'.format(
              letter=letter,
              i=i,
              possible_letters=self._possible_letters[i]))
          self._possible_letters[i] = letter
          non_absent_count += 1
        elif outcome == LetterOutcome.PRESENT:
          self._possible_letters[i] = self._possible_letters[i].replace(
              letter, '')
          non_absent_count += 1
        else:
          assert outcome == LetterOutcome.ABSENT, outcome
          self._possible_letters[i] = self._possible_letters[i].replace(
              letter, '')
          has_absent = True
      if non_absent_count:
        self._letter_frequencies[letter].update_min(non_absent_count)
      if has_absent:
        self._letter_frequencies[letter].update_max(non_absent_count)

  def _update_potential_solutions(self) -> None:
    self._potential_solutions = [w for w in self._potential_solutions if self._word_fits(w)]

  def _word_fits(self, word: str) -> bool:
    word_letter_frequencies: Dict[str, int] = collections.defaultdict(int)
    for i, letter in enumerate(word):
      if letter not in self._possible_letters[i]:
        return False
      word_letter_frequencies[letter] += 1

    for letter, frequency_predicate in self._letter_frequencies.items():
      letter_occurences = word_letter_frequencies[letter]
      if not frequency_predicate.matches(letter_occurences):
        return False

    return True


def calculate_information_gain(word: str, potential_solutions: List[str]) -> float:
  outcomes: Dict[str, int] = collections.defaultdict(int)
  for potential_solution in potential_solutions:
    outcome = evaluate_guess(guess=word, solution=potential_solution)
    outcomes[str(outcome)] += 1

  total_potential_solutions = len(potential_solutions)
  expected_information_gain = 0.0
  # logging.debug('Word %s has %d outcomes: %s', word, len(outcomes), outcomes)
  for num_outcome_solutions in outcomes.values():
    outcome_probability = float(num_outcome_solutions) / total_potential_solutions
    outcome_information_gain = ((total_potential_solutions - num_outcome_solutions) *
                                outcome_probability)
    expected_information_gain += outcome_information_gain

  return expected_information_gain


def evaluate_guess(*, guess: str, solution: str) -> GuessOutcome:
    results = list(itertools.repeat(LetterOutcome.ABSENT, len(guess)))

    # Track whether each solution letter has been accounted in
    # the results.
    accounted = [False for _ in range(len(guess))]

    # First, mark all letters that are exactly correct
    for i in range(len(guess)):
        if guess[i] == solution[i] and not accounted[i]:
            results[i] = LetterOutcome.CORRECT
            accounted[i] = True

    # Next, mark any letters that were present but in a different
    # position. Evaluation is left-to-right, and each solution
    # letter should only be accounted once.
    for i in range(len(guess)):
        if results[i] == LetterOutcome.CORRECT:
            continue
        guess_letter = guess[i]
        for j in range(len(solution)):
            if accounted[j]:
                continue
            if guess_letter == solution[j]:
                results[i] = LetterOutcome.PRESENT
                accounted[j] = True
                break

    return GuessOutcome(letters=list(zip(guess, results)))
