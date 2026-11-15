// renamed packs and presets: an old pack id, label or preset name, as it is now (old projects and songs keep loading)
#pragma once
#include <string>
#include "pack_aliases_gen.h"   // (tools/make_pack_aliases.py, from library/packs/<pack>/RENAMES.TSV)
namespace b16pack {
// renamed packs and presets (pack_aliases_gen.h): an old id or name as it is now
inline std::string packIdNow(const std::string &id)
{
    for (const auto &a : kPackIdAlias) if (id == a.oldId) return a.newId;
    return id;
}
inline std::string packIdsNow(const std::string &list)   // "a,b,c" (the state's `packs`)
{
    std::string out, cur;
    for (char c : list + ",") { if (c == ',') { if (!cur.empty()) out += (out.empty() ? "" : ",") + packIdNow(cur); cur.clear(); } else cur += c; }
    return out;
}
inline std::string presetNameNow(const std::string &pack, const std::string &name)   // "Name" or "Category/Name"
{
    const size_t sl = name.find('/');
    for (const auto &a : kPresetAlias) {
        if (pack != a.pack) continue;
        if (name == a.oldName) return a.newName;
        if (sl != std::string::npos && name.compare(0, sl, a.category) == 0 && name.compare(sl + 1, std::string::npos, a.oldName) == 0)
            return std::string(a.category) + "/" + a.newName;
    }
    return name;
}
}  // namespace b16pack
