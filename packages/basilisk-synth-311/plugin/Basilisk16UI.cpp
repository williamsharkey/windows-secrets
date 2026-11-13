/*
 * BASILISK 16 - the editor: Windows for Workgroups 3.11's screen, nothing else. The pointer and the keys go to
 * Windows (the guest program moves Windows' pointer to where yours is; the buttons are the emulated mouse's).
 */
#include "DistrhoUI.hpp"
#include "Shared.hpp"
#include "OpenGL.hpp"
#include <cstring>
#include <cstdio>
#include <cstdlib>

#ifndef GL_BGRA
#define GL_BGRA 0x80E1
#endif
#ifndef GL_CLAMP_TO_EDGE
#define GL_CLAMP_TO_EDGE 0x812F
#endif

START_NAMESPACE_DISTRHO

Basilisk16Shared *basilisk16Shared(void *plugin);

/* RETRO keycodes (libretro.h) for the keys Windows 3.11 cares about */
enum { RK_BACKSPACE = 8, RK_TAB = 9, RK_RETURN = 13, RK_ESCAPE = 27, RK_DELETE = 127, RK_UP = 273, RK_DOWN = 274,
       RK_RIGHT = 275, RK_LEFT = 276, RK_INSERT = 277, RK_HOME = 278, RK_END = 279, RK_PAGEUP = 280, RK_PAGEDOWN = 281,
       RK_F1 = 282, RK_RSHIFT = 303, RK_LSHIFT = 304, RK_RCTRL = 305, RK_LCTRL = 306, RK_RALT = 307, RK_LALT = 308 };

class Basilisk16UI : public UI
{
    static constexpr int kTex = 1024;
public:
    Basilisk16UI()
        : UI(DISTRHO_UI_DEFAULT_WIDTH, DISTRHO_UI_DEFAULT_HEIGHT)
    {
        sh_ = basilisk16Shared(getPluginInstancePointer());
        if (sh_ && sh_->S) { sh_->editors++; sh_->S->vid_want = 1; }
        setGeometryConstraints(512, 384, true, false);
    }

    ~Basilisk16UI() override
    {
        if (sh_ && sh_->S && --sh_->editors <= 0) sh_->S->vid_want = 0;
        if (tex_) glDeleteTextures(1, &tex_);
    }

protected:
    void parameterChanged(uint32_t, float) override {}
    void programLoaded(uint32_t) override {}
    void stateChanged(const char *, const char *) override {}

    void uiIdle() override
    {
        idles_++;
        if (const char *lg = std::getenv("BASILISK16_UILOG")) {
            if (idles_ % 60 == 1) if (FILE *f = std::fopen(lg, "a")) {
                std::fprintf(f, "idle %u draws %u sh %p S %p vid %ux%u seq %u want %u state %u\n", idles_, draws_, (void *)sh_,
                             sh_ ? (void *)sh_->S : nullptr, sh_ && sh_->S ? sh_->S->vid_w : 0, sh_ && sh_->S ? sh_->S->vid_h : 0,
                             sh_ && sh_->S ? sh_->S->vid_seq : 0, sh_ && sh_->S ? sh_->S->vid_want : 0, sh_ && sh_->S ? sh_->S->state : 0);
                std::fclose(f);
            }
        }
        if (!sh_ || !sh_->S) return;
        if (sh_->S->vid_seq != seenSeq_) repaint();
    }

