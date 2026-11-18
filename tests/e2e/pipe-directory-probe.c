/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Lists the named pipe root directory (\\.\pipe\) the ways applications do: FindFirstFile and
 * NtQueryDirectoryFile with every directory information class, a mask kept across calls, a
 * restart, a truncated entry, no match, no access, a removed pipe and more pipes than one
 * server reply holds. Wine 11.18 answered every one of them with STATUS_BAD_DEVICE_TYPE.
 * Prints one line per failure and RESULT passed=N failed=M. */
#include <windows.h>
#include <winternl.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

typedef NTSTATUS (NTAPI *query_dir_fn)( HANDLE, HANDLE, void *, void *, IO_STATUS_BLOCK *, void *, ULONG,
                                        ULONG, BOOLEAN, UNICODE_STRING *, BOOLEAN );
typedef NTSTATUS (NTAPI *open_file_fn)( HANDLE *, ACCESS_MASK, OBJECT_ATTRIBUTES *, IO_STATUS_BLOCK *, ULONG, ULONG );

#define S_SUCCESS          ((NTSTATUS)0x00000000)
#define S_BUFFER_OVERFLOW  ((NTSTATUS)0x80000005)
#define S_NO_MORE_FILES    ((NTSTATUS)0x80000006)
#define S_NO_SUCH_FILE     ((NTSTATUS)0xC000000F)
#define S_ACCESS_DENIED    ((NTSTATUS)0xC0000022)

static query_dir_fn pNtQueryDirectoryFile;
static open_file_fn pNtOpenFile;
static int passed, failed;
static WCHAR base[64];

#define CHECK(cond, ...) do { if (cond) passed++; else { failed++; printf( "FAIL line %d: ", __LINE__ ); \
    printf( __VA_ARGS__ ); printf( "\n" ); } } while (0)

/* offset of FileName and of FileNameLength per information class (Windows layouts, x64) */
static ULONG name_offset( ULONG class )
{
    switch (class)
    {
    case 1: return 64;   /* FileDirectoryInformation */
    case 2: return 68;   /* FileFullDirectoryInformation */
    case 3: return 94;   /* FileBothDirectoryInformation */
    case 12: return 12;  /* FileNamesInformation */
    case 37: return 104; /* FileIdBothDirectoryInformation */
    case 38: return 80;  /* FileIdFullDirectoryInformation */
    case 50: return 92;  /* FileIdGlobalTxDirectoryInformation */
    case 63: return 114; /* FileIdExtdBothDirectoryInformation */
    }
    return 0;
}

static HANDLE open_root( ACCESS_MASK access )
{
    UNICODE_STRING name = { 18, 20, (WCHAR *)L"\\??\\pipe\\" };
    OBJECT_ATTRIBUTES attr;
    IO_STATUS_BLOCK io;
    HANDLE handle = NULL;
    NTSTATUS status;

    memset( &attr, 0, sizeof(attr) );
    attr.Length = sizeof(attr);
    attr.ObjectName = &name;
    attr.Attributes = OBJ_CASE_INSENSITIVE;
    status = pNtOpenFile( &handle, access | SYNCHRONIZE, &attr, &io, FILE_SHARE_READ | FILE_SHARE_WRITE,
                                   0x1 /* FILE_DIRECTORY_FILE */ | 0x20 /* FILE_SYNCHRONOUS_IO_NONALERT */ );
    CHECK( !status, "open of the pipe root with access %#lx: %08lx", (unsigned long)access, (unsigned long)status );
    return status ? NULL : handle;
}

static NTSTATUS query( HANDLE dir, void *buffer, ULONG length, ULONG class, BOOLEAN single,
                       const WCHAR *mask, BOOLEAN restart, IO_STATUS_BLOCK *io )
{
    UNICODE_STRING str;
    if (mask)
    {
        str.Buffer = (WCHAR *)mask;
        str.Length = str.MaximumLength = wcslen( mask ) * sizeof(WCHAR);
    }
    io->Information = 0xdead;
    return pNtQueryDirectoryFile( dir, NULL, NULL, NULL, io, buffer, length, class, single, mask ? &str : NULL, restart );
}

static HANDLE make_pipe( const WCHAR *suffix, DWORD max )
{
    WCHAR name[128];
    swprintf( name, 128, L"\\\\.\\pipe\\%ls%ls", base, suffix );
    return CreateNamedPipeW( name, PIPE_ACCESS_DUPLEX, PIPE_TYPE_BYTE, max, 512, 512, 0, NULL );
}

/* count FindFirstFile matches of base+pattern; return the size of the entry named base+want */
static int find_count( const WCHAR *pattern, const WCHAR *want, DWORD *size, DWORD *attrs, DWORD *error )
{
    WCHAR path[160], name[128];
    WIN32_FIND_DATAW data;
    HANDLE find;
    int count = 0;

    swprintf( path, 160, L"\\\\.\\pipe\\%ls%ls", base, pattern );
    swprintf( name, 128, L"%ls%ls", base, want ? want : L"" );
    *error = 0;
    if ((find = FindFirstFileW( path, &data )) == INVALID_HANDLE_VALUE)
    {
        *error = GetLastError();
        return -1;
    }
    do
    {
        count++;
        if (want && !wcscmp( data.cFileName, name ))
        {
            *size = data.nFileSizeLow;
            *attrs = data.dwFileAttributes;
        }
    } while (FindNextFileW( find, &data ));
    *error = GetLastError();
    FindClose( find );
    return count;
}

