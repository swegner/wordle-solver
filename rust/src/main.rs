use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {
    let dictionary = wordle_solver::load_words_file(wordle_solver::DICTIONARY_FILE)?;
    let possible_solutions = wordle_solver::load_words_file(wordle_solver::SOLUTIONS_FILE)?;

    wordle_solver::play_wordle(&dictionary, &possible_solutions)
}
