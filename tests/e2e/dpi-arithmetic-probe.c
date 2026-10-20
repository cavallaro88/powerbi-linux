/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Compile the actual Wine source helper, supplied unchanged in dpi-helper.h. */
#include <stdint.h>
#include <stdio.h>
typedef int64_t INT64;
struct ratio { unsigned int num, den; };
#include "dpi-helper.h"

int main(void)
{
    const struct { int value; struct ratio from, to; int expected; } cases[] = {
        { -4, {1,1}, {5,4}, -5 }, { -3, {1,1}, {5,4}, -4 },
        { -1, {1,1}, {5,4}, -1 }, { 0, {1,1}, {5,4}, 0 },
        { 1000, {1,1}, {5,4}, 1250 }, { -5, {5,4}, {1,1}, -4 },
        { -300, {3,2}, {5,4}, -250 }, { 300, {3,2}, {5,4}, 250 },
        { -2000000000, {2,1}, {1,1}, -1000000000 },
        { 2000000000, {2,1}, {1,1}, 1000000000 },
        { -1000000000, {1,1}, {2,1}, -2000000000 },
        { 1000000000, {1,1}, {2,1}, 2000000000 },
        { -4, {1,1}, {1,1}, -4 }, { 4, {1,1}, {1,1}, 4 }
    };
    unsigned int failed = 0, i;
    for (i = 0; i < sizeof(cases)/sizeof(cases[0]); i++)
        if (scale_dpi(cases[i].value, cases[i].from, cases[i].to) != cases[i].expected)
            failed++;
    printf("{\"checks\":%u,\"failed\":%u}\n", i, failed);
    return failed ? 1 : 0;
}
