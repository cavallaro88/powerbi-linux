/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef PBI_TRANSPORT_H
#define PBI_TRANSPORT_H

struct pbi_transport
{
    HANDLE mapping;
    HANDLE mutex;
    void *view;
    HWND hwnd;
};

BOOL pbi_transport_publish(struct pbi_transport *transport, HWND hwnd, HWND window,
                           const void *pixels, UINT width, UINT height);
void pbi_transport_close(struct pbi_transport *transport);
BOOL pbi_dcomp_start_consumer(void);

#endif
