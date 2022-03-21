use std::collections::{HashMap, HashSet};
use std::error::Error;
use std::fs::File;
use std::io::{self, BufRead};
use std::mem;

pub const DICTIONARY_FILE: &str = "dictionary.txt";
pub const SOLUTIONS_FILE: &str = "solutions.txt";

const WORD_LENGTH: u8 = 5;
const NUM_GUESSES: u8 = 6;
const LETTERS: [char; 26] = [
  'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S',
  'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
];
const BEST_FIRST_GUESS: &str = "ROATE";

#[derive(Debug)]
struct FrequencyPredicate {
  min_occurrences: Option<u8>,
  max_occurrences: Option<u8>,
}

impl FrequencyPredicate {
  fn new() -> FrequencyPredicate {
    FrequencyPredicate {
      min_occurrences: None,
      max_occurrences: None,
    }
  }

  fn update_min(&mut self, new_min: u8) {
    match self.min_occurrences {
      None => self.min_occurrences = Some(new_min),
      Some(prev_min) => self.min_occurrences = Some(std::cmp::max(prev_min, new_min)),
    }
  }

  fn update_max(&mut self, new_max: u8) {
    match self.min_occurrences {
      None => self.max_occurrences = Some(new_max),
      Some(prev_max) => self.max_occurrences = Some(std::cmp::min(prev_max, new_max)),
    }
  }

  fn is_noop(&self) -> bool {
    matches!(self.min_occurrences, None) && matches!(self.max_occurrences, None)
  }

  fn matches(&self, num_occurrences: u8) -> bool {
    if let Some(min) = self.min_occurrences {
      if num_occurrences < min {
        return false;
      }
    }
    if let Some(max) = self.max_occurrences {
      if num_occurrences > max {
        return false;
      }
    }
    true
  }
}

struct GameState {
  // FIXME: Use a reference for dictionary
  dictionary: Vec<String>,
  possible_solutions: Vec<String>,
  is_initial_state: bool,
  letter_frequencies: HashMap<char, FrequencyPredicate>,
  possible_letters: [HashSet<char>; (WORD_LENGTH as usize)],
}

impl GameState {
  fn new(dictionary: &Vec<String>, possible_solutions: &Vec<String>) -> GameState {
    GameState {
      dictionary: dictionary.clone(),
      possible_solutions: possible_solutions.clone(),
      is_initial_state: true,
      letter_frequencies: LETTERS.map(|l| (l, FrequencyPredicate::new())).into(),
      possible_letters: [(); (WORD_LENGTH as usize)].map(|_| HashSet::from(LETTERS)),
    }
  }

  fn calculate_best_guess(&self) -> &str {
    // println!("Calculating best guess..");
    if self.is_initial_state {
      return BEST_FIRST_GUESS;
    }

    if self.possible_solutions.len() == 1 {
      return &self.possible_solutions[0];
    }

    let mut best_word: Option<&str> = None;
    let mut max_gain: Option<f32> = None;

    for word in &self.dictionary {
      let gain = self.calculate_information_gain(word, &self.possible_solutions);
      let new_best = match max_gain {
        None => true,
        Some(mg) => gain > mg,
      };
      if new_best {
        // println!("New best guess so far: {} ({})", word, gain);
        best_word = Some(word);
        max_gain = Some(gain);
      }
    }

    best_word.unwrap()
  }

  fn calculate_information_gain(&self, word: &str, potential_solutions: &Vec<String>) -> f32 {
    let mut outcomes = HashMap::with_capacity(potential_solutions.len());
    for potential_solution in potential_solutions {
      let outcome = evaluate_guess(word, potential_solution);
      outcomes
        .entry(outcome.letter_outcomes())
        .and_modify(|n| *n += 1)
        .or_insert(1);
    }

    let total_potential_solutions: u32 = potential_solutions.len().try_into().unwrap();
    outcomes
      .values()
      .map(|n| {
        let outcome_probability = (*n as f32) / (total_potential_solutions as f32);
        ((total_potential_solutions - n) as f32) * outcome_probability
      })
      .sum()
  }

  fn update(&mut self, guess: GuessOutcome) {
    self._update_state(guess);
    self._update_potential_solutions();
  }

  fn summary(&self) -> String {
    format!(
      "{} possible solutions: [{}]",
      self.possible_solutions.len(),
      self._possible_solutions_summary()
    )
  }

  fn _possible_solutions_summary(&self) -> String {
    String::from("FIXME")
  }

