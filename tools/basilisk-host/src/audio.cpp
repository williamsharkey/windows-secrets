// BasiliskHost - WASAPI (see audio.h)
#include "audio.h"
#include "host.h"
#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <functiondiscoverykeys_devpkey.h>
#include <avrt.h>
#include <mmsystem.h>
#include <endpointvolume.h>
#include <ksmedia.h>
#include <chrono>
#include <cstring>

// KSDATAFORMAT_SUBTYPE_IEEE_FLOAT
// PKEY_Device_FriendlyName
static const PROPERTYKEY kFriendlyName = {{0xa45c254e, 0xdf1c, 0x4efd, {0x80, 0x20, 0x67, 0xd1, 0x46, 0xa8, 0x50, 0xe0}}, 14};
static const GUID kSubtypeFloat = {0x00000003, 0x0000, 0x0010, {0x80, 0x00, 0x00, 0xaa, 0x00, 0x38, 0x9b, 0x71}};

template <class T> static void rel(T *&p) { if (p) { p->Release(); p = nullptr; } }

std::vector<AudioDevice> audio_devices()
{
    std::vector<AudioDevice> v;
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    IMMDeviceEnumerator *en = nullptr;
    if (FAILED(CoCreateInstance(__uuidof(MMDeviceEnumerator), NULL, CLSCTX_ALL, __uuidof(IMMDeviceEnumerator), (void **)&en))) return v;
    std::wstring defId;
    IMMDevice *def = nullptr;
    if (SUCCEEDED(en->GetDefaultAudioEndpoint(eRender, eMultimedia, &def))) {
        LPWSTR id = nullptr;
        def->GetId(&id);
        if (id) { defId = id; CoTaskMemFree(id); }
        rel(def);
    }
    IMMDeviceCollection *col = nullptr;
    if (SUCCEEDED(en->EnumAudioEndpoints(eRender, DEVICE_STATE_ACTIVE, &col))) {
        UINT n = 0;
        col->GetCount(&n);
        for (UINT i = 0; i < n; i++) {
            IMMDevice *d = nullptr;
            if (FAILED(col->Item(i, &d))) continue;
            AudioDevice ad;
            LPWSTR id = nullptr;
            d->GetId(&id);
            if (id) { ad.id = id; CoTaskMemFree(id); }
            IPropertyStore *ps = nullptr;
            if (SUCCEEDED(d->OpenPropertyStore(STGM_READ, &ps))) {
                PROPVARIANT pv;
                PropVariantInit(&pv);
                if (SUCCEEDED(ps->GetValue(kFriendlyName, &pv)) && pv.vt == VT_LPWSTR) ad.name = narrow(pv.pwszVal);
                PropVariantClear(&pv);
                rel(ps);
            }
            ad.isDefault = ad.id == defId;
            v.push_back(ad);
            rel(d);
        }
        rel(col);
    }
    rel(en);
    return v;
}

static IMMDevice *open_device(IMMDeviceEnumerator *en, const std::wstring &id)
{
    IMMDevice *d = nullptr;
    if (!id.empty() && SUCCEEDED(en->GetDevice(id.c_str(), &d))) return d;
    if (SUCCEEDED(en->GetDefaultAudioEndpoint(eRender, eMultimedia, &d))) return d;
    return nullptr;
}

bool endpoint_volume(const std::wstring &id, float &vol, bool &muted)
{
    IMMDeviceEnumerator *en = nullptr;
    if (FAILED(CoCreateInstance(__uuidof(MMDeviceEnumerator), NULL, CLSCTX_ALL, __uuidof(IMMDeviceEnumerator), (void **)&en))) return false;
    IMMDevice *d = open_device(en, id);
    IAudioEndpointVolume *ev = nullptr;
    bool ok = false;
    if (d && SUCCEEDED(d->Activate(__uuidof(IAudioEndpointVolume), CLSCTX_ALL, NULL, (void **)&ev))) {
        BOOL m = FALSE;
        ok = SUCCEEDED(ev->GetMasterVolumeLevelScalar(&vol)) && SUCCEEDED(ev->GetMute(&m));
        muted = m != FALSE;
    }
    rel(ev);
    rel(d);
    rel(en);
    return ok;
}

