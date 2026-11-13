// DNA recipes (design/PRESET-ENGINE-2.md section 17): a readable form of a DNA in Sound Recorder's own words.
//
//   multi-line:  tada   slower ×2, reverse, louder   4 recorders · notes +0 +12 · unison 2 ±9¢
//                env    attack 5ms · release 350ms
//   one-line:    ding faster echo / tada slower×2 reverse louder 4rec notes+0+12 | atk 5ms rel 350ms
//   short:       for lists; at most maxLen characters, else cut at a word and ended with "…" (then not parseable)
//
// Lossless: fromRecipe(toRecipe(d)) has exactly the v3 canonical form of d (canonical3), for every form except a
// short form that had to be cut. Every v1, v2 and v3 token has words; a token without words (a later version's)
// is written verbatim in braces, {Dl3}, and kept.
// Parsing is lenient: any case, ASCII for the symbols (x for ×, +- for ±, c for ¢, .. or - for –), any of the
// three spellings of a word, commas and · as spaces. Errors name the word and its position.
#pragma once
#include <string>

namespace bsynth3 {

enum class RecipeForm { Lines, OneLine, Short };

std::string toRecipe(const std::string &dna, RecipeForm form, size_t maxLen = 60);

struct RecipeError {
    size_t pos = 0;          // byte offset of the offending word in the recipe text
    std::string word;        // the word
    std::string message;     // what was expected
};
// Returns false (and fills err) when the text is not a recipe. On success dna is the canonical DNA (canonical3).
bool fromRecipe(const std::string &text, std::string &dna, RecipeError *err = nullptr);

}  // namespace bsynth3
