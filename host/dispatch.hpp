#pragma once
#include <oleauto.h>
#include <cstdio>

static HRESULT dispatch_call(IDispatch* object,const wchar_t* name,VARIANTARG* args,UINT count) {
    LPOLESTR method=const_cast<LPOLESTR>(name);DISPID id=0;
    HRESULT hr=object->GetIDsOfNames(IID_NULL,&method,1,LOCALE_SYSTEM_DEFAULT,&id);
    if(FAILED(hr)) {std::printf("GetIDsOfNames %ls=0x%08lx\n",name,static_cast<unsigned long>(hr));return hr;}
    DISPPARAMS parameters{args,nullptr,count,0};EXCEPINFO exception{};UINT argument=0;
    VARIANT result;VariantInit(&result);
    hr=object->Invoke(id,IID_NULL,LOCALE_SYSTEM_DEFAULT,DISPATCH_METHOD,&parameters,&result,&exception,&argument);
    if(FAILED(hr))std::printf("Invoke %ls=0x%08lx arg=%u exception=0x%08lx\n",name,static_cast<unsigned long>(hr),argument,static_cast<unsigned long>(exception.scode));
    VariantClear(&result);SysFreeString(exception.bstrSource);SysFreeString(exception.bstrDescription);SysFreeString(exception.bstrHelpFile);
    return hr;
}
static HRESULT dispatch_string(IDispatch* object,const wchar_t* name,BSTR* value) {
    VARIANTARG arg{};arg.vt=VT_BSTR|VT_BYREF;arg.pbstrVal=value;
    return dispatch_call(object,name,&arg,1);
}
static HRESULT dispatch_long(IDispatch* object,const wchar_t* name,LONG* value) {
    VARIANTARG arg{};arg.vt=VT_I4|VT_BYREF;arg.plVal=value;
    return dispatch_call(object,name,&arg,1);
}
static HRESULT dispatch_bool(IDispatch* object,const wchar_t* name,VARIANT_BOOL* value) {
    VARIANTARG arg{};arg.vt=VT_BOOL|VT_BYREF;arg.pboolVal=value;
    return dispatch_call(object,name,&arg,1);
}
static HRESULT dispatch_open(IDispatch* object,const wchar_t* name,IDispatch** value,const LONG* key=nullptr) {
    VARIANTARG args[2]{};args[0].vt=VT_DISPATCH|VT_BYREF;args[0].ppdispVal=value;
    if(key){args[1].vt=VT_I4;args[1].lVal=*key;}
    return dispatch_call(object,name,args,key?2:1);
}
