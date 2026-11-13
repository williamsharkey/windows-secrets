// BasiliskHost - a minimal JSON value for the reports
#pragma once
#include <cmath>
#include <cstdio>
#include <map>
#include <memory>
#include <string>
#include <utility>
#include <vector>

class J {
public:
    enum T { Null, Bool, Num, Str, Arr, Obj } t = Null;
    J() {}
    J(bool b) : t(Bool), b_(b) {}
    J(int v) : t(Num), n_(v) {}
    J(unsigned v) : t(Num), n_(v) {}
    J(long v) : t(Num), n_((double)v) {}
    J(long long v) : t(Num), n_((double)v) {}
    J(unsigned long long v) : t(Num), n_((double)v) {}
    J(double v) : t(Num), n_(v) {}
    J(const char *s) : t(Str), s_(s) {}
    J(const std::string &s) : t(Str), s_(s) {}
    static J arr() { J j; j.t = Arr; return j; }
    static J obj() { J j; j.t = Obj; return j; }
    J &operator[](const std::string &k)
    {
        if (t != Obj) t = Obj;
        for (auto &kv : o_) if (kv.first == k) return kv.second;
        o_.push_back({k, J()});
        return o_.back().second;
    }
    void push(const J &v) { if (t != Arr) t = Arr; a_.push_back(v); }
    size_t size() const { return t == Arr ? a_.size() : o_.size(); }
    std::string dump(int ind = 0) const
    {
        std::string pad(ind + 2, ' '), pad0(ind, ' ');
        char b[64];
        switch (t) {
        case Null: return "null";
        case Bool: return b_ ? "true" : "false";
        case Num:
            if (!std::isfinite(n_)) return "null";
            if (n_ == std::floor(n_) && std::fabs(n_) < 1e15) snprintf(b, sizeof b, "%.0f", n_);
            else snprintf(b, sizeof b, "%.6g", n_);
            return b;
        case Str: return quote(s_);
        case Arr: {
            if (a_.empty()) return "[]";
            bool flat = true;
            for (auto &x : a_) if (x.t == Arr || x.t == Obj) flat = false;
            std::string r = "[";
            for (size_t i = 0; i < a_.size(); i++) {
                r += flat ? (i ? ", " : "") : (i ? ",\n" + pad : "\n" + pad);
                r += a_[i].dump(ind + 2);
            }
            return r + (flat ? "]" : "\n" + pad0 + "]");
        }
        case Obj: {
            if (o_.empty()) return "{}";
            std::string r = "{";
            for (size_t i = 0; i < o_.size(); i++) r += (i ? ",\n" : "\n") + pad + quote(o_[i].first) + ": " + o_[i].second.dump(ind + 2);
            return r + "\n" + pad0 + "}";
        }
        }
        return "null";
    }
    static std::string quote(const std::string &s)
    {
        std::string r = "\"";
        for (unsigned char c : s) {
            if (c == '"' || c == '\\') { r += '\\'; r += (char)c; }
            else if (c == '\n') r += "\\n";
            else if (c < 0x20) { char b[8]; snprintf(b, sizeof b, "\\u%04x", c); r += b; }
            else r += (char)c;
        }
        return r + "\"";
    }
private:
    bool b_ = false;
    double n_ = 0;
    std::string s_;
    std::vector<J> a_;
    std::vector<std::pair<std::string, J>> o_;
};

inline double r3(double v) { return std::round(v * 1000) / 1000; }
inline double r1(double v) { return std::round(v * 10) / 10; }