static int contains_name( const char *entry, ULONG class, const WCHAR *name )
{
    ULONG len = *(const ULONG *)(entry + (class == 12 ? 8 : 60));
    return len == wcslen( name ) * sizeof(WCHAR) && !memcmp( entry + name_offset( class ), name, len );
}

int wmain( void )
{
    static const ULONG classes[] = { 1, 2, 3, 12, 37, 38, 50, 63 };
    HMODULE ntdll = GetModuleHandleW( L"ntdll.dll" );
    HANDLE alpha[2], beta, gamma, dir, bulk[1100];
    WCHAR name[128], mask[128];
    char buffer[8192];
    IO_STATUS_BLOCK io;
    NTSTATUS status;
    DWORD size = 0, attrs = 0, error;
    unsigned int i, seen;
    int count;

    pNtQueryDirectoryFile = (query_dir_fn)GetProcAddress( ntdll, "NtQueryDirectoryFile" );
    pNtOpenFile = (open_file_fn)GetProcAddress( ntdll, "NtOpenFile" );
    swprintf( base, 64, L"pbi-pipe-dir-%lu-", (unsigned long)GetCurrentProcessId() );

    alpha[0] = make_pipe( L"alpha", 4 );
    alpha[1] = make_pipe( L"alpha", 4 );
    beta = make_pipe( L"beta.part", PIPE_UNLIMITED_INSTANCES );
    gamma = make_pipe( L"gamma", 1 );
    CHECK( alpha[0] != INVALID_HANDLE_VALUE && alpha[1] != INVALID_HANDLE_VALUE &&
           beta != INVALID_HANDLE_VALUE && gamma != INVALID_HANDLE_VALUE, "pipe creation failed" );

    /* FindFirstFile over the whole root, then with masks */
    swprintf( name, 128, L"%lsalpha", base );
    size = attrs = 0;
    {
        WIN32_FIND_DATAW data;
        HANDLE find = FindFirstFileW( L"\\\\.\\pipe\\*", &data );
        int total = 0, found = 0;
        CHECK( find != INVALID_HANDLE_VALUE, "FindFirstFile(\\\\.\\pipe\\*) failed: %lu", GetLastError() );
        if (find != INVALID_HANDLE_VALUE)
        {
            do
            {
                total++;
                if (!wcscmp( data.cFileName, name ))
                {
                    found++;
                    size = data.nFileSizeLow;
                    attrs = data.dwFileAttributes;
                }
            } while (FindNextFileW( find, &data ));
            CHECK( GetLastError() == ERROR_NO_MORE_FILES, "FindNextFile ended with %lu", GetLastError() );
            FindClose( find );
        }
        CHECK( total >= 3 && found == 1, "whole root: %d entries, alpha found %d times", total, found );
        CHECK( size == 2, "alpha reports %lu instances, expected 2", size );
        CHECK( attrs == FILE_ATTRIBUTE_NORMAL, "alpha attributes %#lx", attrs );
    }
    count = find_count( L"*", L"beta.part", &size, &attrs, &error );
    CHECK( count == 3, "mask base*: %d entries (error %lu)", count, error );
    CHECK( size == 1, "beta.part reports %lu instances", size );
    count = find_count( L"*.part", NULL, &size, &attrs, &error );
    CHECK( count == 1, "mask *.part: %d entries", count );
    count = find_count( L"nomatch*", NULL, &size, &attrs, &error );
    CHECK( count == -1 && error == ERROR_FILE_NOT_FOUND, "no match: count %d error %lu", count, error );

    /* the mask of the first query is kept by later queries without one */
    swprintf( mask, 128, L"%ls*", base );
    if ((dir = open_root( FILE_LIST_DIRECTORY )))
    {
        status = query( dir, buffer, sizeof(buffer), 1, TRUE, mask, TRUE, &io );
        CHECK( status == S_SUCCESS, "single entry with mask: %08lx", (unsigned long)status );
        seen = status == S_SUCCESS;
        while (!(status = query( dir, buffer, sizeof(buffer), 1, TRUE, NULL, FALSE, &io )))
        {
            seen++;
            CHECK( !wcsncmp( (WCHAR *)(buffer + 64), base, wcslen( base ) ), "entry outside the stored mask" );
            if (seen > 10) break;
        }
        CHECK( seen == 3 && status == S_NO_MORE_FILES, "stored mask: %u entries, then %08lx", seen, (unsigned long)status );
        status = query( dir, buffer, sizeof(buffer), 1, FALSE, NULL, TRUE, &io );
        CHECK( status == S_SUCCESS && !wcsncmp( (WCHAR *)(buffer + 64), base, wcslen( base ) ),
               "restart without a mask: %08lx", (unsigned long)status );
        CloseHandle( dir );
    }

    /* every information class, on a fresh handle each */
    for (i = 0; i < ARRAYSIZE(classes); i++)
    {
        if (!(dir = open_root( FILE_LIST_DIRECTORY ))) continue;
        memset( buffer, 0xcc, sizeof(buffer) );
        status = query( dir, buffer, sizeof(buffer), classes[i], FALSE, name, TRUE, &io );
        CHECK( status == S_SUCCESS, "class %lu: %08lx", classes[i], (unsigned long)status );
        if (!status)
        {
            CHECK( *(ULONG *)buffer == 0, "class %lu: more than one entry", classes[i] );
            CHECK( contains_name( buffer, classes[i], name ), "class %lu: wrong name or length", classes[i] );
            CHECK( io.Information == name_offset( classes[i] ) + wcslen( name ) * sizeof(WCHAR),
                   "class %lu: information %lu", classes[i], (unsigned long)io.Information );
            if (classes[i] != 12)
                CHECK( *(LONGLONG *)(buffer + 40) == 2 && *(LONGLONG *)(buffer + 48) == 4 &&
                       *(ULONG *)(buffer + 56) == FILE_ATTRIBUTE_NORMAL,
                       "class %lu: size %lld allocation %lld attributes %#lx", classes[i],
                       *(LONGLONG *)(buffer + 40), *(LONGLONG *)(buffer + 48), *(ULONG *)(buffer + 56) );
        }
        CloseHandle( dir );
    }

    /* a buffer too small for the name: the entry comes back truncated and is consumed */
    if ((dir = open_root( FILE_LIST_DIRECTORY )))
    {
        status = query( dir, buffer, 72, 1, FALSE, name, TRUE, &io );
        CHECK( status == S_BUFFER_OVERFLOW && io.Information == 72 && *(ULONG *)(buffer + 60) == wcslen( name ) * sizeof(WCHAR),
               "truncated entry: %08lx information %lu", (unsigned long)status, (unsigned long)io.Information );
        status = query( dir, buffer, sizeof(buffer), 1, FALSE, NULL, FALSE, &io );
        CHECK( status == S_NO_MORE_FILES, "after the truncated entry: %08lx", (unsigned long)status );
        CloseHandle( dir );
    }

    /* no match: no such file on the first query, no more files after it */
    if ((dir = open_root( FILE_LIST_DIRECTORY )))
    {
        status = query( dir, buffer, sizeof(buffer), 3, FALSE, L"pbi-pipe-dir-none-*", TRUE, &io );
        CHECK( status == S_NO_SUCH_FILE, "no match, first query: %08lx", (unsigned long)status );
        status = query( dir, buffer, sizeof(buffer), 3, FALSE, NULL, FALSE, &io );
        CHECK( status == S_NO_MORE_FILES, "no match, second query: %08lx", (unsigned long)status );
        CloseHandle( dir );
    }

    /* listing needs FILE_LIST_DIRECTORY */
    if ((dir = open_root( 0 )))
    {
        status = query( dir, buffer, sizeof(buffer), 1, FALSE, NULL, TRUE, &io );
        CHECK( status == S_ACCESS_DENIED, "without list access: %08lx", (unsigned long)status );
        CloseHandle( dir );
    }

    /* a pipe whose last instance closed is gone */
    CloseHandle( gamma );
    count = find_count( L"*", L"alpha", &size, &attrs, &error );
    CHECK( count == 2, "after closing gamma: %d entries", count );

    /* more pipes than one server reply holds, read through FindNextFile's small buffer */
    for (i = 0; i < ARRAYSIZE(bulk); i++)
    {
        swprintf( name, 128, L"bulk-%04u-padding-the-name-to-sixty-characters-xxxxxxxxxx", i );
        bulk[i] = make_pipe( name, 1 );
        if (bulk[i] == INVALID_HANDLE_VALUE) break;
    }
    CHECK( i == ARRAYSIZE(bulk), "created %u of %u bulk pipes", i, (unsigned)ARRAYSIZE(bulk) );
    count = find_count( L"bulk-*", NULL, &size, &attrs, &error );
    CHECK( count == (int)ARRAYSIZE(bulk), "bulk: %d of %u listed", count, (unsigned)ARRAYSIZE(bulk) );
    for (i = 0; i < ARRAYSIZE(bulk); i++) if (bulk[i] != INVALID_HANDLE_VALUE) CloseHandle( bulk[i] );

    CloseHandle( alpha[0] );
    CloseHandle( alpha[1] );
    CloseHandle( beta );
    count = find_count( L"*", NULL, &size, &attrs, &error );
    CHECK( count == -1 && error == ERROR_FILE_NOT_FOUND, "after closing all: %d entries", count );

    printf( "RESULT passed=%d failed=%d\n", passed, failed );
    return failed ? 1 : 0;
}
