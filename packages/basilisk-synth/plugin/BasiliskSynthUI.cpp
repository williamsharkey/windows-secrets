// BASILISK SYNTH - the editor: Windows XP's screen, and the visitor's mouse and keys into it.
// There is nothing else on it: the instrument's whole interface is the one inside XP.
#include "DistrhoUI.hpp"
#include "BasiliskSynthShared.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

START_NAMESPACE_DISTRHO

using bsynth::Machine;

class BasiliskSynthUI : public UI
{
public:
    BasiliskSynthUI()
        : UI(Machine::kW, Machine::kH)
    {
        host_ = synthHostOf(getPluginInstancePointer());
        loadSharedResources();
        // XP's screen is drawn sharp: each XP pixel is an exact k x k block of device pixels (k = 1, 2, 3...), never
        // resampled. The window opens at the integer scale nearest the system's (150 % -> 1x, 175-200 % -> 2x,
        // Retina -> 2x) and never goes below 1x.
        const double s = getScaleFactor();
        const uint k = std::max(1, (int)std::floor(s + 0.25));
        setGeometryConstraints(Machine::kW, Machine::kH, true);
        if (k != 1) setSize(Machine::kW * k, Machine::kH * k);
        if (host_) host_->uiOpened();
        opened_ = Machine::now();
    }
    ~BasiliskSynthUI() override { if (host_) host_->uiClosed(); }

protected:
    void parameterChanged(uint32_t, float) override {}
    void stateChanged(const char *, const char *) override {}

    void uiIdle() override
    {
        if (!host_) return;
        Machine &m = host_->machine();
        m.touch();              // XP stays awake while its screen is showing
        std::string e;
        // an edit made in Windows is already in 1.2.1's names: the state says so ("ver"), so it is not migrated
        if (host_->takeEdit(e)) setState("dna", ("BASILISK-SYNTH 1\ndna " + e + "\nreference 0\nver 1.2.1\n").c_str());
        int x0, y0, x1, y1;
        if (m.phase == Machine::Running && m.frame(rgba_, x0, y0, x1, y1)) {
            fresh_ = true;      // uploaded in onNanoDisplay, where the GL context is current
            shown_ = true;
            repaint();
        } else if (!shown_) repaint();   // the waking card animates
    }

    void onNanoDisplay() override
    {
        const float W = getWidth(), H = getHeight();
        if (fresh_ && !rgba_.empty()) {
            // NVG_IMAGE_NEAREST (1 << 5): nearest-neighbour, never smoothed
            if (!img_.isValid()) img_ = createImageFromRGBA(Machine::kW, Machine::kH, rgba_.data(), (ImageFlags)(1 << 5));
            else img_.update(rgba_.data());
            fresh_ = false;
        }
        if (shown_ && img_.isValid()) {
            // the largest whole scale that fits, centred; a host's in-between size gets XP's panel colour around it
            int k, ox, oy;
            layout(k, ox, oy);
            if (ox > 0 || oy > 0) {
                beginPath();
                rect(0, 0, W, H);
                fillColor(236, 233, 216);
                fill();
            }
            beginPath();
            rect(ox, oy, Machine::kW * k, Machine::kH * k);
            fillPaint(imagePattern(ox, oy, Machine::kW * k, Machine::kH * k, 0, img_, 1.f));
            fill();
            return;
        }
        // until XP is up: a plain card in XP's own colours, saying what is happening
        beginPath();
        rect(0, 0, W, H);
        fillColor(0, 84, 227);
        fill();
        const float s = W / Machine::kW;
        Machine *m = host_ ? &host_->machine() : nullptr;
        std::string title = "BASILISK SYNTH", line = "Waking Windows XP...", err;
        float prog = -1;
        if (m) {
            int ph = m->phase;
            std::string st = m->status();
            if (!st.empty()) line = st;
            if (ph == Machine::Fetching || ph == Machine::Unpacking) prog = m->progress;
            if (ph == Machine::Failed) { line = "Windows XP could not start."; err = m->error(); }
            if (ph == Machine::Running) line = "Windows XP is up. Sixteen Sound Recorders are coming together...";
        }
        fontSize(44 * s);
        fillColor(255, 255, 255);
        textAlign(ALIGN_CENTER | ALIGN_MIDDLE);
        text(W / 2, H * 0.42f, title.c_str(), nullptr);
        fontSize(18 * s);
        fillColor(220, 232, 255);
        text(W / 2, H * 0.52f, line.c_str(), nullptr);
        if (!err.empty()) {
            fontSize(14 * s);
            textBox(W * 0.15f, H * 0.58f, W * 0.7f, err.c_str(), nullptr);
        }
        // XP's boot bar: three blue blocks sliding, or a real progress bar while fetching
        const float bw = 160 * s, bh = 14 * s, bx = W / 2 - bw / 2, by = H * 0.62f;
        beginPath();
        roundedRect(bx, by, bw, bh, 3 * s);
        strokeColor(255, 255, 255);
        strokeWidth(1.5f * s);
        stroke();
        if (prog >= 0) {
            beginPath();
            rect(bx + 2 * s, by + 2 * s, (bw - 4 * s) * (prog > 1 ? 1 : prog), bh - 4 * s);
            fillColor(255, 255, 255);
            fill();
            char pc[32];
            snprintf(pc, sizeof pc, "%d%%", (int)(prog * 100));
            fontSize(13 * s);
            text(W / 2, by + bh + 16 * s, pc, nullptr);
        } else if (err.empty()) {
            const float t = (float)(Machine::now() - opened_);
            for (int i = 0; i < 3; i++) {
                float x = std::fmod(t * 90 * s + i * 11 * s, bw + 30 * s) - 30 * s;
                if (x < 0 || x > bw - 12 * s) continue;
                beginPath();
                rect(bx + x, by + 3 * s, 9 * s, bh - 6 * s);
                fillColor(255, 255, 255);
                fill();
            }
        }
    }

