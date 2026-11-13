// DNA recipes (design/PRESET-ENGINE-2.md section 17): a readable form of a DNA in Sound Recorder's own words.
//
// The canonical, editable recipe is plain printable ASCII (0x20-0x7E; lines end in \n), typable on any keyboard:
//   multi-line:  ding     faster, echo
//                tada     slower x2, reverse, louder   4 recorders  notes +0 +12  unison 2 +-9c
//                env     attack 5ms  release 350ms
//   one-line:    ding faster echo / tada slower x2 reverse louder 4rec notes +0 +12 unison 2 +-9c | atk 5ms rel 350ms
//   short:       for lists; at most maxLen characters, else cut at a word and ended with "..." (then not parseable)
// prettify() turns it into the display form by pure character substitution (x2 -> ×2, +- -> ±, 9c -> 9¢,
// 5-45 -> 5–45, two spaces -> " · ", ... -> …); asciify() turns it back exactly. UIs show the pretty form, edit and
// copy the ASCII form.
//
// Lossless: fromRecipe(toRecipe(d)) has exactly the v3 canonical form of d (canonical3), for every form except a
// short form that had to be cut, and so has fromRecipe(prettify(toRecipe(d))). Every v1, v2 and v3 token has
// words; a token without words (a later version's) is written verbatim in braces, {Dl3}, and kept.
// Parsing is lenient: any case, the pretty symbols or their ASCII, any of the three spellings of a word, commas
// and · as spaces. Errors name the word and its position.
#pragma once
#include <string>

namespace bsynth3 {

enum class RecipeForm { Lines, OneLine, Short };

std::string toRecipe(const std::string &dna, RecipeForm form, size_t maxLen = 60);   // ASCII
std::string prettify(const std::string &asciiRecipe);   // the display form
std::string asciify(const std::string &prettyRecipe);   // back to the ASCII form, exactly

struct RecipeError {
    size_t pos = 0;          // byte offset of the offending word in the recipe text
    std::string word;        // the word
    std::string message;     // what was expected
};
// Returns false (and fills err) when the text is not a recipe. On success dna is the canonical DNA (canonical3).
bool fromRecipe(const std::string &text, std::string &dna, RecipeError *err = nullptr);

}  // namespace bsynth3