  fn _update_state(&mut self, guess: GuessOutcome) {
    let mut info_by_letter: HashMap<char, Vec<(usize, LetterOutcome)>> =
      HashMap::with_capacity(WORD_LENGTH.into());
    for (i, (letter, letter_outcome)) in guess.letters.into_iter().enumerate() {
      info_by_letter
        .entry(letter)
        .and_modify(|v| v.push((i, letter_outcome)))
        .or_insert_with(|| vec![(i, letter_outcome)]);
    }
    self.is_initial_state = false;

    for (letter, letter_outcomes) in info_by_letter.into_iter() {
      let mut has_absent = false;
      let mut non_absent_count = 0;
      for (i, outcome) in letter_outcomes {
        match outcome {
          LetterOutcome::Correct => {
            let possible_letters = &mut self.possible_letters[i];
            assert!(possible_letters.contains(&letter));
            possible_letters.clear();
            possible_letters.insert(letter);
            non_absent_count += 1;
          }
          LetterOutcome::Present => {
            self.possible_letters[i].remove(&letter);
            non_absent_count += 1;
          }
          LetterOutcome::Absent => {
            self.possible_letters[i].remove(&letter);
            has_absent = true;
          }
        }
        if non_absent_count > 0 {
          self
            .letter_frequencies
            .get_mut(&letter)
            .unwrap()
            .update_min(non_absent_count);
        }
        if has_absent {
          self
            .letter_frequencies
            .get_mut(&letter)
            .unwrap()
            .update_max(non_absent_count);
        }
      }
    }
  }

  fn _update_potential_solutions(&mut self) {
    let mut possible_solutions = mem::take(&mut self.possible_solutions);
    possible_solutions.retain(|w| self._word_fits(w));
    self.possible_solutions = possible_solutions;
  }

  fn _word_fits(&self, word: &str) -> bool {
    let mut word_letter_frequencies: HashMap<char, u8> = HashMap::new();
    for (i, letter) in word.chars().enumerate() {
      if !self.possible_letters[i].contains(&letter) {
        return false;
      }
      word_letter_frequencies
        .entry(letter)
        .and_modify(|x| *x += 1)
        .or_insert(1);
    }
    for (letter, frequency_predicate) in self.letter_frequencies.iter() {
      if frequency_predicate.is_noop() {
        continue;
      }
      let letter_occurences = word_letter_frequencies.get(letter).or(Some(&0)).unwrap();
      if !frequency_predicate.matches(*letter_occurences) {
        return false;
      }
    }

    true
  }
}

#[derive(Clone, Debug, Copy, Eq, PartialEq, Hash)]
enum LetterOutcome {
  Correct, // Green: letter in solution in correct position
  Present, // Yellow: letter in solution, wrong position
  Absent,  // Black: letter not in solution
}

impl LetterOutcome {
  fn parse(outcome_char: char) -> LetterOutcome {
    match outcome_char {
      'G' => LetterOutcome::Correct,
      'Y' => LetterOutcome::Present,
      'B' => LetterOutcome::Absent,
      _ => panic!("Invalid letter outcome: {}", outcome_char),
    }
  }
}

#[derive(Debug)]
struct GuessOutcome {
  letters: Vec<(char, LetterOutcome)>,
}

impl GuessOutcome {
  fn parse(word: &str, outcome_str: &str) -> GuessOutcome {
    GuessOutcome {
      letters: word
        .chars()
        .zip(outcome_str.chars().map(|oc| LetterOutcome::parse(oc)))
        .collect(),
    }
  }

  fn letter_outcomes(&self) -> Vec<LetterOutcome> {
    self.letters.iter().map(|l| l.1).collect()
  }

  fn is_win(&self) -> bool {
    self
      .letters
      .iter()
      .all(|(_, o)| matches!(o, LetterOutcome::Correct))
  }
}