bool AudioOut::start(const std::wstring &id, int sr, int blk, RenderFn fn, std::string &err)
{
    stop();
    fn_ = std::move(fn);
    run_ = true;
    ready_ = false;
    failed_ = false;
    underruns = 0;
    framesOut = 0;
    th_ = std::thread(&AudioOut::thread, this, id, sr, blk);
    while (!ready_ && !failed_) std::this_thread::sleep_for(std::chrono::milliseconds(5));
    if (failed_) {
        err = err_;
        if (th_.joinable()) th_.join();
        run_ = false;
        return false;
    }
    return true;
}

void AudioOut::stop()
{
    run_ = false;
    if (th_.joinable()) th_.join();
}

// the "dummy" device: no hardware, one block per block-length of wall clock (as REAPER's Dummy Audio)
static bool dummy_id(const std::wstring &id) { return id == L"dummy"; }

void AudioOut::thread(std::wstring id, int sr, int blk)
{
    if (dummy_id(id)) {
        deviceName = "Dummy (no device)";
        sampleRate = sr;
        block = blk;
        bufferFrames = blk;
        periodMs = blk * 1000.0 / sr;
        std::vector<float> L(blk), R(blk);
        timeBeginPeriod(1);
        ready_ = true;
        double start = now_s(), busy = 0, t0 = start;
        uint64_t n = 0;
        while (run_) {
            double a = now_s();
            fn_(L.data(), R.data(), blk);
            busy += now_s() - a;
            n += blk;
            framesOut += blk;
            double due = start + (double)n / sr, now = now_s();
            if (due > now) Sleep((DWORD)((due - now) * 1000));
            else if (now - due > 0.05) { underruns++; start = now - (double)n / sr; }   // late: count once, then carry on from now
            if (now_s() - t0 > 0.5) { load = busy / (now_s() - t0); busy = 0; t0 = now_s(); }
        }
        timeEndPeriod(1);
        return;
    }

    CoInitializeEx(NULL, COINIT_MULTITHREADED);
    IMMDeviceEnumerator *en = nullptr;
    IMMDevice *dev = nullptr;
    IAudioClient *ac = nullptr;
    IAudioRenderClient *rc = nullptr;
    HANDLE ev = CreateEventW(NULL, FALSE, FALSE, NULL), task = NULL;
    DWORD taskIdx = 0;
    auto fail = [&](const char *what, HRESULT hr) {
        char b[160];
        snprintf(b, sizeof b, "%s failed (hr 0x%08lx)", what, (unsigned long)hr);
        err_ = b;
        failed_ = true;
    };
    HRESULT hr = CoCreateInstance(__uuidof(MMDeviceEnumerator), NULL, CLSCTX_ALL, __uuidof(IMMDeviceEnumerator), (void **)&en);
    if (FAILED(hr)) { fail("MMDeviceEnumerator", hr); goto done; }
    dev = open_device(en, id);
    if (!dev) { fail("open device", E_FAIL); goto done; }
    {
        IPropertyStore *ps = nullptr;
        if (SUCCEEDED(dev->OpenPropertyStore(STGM_READ, &ps))) {
            PROPVARIANT pv;
            PropVariantInit(&pv);
            if (SUCCEEDED(ps->GetValue(kFriendlyName, &pv)) && pv.vt == VT_LPWSTR) deviceName = narrow(pv.pwszVal);
            PropVariantClear(&pv);
            rel(ps);
        }
    }
    hr = dev->Activate(__uuidof(IAudioClient), CLSCTX_ALL, NULL, (void **)&ac);
    if (FAILED(hr)) { fail("IAudioClient", hr); goto done; }
    {
        // float32 stereo at the chosen rate; Windows converts to the device's own format and rate
        WAVEFORMATEXTENSIBLE wf = {};
        wf.Format.wFormatTag = WAVE_FORMAT_EXTENSIBLE;
        wf.Format.nChannels = 2;
        wf.Format.nSamplesPerSec = sr;
        wf.Format.wBitsPerSample = 32;
        wf.Format.nBlockAlign = 8;
        wf.Format.nAvgBytesPerSec = sr * 8;
        wf.Format.cbSize = 22;
        wf.Samples.wValidBitsPerSample = 32;
        wf.dwChannelMask = SPEAKER_FRONT_LEFT | SPEAKER_FRONT_RIGHT;
        wf.SubFormat = kSubtypeFloat;
        {
            WAVEFORMATEX *mix = nullptr;
            if (SUCCEEDED(ac->GetMixFormat(&mix)) && mix) {
                mixRate = (int)mix->nSamplesPerSec;
                mixChannels = mix->nChannels;
                mixBits = mix->wBitsPerSample;
                CoTaskMemFree(mix);
            }
        }
        REFERENCE_TIME defP = 0, minP = 0;
        ac->GetDevicePeriod(&defP, &minP);
        periodMs = defP / 10000.0;
        // the WASAPI buffer holds two host blocks (at least two device periods)
        REFERENCE_TIME dur = (REFERENCE_TIME)(2.0 * blk * 1e7 / sr);
        if (dur < 2 * defP) dur = 2 * defP;
        hr = ac->Initialize(AUDCLNT_SHAREMODE_SHARED,
                            AUDCLNT_STREAMFLAGS_EVENTCALLBACK | AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM | AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY,
                            dur, 0, (WAVEFORMATEX *)&wf, NULL);
        if (FAILED(hr)) { fail("IAudioClient::Initialize", hr); goto done; }
        UINT32 bf = 0;
        ac->GetBufferSize(&bf);
        bufferFrames = (int)bf;
        REFERENCE_TIME sl = 0;
        ac->GetStreamLatency(&sl);
        streamLatencyMs = sl / 10000.0;
        ac->SetEventHandle(ev);
        hr = ac->GetService(__uuidof(IAudioRenderClient), (void **)&rc);
        if (FAILED(hr)) { fail("IAudioRenderClient", hr); goto done; }
    }
    sampleRate = sr;
    block = blk;
    task = AvSetMmThreadCharacteristicsW(L"Pro Audio", &taskIdx);
    {
        std::vector<float> L(blk), R(blk), fifo;   // fifo: interleaved frames rendered but not yet given to the device
        size_t fpos = 0;
        BYTE *buf = nullptr;
        // prefill with silence, then start
        if (SUCCEEDED(rc->GetBuffer(bufferFrames, &buf))) rc->ReleaseBuffer(bufferFrames, AUDCLNT_BUFFERFLAGS_SILENT);
        ac->Start();
        ready_ = true;
        double busy = 0, t0 = now_s();
        while (run_) {
            if (WaitForSingleObject(ev, 200) != WAIT_OBJECT_0) { underruns++; continue; }
            UINT32 pad = 0;
            if (FAILED(ac->GetCurrentPadding(&pad))) break;
            int avail = bufferFrames - (int)pad;
            if (pad == 0 && framesOut > 0) underruns++;
            if (avail <= 0) continue;
            if (FAILED(rc->GetBuffer(avail, &buf))) continue;
            float *o = (float *)buf;
            for (int i = 0; i < avail; i++) {
                if (fpos * 2 >= fifo.size()) {
                    double a = now_s();
                    fn_(L.data(), R.data(), blk);
                    busy += now_s() - a;
                    fifo.resize(blk * 2);
                    for (int k = 0; k < blk; k++) { fifo[2 * k] = L[k]; fifo[2 * k + 1] = R[k]; }
                    fpos = 0;
                }
                o[2 * i] = fifo[2 * fpos] * gain;
                o[2 * i + 1] = fifo[2 * fpos + 1] * gain;
                fpos++;
            }
            rc->ReleaseBuffer(avail, 0);
            framesOut += avail;
            double el = now_s() - t0;
            if (el > 0.5) { load = busy / el; busy = 0; t0 = now_s(); }
        }
        ac->Stop();
    }
done:
    if (task) AvRevertMmThreadCharacteristics(task);
    rel(rc);
    rel(ac);
    rel(dev);
    rel(en);
    CloseHandle(ev);
    CoUninitialize();
    if (!ready_) failed_ = true;
}

