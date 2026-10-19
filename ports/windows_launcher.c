#define UNICODE
#define _UNICODE
#include <windows.h>
#include <wchar.h>

int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,PWSTR args,int show) {
    wchar_t root[32768],python[32768],script[32768],command[65536];
    GetModuleFileNameW(NULL,root,32768);
    wchar_t *slash=wcsrchr(root,L'\\');if(!slash)return 1;*slash=0;
    swprintf(python,32768,L"%ls\\_internal\\pythonw.exe",root);
    swprintf(script,32768,L"%ls\\_internal\\app\\windows_app.py",root);
    swprintf(command,65536,L"\"%ls\" \"%ls\" %ls",python,script,args);
    STARTUPINFOW si={.cb=sizeof(si)};PROCESS_INFORMATION pi={0};
    if(!CreateProcessW(python,command,NULL,NULL,FALSE,CREATE_NO_WINDOW,NULL,root,&si,&pi)) {
        MessageBoxW(NULL,L"Please extract the entire ZIP before starting. Keep the _internal folder beside this EXE.\n\n请先完整解压 ZIP；_internal 文件夹必须和 EXE 放在一起。",L"Snake Xenzia",MB_OK|MB_ICONERROR);
        return 1;
    }
    CloseHandle(pi.hThread);WaitForSingleObject(pi.hProcess,INFINITE);
    DWORD code=1;GetExitCodeProcess(pi.hProcess,&code);CloseHandle(pi.hProcess);return code;
}
