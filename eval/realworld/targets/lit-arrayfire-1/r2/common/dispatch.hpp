// cuRace R2 shim for src/backend/dispatch.hpp (+ nextpow2 from dispatch.cpp; divup macro identical in a35a2d08 and a7a297ba).
#pragma once

#define divup(a, b) (((a)+(b)-1)/(b))

inline unsigned nextpow2(unsigned x)
{
    x = x - 1;
    x = x | (x >> 1);
    x = x | (x >> 2);
    x = x | (x >> 4);
    x = x | (x >> 8);
    x = x | (x >>16);
    return x + 1;
}
