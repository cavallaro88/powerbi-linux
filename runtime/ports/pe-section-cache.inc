/* Opt-in Linux backing for large, unaligned PE sections. MAP_PRIVATE keeps
 * Windows write-copy/relocation semantics. Source PE files remain authoritative;
 * cache entries are prebuilt, content-verified by the launcher, and keyed by
 * inode, ctime, size and byte range. Missing/stale entries use Wine's read path. */
static BOOL pbi_map_cached_pe_section(struct file_view *view, int fd, void *address,
                                      size_t bytes, size_t mapped, off_t offset,
                                      int prot, unsigned int vprot, BOOL removable)
{
#ifdef __linux__
    const char *directory = getenv("PBI_PE_SECTION_CACHE");
    struct stat source, cache;
    char name[2048], magic[8];
    int cache_fd;
    BOOL success = FALSE;
    if (!directory || !(view->protect & SEC_IMAGE) || removable || (vprot & VPROT_WRITE) ||
        !(offset & host_page_mask) || bytes < 16 * 1024 * 1024 || fstat(fd, &source)) return FALSE;
    if (snprintf(name, sizeof(name), "%s/%llx-%llx-%llx-%llx-%llx-%llx-%llx.bin", directory,
                 (unsigned long long)source.st_dev, (unsigned long long)source.st_ino,
                 (unsigned long long)source.st_ctim.tv_sec, (unsigned long long)source.st_ctim.tv_nsec,
                 (unsigned long long)source.st_size, (unsigned long long)offset,
                 (unsigned long long)bytes) >= sizeof(name)) return FALSE;
    cache_fd = open(name, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (cache_fd < 0) return FALSE;
    if (!fstat(cache_fd, &cache) && S_ISREG(cache.st_mode) && cache.st_uid == getuid() &&
        !(cache.st_mode & 0222) && cache.st_size == mapped + 4096 &&
        pread(cache_fd, magic, sizeof(magic), 0) == sizeof(magic) && !memcmp(magic, "PBICACH1", 8))
    {
        success = mmap(address, mapped, prot, MAP_FIXED | MAP_PRIVATE, cache_fd, 4096) != MAP_FAILED;
        if (success && getenv("PBI_COMPOSITION_DIAG"))
            WARN("pbi-pe-cache: mapped %zu bytes at %p source-offset=%llx\n", mapped, address,
                 (unsigned long long)offset);
    }
    close(cache_fd);
    return success;
#else
    return FALSE;
#endif
}
