#pragma once
#include <windows.h>
#include <oleauto.h>

struct ControlStore;
struct ExpertDevice : IDispatch {
    virtual HRESULT STDMETHODCALLTYPE GetId(GUID*)=0;
    virtual HRESULT STDMETHODCALLTYPE GetFormFactor(LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE GetHWID(BSTR*)=0;
    virtual HRESULT STDMETHODCALLTYPE GetName(BSTR*)=0;
    virtual HRESULT STDMETHODCALLTYPE OpenStore(ControlStore**)=0;
};

struct ExpertControl : IDispatch {
    virtual HRESULT STDMETHODCALLTYPE GetDeviceCount(LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE GetDevice(LONG,IDispatch**)=0;
    virtual HRESULT STDMETHODCALLTYPE AddDevice(BSTR,IDispatch**)=0;
    virtual HRESULT STDMETHODCALLTYPE RemoveDevice(IDispatch*)=0;
    virtual HRESULT STDMETHODCALLTYPE OpenDevice(GUID,IDispatch**)=0;
    virtual HRESULT STDMETHODCALLTYPE OpenDefaultDevice(IDispatch**)=0;
    virtual HRESULT STDMETHODCALLTYPE RegisterExpertNotificationClient(IUnknown**)=0;
    virtual HRESULT STDMETHODCALLTYPE UnregisterExpertNotificationClient(IUnknown**)=0;
    virtual HRESULT STDMETHODCALLTYPE FindDevice(BSTR,LONG,IDispatch**)=0;
    virtual HRESULT STDMETHODCALLTYPE GetDefaultProfileId(GUID*)=0;
    virtual HRESULT STDMETHODCALLTYPE SetDefaultProfileId(GUID)=0;
    virtual HRESULT STDMETHODCALLTYPE Save(BSTR)=0;
    virtual HRESULT STDMETHODCALLTYPE Load(BSTR)=0;
    virtual HRESULT STDMETHODCALLTYPE ImportDeviceFromFile(BSTR)=0;
    virtual HRESULT STDMETHODCALLTYPE ImportProfileFromFile(BSTR)=0;
    virtual HRESULT STDMETHODCALLTYPE ImportGlobalsFromFile(BSTR)=0;
    virtual HRESULT STDMETHODCALLTYPE Initialize(BSTR)=0;
    virtual HRESULT STDMETHODCALLTYPE ImportEQPresetFromFile(BSTR)=0;
    virtual HRESULT STDMETHODCALLTYPE ImportCaptureEQPresetFromFile(BSTR)=0;
    virtual HRESULT STDMETHODCALLTYPE Setup(BSTR)=0;
    virtual HRESULT STDMETHODCALLTYPE CleanUpDevices()=0;
    virtual HRESULT STDMETHODCALLTYPE CleanUpEqPresets()=0;
    virtual HRESULT STDMETHODCALLTYPE CleanUpCaptureEqPresets()=0;
    virtual HRESULT STDMETHODCALLTYPE OpenProfile(GUID,IDispatch**)=0;
};
