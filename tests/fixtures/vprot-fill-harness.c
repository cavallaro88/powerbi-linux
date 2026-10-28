#include <sys/mman.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
typedef unsigned char BYTE;
typedef uintptr_t UINT_PTR;
static uintptr_t host_page_mask;
static int fail_advice, advice_calls;
static int test_advice(void *p, size_t n, int a) {
 advice_calls++;
 if(fail_advice==1)return -1;
 if(fail_advice==2) { if(n>=8192)madvise(p,4096,a); return -1; }
 return madvise(p,n,a);
}
#define madvise test_advice
/* CANDIDATE_HELPER */

#undef madvise
int main(void) {
 size_t n=1024*1024, tests=0;
 host_page_mask=(uintptr_t)sysconf(_SC_PAGESIZE)-1;
 BYTE *actual=mmap(NULL,n,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 BYTE *expected=malloc(n);
 if(actual==MAP_FAILED || !expected)return 2;
 unsigned seed=19;
 for(int fail=0;fail<3;fail++) {
  fail_advice=fail;
  for(int i=0;i<2000;i++) {
   size_t off=rand_r(&seed)%n;
   size_t len=rand_r(&seed)%(n-off+1);
   BYTE value=i%3 ? 0 : 0x61;
   memset(actual,0xa5,n); memset(expected,0xa5,n);
   memset(expected+off,value,len);fill_page_vprot(actual+off,len,value);
   if(memcmp(actual,expected,n)){printf("FAIL off=%zu len=%zu fail=%d\n",off,len,fail);return 1;}
   tests++;
  }
 }
 /* Deterministic boundaries; larger masks simulate arithmetic only on this 4KiB host. */
 for(size_t page=4096;page<=65536;page*=4) {
  host_page_mask=page-1;
  size_t offsets[]={0,1,page-1,page,page+1};
  size_t lengths[]={0,1,page-1,page,page+1,2*page-1,2*page,2*page+1};
  for(int fail=0;fail<3;fail++) for(unsigned i=0;i<5;i++) for(unsigned j=0;j<8;j++) {
   fail_advice=fail;size_t off=offsets[i],len=lengths[j];
   memset(actual,0xa5,n);memset(expected,0xa5,n);
   memset(expected+off,0,len);fill_page_vprot(actual+off,len,0);
   if(memcmp(actual,expected,n)){printf("FAIL deterministic page=%zu off=%zu len=%zu\n",page,off,len);return 4;}
   tests++;
  }
 }
 host_page_mask=(uintptr_t)sysconf(_SC_PAGESIZE)-1;
 fill_page_vprot(actual+n,0,0);
 memset(actual,0xff,n);fill_page_vprot(actual,n,0);
 memset(expected,0,n);if(memcmp(actual,expected,n))return 3;
 printf("PASS differential_cases=%zu advice_calls=%d fallback_forced=1\n",tests,advice_calls);
 munmap(actual,n);free(expected);return 0;
}