    // ------------------------------------------------------------------ mouse and keys go to XP
    void layout(int &k, int &ox, int &oy) const
    {
        k = std::max(1, (int)std::min(getWidth() / Machine::kW, getHeight() / Machine::kH));
        ox = std::max(0, ((int)getWidth() - Machine::kW * k) / 2);
        oy = std::max(0, ((int)getHeight() - Machine::kH * k) / 2);
    }
    bool toXP(double x, double y, int &vx, int &vy) const
    {
        int k, ox, oy;
        layout(k, ox, oy);
        vx = (int)std::floor((x - ox) / k);
        vy = (int)std::floor((y - oy) / k);
        vx = vx < 0 ? 0 : vx >= Machine::kW ? Machine::kW - 1 : vx;
        vy = vy < 0 ? 0 : vy >= Machine::kH ? Machine::kH - 1 : vy;
        return shown_;
    }
    bool onMouse(const MouseEvent &ev) override
    {
        int x, y;
        if (!host_ || !toXP(ev.pos.getX(), ev.pos.getY(), x, y)) return false;
        int bit = ev.button == 1 ? 1 : ev.button == 2 ? 2 : ev.button == 3 ? 4 : 0;   // VNC: left, middle, right
        if (ev.press) buttons_ |= bit; else buttons_ &= ~bit;
        host_->machine().pointer(x, y, buttons_);
        return true;
    }
    bool onMotion(const MotionEvent &ev) override
    {
        int x, y;
        if (!host_ || !toXP(ev.pos.getX(), ev.pos.getY(), x, y)) return false;
        host_->machine().pointer(x, y, buttons_);
        return true;
    }
    bool onScroll(const ScrollEvent &ev) override
    {
        int x, y;
        if (!host_ || !toXP(ev.pos.getX(), ev.pos.getY(), x, y)) return false;
        int b = ev.delta.getY() > 0 ? 8 : 16;
        host_->machine().pointer(x, y, buttons_ | b);
        host_->machine().pointer(x, y, buttons_);
        return true;
    }
    bool onKeyboard(const KeyboardEvent &ev) override
    {
        if (!host_ || !shown_) return false;
        uint32_t k = keysym(ev.key);
        if (!k) return false;
        host_->machine().key(k, ev.press);
        return true;
    }

private:
    static uint32_t keysym(uint32_t key)
    {
        switch (key) {
        case kKeyBackspace: return 0xff08;
        case kKeyTab: return 0xff09;
        case kKeyEnter: return 0xff0d;
        case kKeyEscape: return 0xff1b;
        case kKeyDelete: return 0xffff;
        case kKeyHome: return 0xff50;
        case kKeyLeft: return 0xff51;
        case kKeyUp: return 0xff52;
        case kKeyRight: return 0xff53;
        case kKeyDown: return 0xff54;
        case kKeyPageUp: return 0xff55;
        case kKeyPageDown: return 0xff56;
        case kKeyEnd: return 0xff57;
        case kKeyInsert: return 0xff63;
        case kKeyShiftL: return 0xffe1;
        case kKeyShiftR: return 0xffe2;
        case kKeyControlL: return 0xffe3;
        case kKeyControlR: return 0xffe4;
        case kKeyAltL: return 0xffe9;
        case kKeyAltR: return 0xffea;
        case kKeyCapsLock: return 0xffe5;
        case kKeyPadEnter: return 0xff8d;
        default: break;
        }
        if (key >= kKeyF1 && key <= kKeyF12) return 0xffbe + (key - kKeyF1);
        if (key >= 0x20 && key < 0x7f) return key;
        if (key >= 0xa0 && key <= 0xff) return key;
        return 0;
    }

    SynthHost *host_ = nullptr;
    NanoImage img_;
    std::vector<uint8_t> rgba_;
    bool shown_ = false, fresh_ = false;
    int buttons_ = 0;
    double opened_ = 0;

    DISTRHO_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(BasiliskSynthUI)
};

UI *createUI() { return new BasiliskSynthUI(); }

END_NAMESPACE_DISTRHO