// ------------------------------------------------------------------ loopback
bool Loopback::start(const std::wstring &id, std::string &err)
{
    std::atomic<int> state{0};
    run_ = true;
    data_.clear();
    th_ = std::thread([this, id, &state, &err]() {
        CoInitializeEx(NULL, COINIT_MULTITHREADED);
        IMMDeviceEnumerator *en = nullptr;
        IMMDevice *dev = nullptr;
        IAudioClient *ac = nullptr;
        IAudioCaptureClient *cc = nullptr;
        WAVEFORMATEX *mix = nullptr;
        bool isFloat = false;
        int ch = 2;
        HRESULT hr = CoCreateInstance(__uuidof(MMDeviceEnumerator), NULL, CLSCTX_ALL, __uuidof(IMMDeviceEnumerator), (void **)&en);
        if (SUCCEEDED(hr)) dev = open_device(en, id);
        if (dev) hr = dev->Activate(__uuidof(IAudioClient), CLSCTX_ALL, NULL, (void **)&ac);
        if (ac) hr = ac->GetMixFormat(&mix);
        if (mix) {
            ch = mix->nChannels;
            sampleRate = mix->nSamplesPerSec;
            isFloat = mix->wFormatTag == WAVE_FORMAT_IEEE_FLOAT ||
                      (mix->wFormatTag == WAVE_FORMAT_EXTENSIBLE && ((WAVEFORMATEXTENSIBLE *)mix)->SubFormat == kSubtypeFloat);
            hr = ac->Initialize(AUDCLNT_SHAREMODE_SHARED, AUDCLNT_STREAMFLAGS_LOOPBACK, 2000000, 0, mix, NULL);
            if (SUCCEEDED(hr)) hr = ac->GetService(__uuidof(IAudioCaptureClient), (void **)&cc);
        }
        if (!cc || FAILED(hr)) {
            char b[96];
            snprintf(b, sizeof b, "loopback capture failed (hr 0x%08lx)", (unsigned long)hr);
            err = b;
            state = 2;
        } else {
            ac->Start();
            state = 1;
            while (run_) {
                Sleep(10);
                UINT32 pk = 0;
                while (SUCCEEDED(cc->GetNextPacketSize(&pk)) && pk > 0) {
                    BYTE *b;
                    UINT32 n;
                    DWORD fl;
                    if (FAILED(cc->GetBuffer(&b, &n, &fl, NULL, NULL))) break;
                    std::lock_guard<std::mutex> g(m_);
                    for (UINT32 i = 0; i < n; i++)
                        for (int c = 0; c < 2; c++) {
                            float v = 0;
                            int cc2 = c < ch ? c : 0;
                            if (fl & AUDCLNT_BUFFERFLAGS_SILENT) v = 0;
                            else if (isFloat) v = ((float *)b)[i * ch + cc2];
                            else if (mix->wBitsPerSample == 16) v = ((int16_t *)b)[i * ch + cc2] / 32768.f;
                            else if (mix->wBitsPerSample == 32) v = ((int32_t *)b)[i * ch + cc2] / 2147483648.f;
                            data_.push_back(v);
                        }
                    cc->ReleaseBuffer(n);
                }
            }
            ac->Stop();
        }
        if (mix) CoTaskMemFree(mix);
        rel(cc);
        rel(ac);
        rel(dev);
        rel(en);
        CoUninitialize();
    });
    while (state == 0) Sleep(5);
    if (state == 2) { run_ = false; th_.join(); return false; }
    return true;
}

std::vector<float> Loopback::stop()
{
    run_ = false;
    if (th_.joinable()) th_.join();
    std::lock_guard<std::mutex> g(m_);
    return data_;
}