    void onDisplay() override
    {
        const GraphicsContext &ctx(getGraphicsContext());
        (void)ctx;
        bshm *S = sh_ ? sh_->S : nullptr;
        const uint W = getWidth(), H = getHeight();
        draws_++;
        glClearColor(0.f, 0.f, 0.f, 1.f);
        glClear(GL_COLOR_BUFFER_BIT);
        if (!S || !S->vid_w) return;
        if (!tex_) {
            glGenTextures(1, &tex_);
            glBindTexture(GL_TEXTURE_2D, tex_);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, kTex, kTex, 0, GL_BGRA, GL_UNSIGNED_BYTE, nullptr);   // power of two: any OpenGL
        }
        glBindTexture(GL_TEXTURE_2D, tex_);
        // copy a consistent frame (the engine writes with a sequence lock)
        for (int tries = 0; tries < 3; tries++) {
            const uint32_t s = S->vid_seq;
            if (s & 1) continue;
            fw_ = S->vid_w; fh_ = S->vid_h;
            std::memcpy(frame_, S->vid, (size_t)fw_ * fh_ * 4);
            __sync_synchronize();
            if (S->vid_seq == s) { seenSeq_ = s; break; }
        }
        glPixelStorei(GL_UNPACK_ALIGNMENT, 4);
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, fw_, fh_, GL_BGRA, GL_UNSIGNED_BYTE, frame_);
        // fit the screen into the editor, keeping its shape
        const double sx = (double)W / fw_, sy = (double)H / fh_, s = sx < sy ? sx : sy;
        dw_ = fw_ * s; dh_ = fh_ * s; ox_ = (W - dw_) / 2; oy_ = (H - dh_) / 2;
        const float u = (float)fw_ / kTex, v = (float)fh_ / kTex;
        glDisable(GL_BLEND);        // the frame is XRGB: its alpha byte is 0, so it must not blend
        glEnable(GL_TEXTURE_2D);
        glColor4f(1.f, 1.f, 1.f, 1.f);
        glBegin(GL_QUADS);
        glTexCoord2f(0.f, 0.f); glVertex2d(ox_, oy_);
        glTexCoord2f(u, 0.f); glVertex2d(ox_ + dw_, oy_);
        glTexCoord2f(u, v); glVertex2d(ox_ + dw_, oy_ + dh_);
        glTexCoord2f(0.f, v); glVertex2d(ox_, oy_ + dh_);
        glEnd();
        glDisable(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, 0);
        glEnable(GL_BLEND);
    }

    bool onMouse(const MouseEvent &ev) override
    {
        if (!sh_ || !sh_->S) return false;
        movePointer(ev.pos.getX(), ev.pos.getY());
        const uint bit = ev.button == 1 ? 1 : ev.button == 3 ? 2 : 0;
        if (!bit) return false;
        if (ev.press) btn_ |= bit; else btn_ &= ~bit;
        sh_->S->mouse_btn = btn_;
        sh_->S->mouse_seq++;
        return true;
    }

    bool onMotion(const MotionEvent &ev) override
    {
        if (!sh_ || !sh_->S) return false;
        movePointer(ev.pos.getX(), ev.pos.getY());
        return true;
    }

    bool onKeyboard(const KeyboardEvent &ev) override
    {
        if (!sh_ || !sh_->S) return false;
        uint k = ev.key, rk = 0;
        if (k >= 'A' && k <= 'Z') k += 32;
        {   // a shifted character arrives as itself; Windows 3.11 gets the key under it (the Shift key is already down)
            static const char shifted[] = "~!@#$%^&*()_+{}|:\"<>?", base[] = "`1234567890-=[]\\;',./";
            for (int i = 0; shifted[i]; i++) if (k == (uint)(unsigned char)shifted[i]) { k = (uint)(unsigned char)base[i]; break; }
        }
        if (k >= 32 && k < 127) rk = k;
        else switch (k) {
            case kKeyBackspace: rk = RK_BACKSPACE; break; case kKeyTab: rk = RK_TAB; break;
            case kKeyEnter: rk = RK_RETURN; break; case kKeyEscape: rk = RK_ESCAPE; break; case kKeyDelete: rk = RK_DELETE; break;
            case kKeyUp: rk = RK_UP; break; case kKeyDown: rk = RK_DOWN; break; case kKeyLeft: rk = RK_LEFT; break;
            case kKeyRight: rk = RK_RIGHT; break; case kKeyHome: rk = RK_HOME; break; case kKeyEnd: rk = RK_END; break;
            case kKeyPageUp: rk = RK_PAGEUP; break; case kKeyPageDown: rk = RK_PAGEDOWN; break; case kKeyInsert: rk = RK_INSERT; break;
            case kKeyShiftL: rk = RK_LSHIFT; break; case kKeyShiftR: rk = RK_RSHIFT; break;
            case kKeyControlL: rk = RK_LCTRL; break; case kKeyControlR: rk = RK_RCTRL; break;
            case kKeyAltL: rk = RK_LALT; break; case kKeyAltR: rk = RK_RALT; break;
            default: if (k >= kKeyF1 && k <= kKeyF12) rk = RK_F1 + (k - kKeyF1); break;
        }
        if (!rk) return false;
        bshm *S = sh_->S;
        if (S->key_w - S->key_r >= BSHM_KEYS) return true;
        S->keys[S->key_w % BSHM_KEYS] = (ev.press ? 0x80000000u : 0u) | rk;
        __sync_synchronize();
        S->key_w++;
        return true;
    }

private:
    Basilisk16Shared *sh_ = nullptr;
    GLuint tex_ = 0;
    uint32_t seenSeq_ = 0xFFFFFFFF;
    uint fw_ = 0, fh_ = 0;
    double ox_ = 0, oy_ = 0, dw_ = 1, dh_ = 1;
    uint btn_ = 0;
    uint idles_ = 0, draws_ = 0;
    uint32_t frame_[BSHM_W * BSHM_H];

    void movePointer(double x, double y)
    {
        if (!fw_ || dw_ <= 0) return;
        int gx = (int)((x - ox_) * fw_ / dw_), gy = (int)((y - oy_) * fh_ / dh_);
        if (gx < 0) gx = 0; if (gy < 0) gy = 0;
        if (gx >= (int)fw_) gx = fw_ - 1; if (gy >= (int)fh_) gy = fh_ - 1;
        bshm *S = sh_->S;
        if (gx == S->mouse_x && gy == S->mouse_y) return;
        S->mouse_x = gx; S->mouse_y = gy;
        S->mouse_seq++;
    }

    DISTRHO_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(Basilisk16UI)
};

UI *createUI() { return new Basilisk16UI(); }

END_NAMESPACE_DISTRHO
