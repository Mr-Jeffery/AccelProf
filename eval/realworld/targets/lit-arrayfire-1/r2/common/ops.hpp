/*******************************************************
 * Copyright (c) 2014, ArrayFire
 * All rights reserved.
 *
 * This file is distributed under 3-clause BSD license.
 * The complete license agreement can be obtained at:
 * http://arrayfire.com/licenses/BSD-3-Clause
 ********************************************************/
// (ArrayFire licence header of src/api/c/ops.hpp at a35a2d08, kept because parts of that file are copied below)
// cuRace R2 shim for src/api/c/ops.hpp (+ optypes.hpp): af_op_t and Binary/Transform.  The generic Binary (init 0, lhs + rhs),
// Binary<T, af_add_t> and the generic Transform below are copied from ops.hpp (identical in a35a2d08 and a7a297ba); the other
// operators (min/max/and/or...) are not instantiated by the driver and are omitted.
#pragma once
#include <backend.hpp>
#include <math.hpp>

#ifndef __DH__
#define __DH__
#endif

typedef enum {
    af_add_t = 0,
    af_sub_t,
    af_mul_t,
    af_div_t,
    af_and_t,
    af_or_t,
    af_min_t,
    af_max_t,
    af_notzero_t
} af_op_t;

using namespace detail;

template<typename T, af_op_t op>
struct Binary
{
    __DH__ T init()
    {
        return detail::scalar<T>(0);
    }

    __DH__ T operator() (T lhs, T rhs)
    {
        return lhs + rhs;
    }
};

template<typename T>
struct Binary<T, af_add_t>
{
    __DH__ T init()
    {
        return detail::scalar<T>(0);
    }

    __DH__ T operator() (T lhs, T rhs)
    {
        return lhs + rhs;
    }
};

template<typename Ti, typename To, af_op_t op>
struct Transform
{
    __DH__ To operator ()(Ti in)
    {
        return (To)(in);
    }
};