fn evaluate_guess(guess: &str, solution: &str) -> GuessOutcome {
  let mut results = vec![LetterOutcome::Absent; NUM_GUESSES.into()];

  // Track whether each solution letter has been accounted for in the results.
  let mut accounted = vec![false; WORD_LENGTH.into()];

  // First, mark all letters that are exactly correct
  for (i, (guess_letter, solution_letter)) in guess.chars().zip(solution.chars()).enumerate() {
    if guess_letter == solution_letter && !accounted[i] {
      results[i] = LetterOutcome::Correct;
      accounted[i] = true;
    }
  }

  // Next, mark any letters that were prsent but in a differe position.
  // Evaluation is left-to-right, and each solution letter should only be
  // accounted once.
  for (result, guess_letter) in (&mut results).iter_mut().zip(guess.chars()) {
    if matches!(result, LetterOutcome::Correct) {
      continue;
    }
    for (acc, solution_letter) in (&mut accounted).iter_mut().zip(solution.chars()) {
      if *acc {
        continue;
      }
      if guess_letter == solution_letter {
        *result = LetterOutcome::Present;
        *acc = true;
        break;
      }
    }
  }

  GuessOutcome {
    letters: guess.chars().zip(results).collect(),
  }
}

pub fn load_words_file(path: &str) -> io::Result<Vec<String>> {
  let file = File::open(path)?;
  let lines = io::BufReader::new(file).lines();
  let words: Vec<String> = lines.map(|f| f.unwrap().to_uppercase()).collect();

  println!("Loaded {} words from `{}`", words.len(), path);
  Ok(words)
}

pub fn play_wordle(
  dictionary: &Vec<String>,
  possible_solutions: &Vec<String>,
) -> Result<(), Box<dyn Error>> {
  let mut game_state = GameState::new(dictionary, possible_solutions);

  for i in 0..NUM_GUESSES {
    println!("Playing guess: {}", i);
    let suggested_guess = game_state.calculate_best_guess();
    let outcome = prompt_guess(suggested_guess);
    if outcome.is_win() {
      println!("You win!");
      break;
    }
    game_state.update(outcome);
    println!("{}", game_state.summary());
  }
  Ok(())
}

fn prompt_guess(guess: &str) -> GuessOutcome {
  println!("Enter guess: `{}`", guess);
  let mut current_guess = guess;
  // loop {
  println!(
    "Enter the outcome for guess `{}`, encoding each letter according to its color:
  B = black
  Y = yellow
  G = green

If you used a different guess than `{}`, enter it instead.",
    current_guess, current_guess
  );
  let mut input = String::new();
  io::stdin().read_line(&mut input).unwrap();
  let outcome_str = input.trim();
  println!("Outcome string: {}", outcome_str);
  if outcome_str
    .chars()
    .all(|c| c == 'B' || c == 'Y' || c == 'G')
  {
    return GuessOutcome::parse(guess, outcome_str);
  }

  // // Something other than an outcome was entered.. should be a different guess.
  // if outcome_str.len() == 5 {
  //   current_guess = &outcome_str;
  //   continue;
  // }

  // println!("Invalid outcome string: {}", outcome_str);
  panic!("Invalid outcome string: {}", outcome_str);
}

#[cfg(test)]
mod tests {
  use super::*;

  fn simulate_game(
    dictionary: &Vec<String>,
    possible_solutions: &Vec<String>,
    solution_word: &str,
  ) -> Option<u8> {
    let mut state = GameState::new(dictionary, possible_solutions);

    println!("Simulating wordle game for solution: {}", solution_word);
    for guess_num in 1..NUM_GUESSES + 1 {
      let guess = state.calculate_best_guess();
      let outcome = evaluate_guess(guess, solution_word);
      // println!("Guess #{}: {}; Outcome: {:#?}", guess_num, guess, outcome);

      if outcome.is_win() {
        return Some(guess_num);
      }
      state.update(outcome);
    }

    None // If we get here, we didn't find a solution in time.
  }

  #[test]
  fn sample_game() {
    let dictionary = load_words_file(DICTIONARY_FILE).unwrap();
    let possible_solutions = load_words_file(SOLUTIONS_FILE).unwrap();
    let solution_word = "ABATE";

    // Should not panic
    let num_guesses = simulate_game(&dictionary, &possible_solutions, solution_word);

    assert!(matches!(num_guesses, Some(_)));
    println!("Found solution in {} guesses.", num_guesses.unwrap());
  }

  #[test]
  fn num_guesses_histogram() {
    let dictionary = load_words_file(DICTIONARY_FILE).unwrap();
    let possible_solutions = load_words_file(SOLUTIONS_FILE).unwrap();

    let mut histogram = [0; 7];
    for solution_word in possible_solutions.iter() {
      let num_guesses = simulate_game(&dictionary, &possible_solutions, solution_word);
      println!("Num guesses for {}: {:?}", solution_word, num_guesses);
      histogram[(num_guesses.unwrap_or(7) as usize) - 1] += 1;
    }

    println!("Guesses histogram: {:?}", histogram);
  }
}
