#include <windows.h>
#include <stdio.h>
#define CHECK(x) do { if (!(x)) { printf("FAIL line=%d error=%lu\n",__LINE__,GetLastError()); ExitProcess(1); } checks++; } while(0)
static LONG checks;
static volatile LONG guards;
static LONG CALLBACK handler(EXCEPTION_POINTERS *e) {
 if(e->ExceptionRecord->ExceptionCode==STATUS_GUARD_PAGE_VIOLATION) { InterlockedIncrement(&guards); return EXCEPTION_CONTINUE_EXECUTION; }
 return EXCEPTION_CONTINUE_SEARCH;
}
static DWORD WINAPI worker(void *unused) {
 (void)unused;
 for(int i=0;i<200;i++) {
  char *p=VirtualAlloc(NULL,32*1024*1024,MEM_RESERVE,PAGE_NOACCESS);
  if(!p)return 1;
  char *q=VirtualAlloc(p+65536,4096,MEM_COMMIT,PAGE_READWRITE);
  if(!q)return 2;
  *q=42;
  if(!VirtualFree(p,0,MEM_RELEASE))return 3;
 }
 return 0;
}
int main(void) {
 MEMORY_BASIC_INFORMATION m; DWORD old; SIZE_T size=(SIZE_T)8<<30;
 char *p=VirtualAlloc(NULL,size,MEM_RESERVE,PAGE_NOACCESS);CHECK(p);
 CHECK(VirtualQuery(p,&m,sizeof(m))==sizeof(m));CHECK(m.State==MEM_RESERVE && m.Protect==0);
 SIZE_T offsets[]={0,65536,((SIZE_T)4<<30)-4096,((SIZE_T)4<<30),size-4096};
 for(unsigned i=0;i<5;i++) {
  char *q=VirtualAlloc(p+offsets[i],4096,MEM_COMMIT,PAGE_READWRITE);CHECK(q==p+offsets[i]);*q=(char)(i+1);
 }
 /* Partial zero fills must not discard neighbor metadata in the same host page. */
 for(int i=0;i<100;i++) {
  CHECK(VirtualFree(p+65536,4096,MEM_DECOMMIT));
  CHECK(VirtualQuery(p,&m,sizeof(m))==sizeof(m));CHECK(m.State==MEM_COMMIT && m.Protect==PAGE_READWRITE);CHECK(*p==1);
  CHECK(VirtualAlloc(p+65536,4096,MEM_COMMIT,PAGE_READWRITE)==p+65536);CHECK(p[65536]==0);p[65536]=2;
 }
 CHECK(VirtualProtect(p,4096,PAGE_NOACCESS,&old));CHECK(VirtualQuery(p,&m,sizeof(m))==sizeof(m));CHECK(m.State==MEM_COMMIT && m.Protect==PAGE_NOACCESS);
 CHECK(VirtualProtect(p,4096,PAGE_READWRITE,&old));CHECK(*p==1);
 CHECK(AddVectoredExceptionHandler(1,handler)!=NULL);
 CHECK(VirtualProtect(p,4096,PAGE_READWRITE|PAGE_GUARD,&old));CHECK(*p==1);CHECK(guards==1);CHECK(*p==1 && guards==1);
 for(unsigned i=0;i<5;i++)CHECK(p[offsets[i]]==(char)(i+1));
 CHECK(VirtualFree(p,0,MEM_RELEASE));
 CHECK(VirtualAlloc(p,size,MEM_RESERVE,PAGE_NOACCESS)==p);
 CHECK(VirtualQuery(p+((SIZE_T)4<<30),&m,sizeof(m))==sizeof(m));CHECK(m.State==MEM_RESERVE && m.Protect==0);
 CHECK(VirtualFree(p,0,MEM_RELEASE));
 p=VirtualAlloc(NULL,65536,MEM_RESERVE,PAGE_READWRITE);CHECK(p);CHECK(VirtualQuery(p,&m,sizeof(m))==sizeof(m));CHECK(m.State==MEM_RESERVE && m.AllocationProtect==PAGE_READWRITE);CHECK(VirtualFree(p,0,MEM_RELEASE));
 p=VirtualAlloc(NULL,65536,MEM_RESERVE|MEM_COMMIT|MEM_WRITE_WATCH,PAGE_READWRITE);CHECK(p);p[4096]=7;
 void *pages[16];ULONG_PTR count=16;ULONG granularity=0;
 CHECK(GetWriteWatch(0,p,65536,pages,&count,&granularity)==0);CHECK(count==1 && pages[0]==p+4096);CHECK(ResetWriteWatch(p,65536)==0);
 count=16;CHECK(GetWriteWatch(0,p,65536,pages,&count,&granularity)==0 && count==0);CHECK(VirtualFree(p,0,MEM_RELEASE));
 HANDLE threads[4];for(int i=0;i<4;i++){threads[i]=CreateThread(NULL,0,worker,NULL,0,NULL);CHECK(threads[i]);}
 CHECK(WaitForMultipleObjects(4,threads,TRUE,60000)==WAIT_OBJECT_0);
 for(int i=0;i<4;i++){DWORD code;CHECK(GetExitCodeThread(threads[i],&code));CHECK(code==0);CloseHandle(threads[i]);}
 printf("PASS checks=%ld guard_faults=%ld threaded_cycles=800\n",checks,guards);return 0;
}
