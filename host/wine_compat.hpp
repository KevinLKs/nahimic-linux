#pragma once
#include <windows.h>
#include <cstdio>
#include <cstring>

static BOOL WINAPI completed_setup_wait(void (CALLBACK*)(void*), void*, void** wait) {
    if (!wait) { SetLastError(ERROR_INVALID_PARAMETER); return FALSE; }
    *wait=nullptr;
    std::fprintf(stderr,"compat RegisterWaitUntilOOBECompleted: completed setup, ERROR_INVALID_STATE\n");
    std::fflush(stderr);
    SetLastError(ERROR_INVALID_STATE);
    return FALSE;
}

static bool replace_import(HMODULE module,const char* imported_dll,const char* imported_name,UINT_PTR replacement) {
    if (!GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"wine_get_version")) {
        std::fprintf(stderr,"Setup compatibility is only supported under Wine.\n"); return false;
    }
    auto base=reinterpret_cast<BYTE*>(module);
    auto dos=reinterpret_cast<IMAGE_DOS_HEADER*>(base);
    if (dos->e_magic!=IMAGE_DOS_SIGNATURE) return false;
    auto nt=reinterpret_cast<IMAGE_NT_HEADERS64*>(base+dos->e_lfanew);
    if (nt->Signature!=IMAGE_NT_SIGNATURE || nt->OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC) return false;
    auto directory=nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!directory.VirtualAddress || directory.Size<sizeof(IMAGE_IMPORT_DESCRIPTOR)) return false;
    auto imports=reinterpret_cast<IMAGE_IMPORT_DESCRIPTOR*>(base+directory.VirtualAddress);
    for (unsigned d=0;d<directory.Size/sizeof(*imports) && imports[d].Name;++d) {
        if (_stricmp(reinterpret_cast<char*>(base+imports[d].Name),imported_dll)) continue;
        if (!imports[d].OriginalFirstThunk) return false;
        auto names=reinterpret_cast<IMAGE_THUNK_DATA64*>(base+imports[d].OriginalFirstThunk);
        auto addresses=reinterpret_cast<IMAGE_THUNK_DATA64*>(base+imports[d].FirstThunk);
        for (unsigned n=0;names[n].u1.AddressOfData;++n) {
            if (IMAGE_SNAP_BY_ORDINAL64(names[n].u1.Ordinal)) {
                auto imported=GetModuleHandleA(imported_dll);
                auto expected=GetProcAddress(imported,imported_name);
                auto ordinal=GetProcAddress(imported,MAKEINTRESOURCEA(IMAGE_ORDINAL64(names[n].u1.Ordinal)));
                if (!expected || expected!=ordinal) continue;
            } else {
                auto name=reinterpret_cast<IMAGE_IMPORT_BY_NAME*>(base+names[n].u1.AddressOfData);
                if (std::strcmp(name->Name,imported_name)) continue;
            }
            DWORD old_protect=0;
            auto slot=&addresses[n].u1.Function;
            if (!VirtualProtect(slot,sizeof(*slot),PAGE_READWRITE,&old_protect)) return false;
            static_assert(sizeof(replacement)==sizeof(*slot));
            std::memcpy(slot,&replacement,sizeof(*slot));
            DWORD ignored=0;
            if (!VirtualProtect(slot,sizeof(*slot),old_protect,&ignored)) return false;
            return true;
        }
    }
    std::fprintf(stderr,"Expected import absent: %s!%s\n",imported_dll,imported_name);
    return false;
}

static bool install_wine_setup_compat(HMODULE module) {
    return replace_import(module,"kernel32.dll","RegisterWaitUntilOOBECompleted",reinterpret_cast<UINT_PTR>(&completed_setup_wait));
}

