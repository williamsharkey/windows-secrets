// User recordings (design/RECORDING.md sections 2.4, 3, 4.1, 4.2) and the .b16 state file (design/STATE.md): the
// parts both editions share, as pure functions. No file system here: the plugins do the I/O (one writer, a lock).
//   - names:     a file stem -> its DNA name (u_ + [a-z0-9_], at most 24 characters after the prefix)
//   - sha1, base64, zlib (RFC 1950 deflate / inflate, crc32): the state's embedded WAVs and the .b16 container
//   - the index (My Recordings/index.tsv) and the resolution order of a u_ name on load
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace bsynth {

// ---- names
constexpr const char *kUserPrefix = "u_";
std::string userName(const std::string &stem);           // "My Vox (2)" -> "u_my_vox_2"; "" if nothing is left
bool isUserName(const std::string &name);                // starts with u_ and is [a-z0-9_]
std::string userDisplay(const std::string &name);        // "u_vox" -> "vox" (the lists show it without the prefix)

// ---- digests and encodings
std::string sha1Hex(const void *data, size_t n);
std::string base64(const void *data, size_t n);
bool unbase64(const std::string &s, std::vector<uint8_t> &out);
uint32_t crc32(const void *data, size_t n, uint32_t crc = 0);
// zlib format (RFC 1950): deflate with fixed Huffman codes and LZ77 (a real compression, readable by any inflater,
// e.g. the browser's DecompressionStream('deflate')), and a complete inflater (stored, fixed and dynamic blocks).
std::vector<uint8_t> zlibCompress(const void *data, size_t n);
bool zlibDecompress(const void *data, size_t n, std::vector<uint8_t> &out, size_t maxOut = 64u << 20);

// ---- the .b16 state file (STATE.md 2): B16S, u16 version 1, u16 flags (bit 0 zlib), u32 length, u32 crc32, payload
std::vector<uint8_t> b16Write(const std::string &stateText, bool compress = true);
bool b16Read(const void *data, size_t n, std::string &stateText, std::string *err = nullptr);

// ---- the index of My Recordings (RECORDING.md 3.1): name, sha1, file, ms, format, saved, edition
struct UserEntry { std::string name, sha1, file, format, saved, edition; long ms = 0; };
std::vector<UserEntry> readIndex(const std::string &tsv);
std::string writeIndex(const std::vector<UserEntry> &entries);
// a name for a new recording that does not collide: the name if free (or the same sha1), else name_2, name_3 ...
std::string freeName(const std::vector<UserEntry> &idx, const std::string &name, const std::string &sha1);

// ---- recall (RECORDING.md 3.3): where a u_ name of a loaded state comes from
enum class Resolve { Folder, Version, Embedded, Missing };
// inFolder: the folder's current file for that name has this sha1; inVersions: .versions/<sha1>.wav exists;
// embedded: the state carries the bytes
Resolve resolveUser(bool inFolder, bool inVersions, bool embedded);

// ---- state lines (RECORDING.md 4.2): user <name> <sha1> <bytes> [<base64 of the zlib-deflated WAV>]
std::string userLine(const std::string &name, const std::vector<uint8_t> &wav, bool embed);
bool parseUserLine(const std::string &value, std::string &name, std::string &sha1, size_t &bytes, std::vector<uint8_t> *wav);

}  // namespace bsynth
