/* Optional capture of the actual SHM buffer accepted by the Wayland surface.
 * Restrict captures to Power BI; write one current file per HWND atomically.
 * This shows the driver's output, whereas CDP only shows browser rendering. */
static void pbi_dump_submitted_surface(struct wayland_window_surface *wws, struct wayland_shm_buffer *buffer)
{
    const char *directory = getenv("PBI_WAYLAND_CAPTURE_DIR");
    struct timespec now;
    uint64_t milliseconds;
    char path[1024], temp[1024];
    FILE *file;
    BITMAPINFOHEADER header = {0};
    unsigned char file_header[14] = {'B', 'M'};
    uint32_t size;
    if (!directory || !process_name || strcmp(process_name, "pbidesktop.exe")) return;
    if (buffer->width < 200 || buffer->height < 100 || buffer->width > 4096 || buffer->height > 2304) return;
    clock_gettime(CLOCK_MONOTONIC, &now);
    milliseconds = (uint64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
    if (milliseconds - wws->pbi_last_dump < 500) return;
    wws->pbi_last_dump = milliseconds;
    snprintf(path, sizeof(path), "%s/wayland-%08x.bmp", directory, (unsigned int)(ULONG_PTR)wws->header.hwnd);
    snprintf(temp, sizeof(temp), "%s/wayland-%08x.tmp", directory, (unsigned int)(ULONG_PTR)wws->header.hwnd);
    if (!(file = fopen(temp, "wb"))) return;
    size = 54 + buffer->width * buffer->height * 4;
    memcpy(file_header + 2, &size, 4); file_header[10] = 54;
    header.biSize = sizeof(header); header.biWidth = buffer->width;
    header.biHeight = -buffer->height; header.biPlanes = 1; header.biBitCount = 32;
    fwrite(file_header, 1, 14, file);
    fwrite(&header, 1, sizeof(header), file);
    fwrite(buffer->map_data, 1, buffer->width * buffer->height * 4, file);
    fclose(file);
    rename(temp, path);
}

