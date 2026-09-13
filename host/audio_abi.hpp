#pragma once
#include <windows.h>
#include <mmreg.h>
#include <audioapotypes.h>
#include <objbase.h>
#include <cstring>

struct UncompressedFormat {
    GUID type;
    DWORD channels, bytes_per_sample, valid_bits;
    FLOAT rate;
    DWORD channel_mask;
};
struct IAudioMediaType : IUnknown {
    virtual HRESULT STDMETHODCALLTYPE IsCompressedFormat(BOOL*)=0;
    virtual HRESULT STDMETHODCALLTYPE IsEqual(IAudioMediaType*,DWORD*)=0;
    virtual const WAVEFORMATEX* STDMETHODCALLTYPE GetAudioFormat()=0;
    virtual HRESULT STDMETHODCALLTYPE GetUncompressedAudioFormat(UncompressedFormat*)=0;
};
struct Connection {
    UINT32 type;
    UINT_PTR buffer;
    UINT32 max_frames;
    IAudioMediaType* format;
    UINT32 signature;
};
static_assert(sizeof(Connection)==40);
static_assert(sizeof(APO_CONNECTION_PROPERTY)==24);
struct ApoConfiguration : IUnknown {
    virtual HRESULT STDMETHODCALLTYPE LockForProcess(UINT32,Connection**,UINT32,Connection**)=0;
    virtual HRESULT STDMETHODCALLTYPE UnlockForProcess()=0;
};
struct ApoRealtime : IUnknown {
    virtual void STDMETHODCALLTYPE APOProcess(UINT32,APO_CONNECTION_PROPERTY**,UINT32,APO_CONNECTION_PROPERTY**)=0;
    virtual UINT32 STDMETHODCALLTYPE CalcInputFrames(UINT32)=0;
    virtual UINT32 STDMETHODCALLTYPE CalcOutputFrames(UINT32)=0;
};

class FloatMediaType final : public IAudioMediaType {
    LONG refs_=1;
    WAVEFORMATEXTENSIBLE wave_{};
    struct ApplicationFormat {
        WAVEFORMATEXTENSIBLE wave;
        GUID signature;
        DWORD pid;
        WCHAR path[250];
        DWORD type;
    } application_{};
    static_assert(sizeof(ApplicationFormat)==0x234);
    static_assert(offsetof(ApplicationFormat,signature)==0x28 && offsetof(ApplicationFormat,pid)==0x38);
    static_assert(offsetof(ApplicationFormat,path)==0x3c && offsetof(ApplicationFormat,type)==0x230);
    bool has_application_=false;
public:
    FloatMediaType(DWORD rate,WORD channels,DWORD mask) {
        wave_.Format.wFormatTag=WAVE_FORMAT_EXTENSIBLE;
        wave_.Format.nChannels=channels;
        wave_.Format.nSamplesPerSec=rate;
        wave_.Format.nAvgBytesPerSec=rate*channels*4;
        wave_.Format.nBlockAlign=channels*4;
        wave_.Format.wBitsPerSample=32;
        wave_.Format.cbSize=22;
        wave_.Samples.wValidBitsPerSample=32;
        wave_.dwChannelMask=mask;
        wave_.SubFormat={3,0,0x10,{0x80,0,0,0xaa,0,0x38,0x9b,0x71}};
    }
    bool set_application(const wchar_t* path,DWORD pid){
        if(!path || !*path || wcslen(path)>=250 || !pid)return false;
        application_.wave=wave_;
        application_.wave.Format.cbSize=0x222;
        application_.signature={0xcf49a841,0x9319,0x46ee,{0x88,0xa5,0x0b,0x6d,0x69,0xa4,0xa4,0x26}};
        application_.pid=pid;
        std::memcpy(application_.path,path,(wcslen(path)+1)*sizeof(WCHAR));
        application_.type=0; // Original normal-application category.
        has_application_=true;return true;
    }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID id,void** out) override {
        if (!out) return E_POINTER;
        *out=nullptr;
        const IID media={0x4e997f73,0xb71f,0x4798,{0x87,0x3b,0xed,0x7d,0xfc,0xf1,0x5b,0x4d}};
        if (id!=IID_IUnknown && id!=media) return E_NOINTERFACE;
        *out=static_cast<IAudioMediaType*>(this);AddRef();return S_OK;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return InterlockedIncrement(&refs_); }
    ULONG STDMETHODCALLTYPE Release() override { LONG n=InterlockedDecrement(&refs_); if (!n) delete this; return n; }
    HRESULT STDMETHODCALLTYPE IsCompressedFormat(BOOL* compressed) override {
        if (!compressed) return E_POINTER;
        *compressed=FALSE; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE IsEqual(IAudioMediaType* other,DWORD* flags) override {
        if (!other || !flags) return E_INVALIDARG;
        *flags=0;
        auto p=other->GetAudioFormat();
        auto own=GetAudioFormat();
        if (!p) return E_INVALIDARG;
        if (p->wFormatTag==own->wFormatTag) *flags|=2;
        if (!std::memcmp(p,own,sizeof(WAVEFORMATEX))) *flags|=4;
        if (p->cbSize==own->cbSize && !std::memcmp(reinterpret_cast<const BYTE*>(p)+sizeof(WAVEFORMATEX),reinterpret_cast<const BYTE*>(own)+sizeof(WAVEFORMATEX),own->cbSize)) *flags|=8;
        return *flags==14?S_OK:S_FALSE;
    }
    const WAVEFORMATEX* STDMETHODCALLTYPE GetAudioFormat() override { return has_application_?&application_.wave.Format:&wave_.Format; }
    HRESULT STDMETHODCALLTYPE GetUncompressedAudioFormat(UncompressedFormat* out) override {
        if (!out) return E_POINTER;
        *out={wave_.SubFormat,wave_.Format.nChannels,4,32,static_cast<float>(wave_.Format.nSamplesPerSec),wave_.dwChannelMask};
        return S_OK;
    }
};
