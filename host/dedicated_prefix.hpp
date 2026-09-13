#pragma once
#include <windows.h>
#include <string>

inline bool dedicated_prefix() {
    wchar_t prefix[2048]{};
    DWORD count = GetEnvironmentVariableW(L"WINEPREFIX", prefix, 2048);
    if (!GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "wine_get_version") ||
        !count || count >= 2048 || prefix[0] != L'/') return false;
    std::wstring path = L"Z:" + std::wstring(prefix) + L"/.nahimic-linux-owner";
    for (auto& ch : path) if (ch == L'/') ch = L'\\';
    HANDLE file = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
                              OPEN_EXISTING, 0, nullptr);
    if (file == INVALID_HANDLE_VALUE) return false;
    char marker[32]{}; DWORD read = 0;
    bool valid = ReadFile(file, marker, sizeof(marker), &read, nullptr) &&
                 read == 17 && std::string(marker, read) == "nahimic-linux-v1\n";
    CloseHandle(file);
    return valid;
}
