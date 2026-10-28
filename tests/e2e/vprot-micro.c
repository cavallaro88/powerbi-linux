#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
static void stage(const char *name) {
    printf("%s\n", name); fflush(stdout);
    if (getchar() == EOF) ExitProcess(20);
}
int main(int argc, char **argv) {
    SIZE_T size = (SIZE_T)(argc > 1 ? strtoull(argv[1], NULL, 10) : 64) << 30;
    stage("baseline");
    void *p = VirtualAlloc(NULL, size, MEM_RESERVE, PAGE_NOACCESS);
    if (!p) { printf("reserve_failed=%lu\n", GetLastError()); return 1; }
    stage("reserved");
    for (SIZE_T i=0; i<size; i+=((SIZE_T)4<<30)) {
        void *q=VirtualAlloc((char*)p+i,4096,MEM_COMMIT,PAGE_READWRITE);
        if (!q) return 2;
        *(volatile char*)q=1;
    }
    stage("sparse_committed_touched");
    if (!VirtualFree(p,size,MEM_DECOMMIT)) return 3;
    stage("decommitted");
    if (!VirtualFree(p,0,MEM_RELEASE)) return 4;
    stage("released");
    p=VirtualAlloc(NULL,size,MEM_RESERVE,PAGE_NOACCESS);
    if (!p) return 5;
    stage("reserved_again");
    if (!VirtualFree(p,0,MEM_RELEASE)) return 6;
    stage("released_again");
    return 0;
}
