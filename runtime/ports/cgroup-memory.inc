/* Clamp the memory reported to Windows apps to the cgroup v2 limits of the
 * current process. Wine reports host totals otherwise, so the .NET CLR,
 * Chromium (WebView2) and the Analysis Services engine size their heaps and
 * caches for the whole machine and get OOM-killed when the cgroup limit is
 * lower. Read once per query; the files are small. */
struct pbi_cgroup_memory
{
    unsigned long long max, current, swap_max, swap_current;
};

static unsigned long long pbi_cgroup_read_ull( const char *path )
{
    char buffer[64];
    FILE *fp = fopen( path, "r" );
    if (!fp) return 0;
    if (!fgets( buffer, sizeof(buffer), fp ))
    {
        fclose( fp );
        return 0;
    }
    fclose( fp );
    if (!strncmp( buffer, "max", 3 )) return 0;  /* no limit */
    return strtoull( buffer, NULL, 10 );
}

static void pbi_get_cgroup_memory( struct pbi_cgroup_memory *mem )
{
    char line[600], base[512] = {0};
    const char *flag;
    size_t len;
    FILE *fp;

    memset( mem, 0, sizeof(*mem) );
    flag = getenv( "PBI_CGROUP_MEMORY" );
    if (flag && flag[0] == '0') return;  /* PBI_CGROUP_MEMORY=0 desliga */
    if (!(fp = fopen( "/proc/self/cgroup", "r" ))) return;
    while (fgets( line, sizeof(line), fp ))
    {
        if (strncmp( line, "0::", 3 )) continue;  /* cgroup v2 unified hierarchy */
        len = strlen( line + 3 );
        while (len && (line[3 + len - 1] == '\n' || line[3 + len - 1] == '\r')) len--;
        snprintf( base, sizeof(base), "/sys/fs/cgroup/%.*s", (int)len, line + 3 );
        break;
    }
    fclose( fp );
    if (!base[0]) return;
    snprintf( line, sizeof(line), "%s/memory.max", base );
    mem->max = pbi_cgroup_read_ull( line );
    snprintf( line, sizeof(line), "%s/memory.current", base );
    mem->current = pbi_cgroup_read_ull( line );
    snprintf( line, sizeof(line), "%s/memory.swap.max", base );
    mem->swap_max = pbi_cgroup_read_ull( line );
    snprintf( line, sizeof(line), "%s/memory.swap.current", base );
    mem->swap_current = pbi_cgroup_read_ull( line );
}
