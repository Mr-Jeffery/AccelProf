// cuRace R2 shim for FWCore/Utilities/interface/Likely.h (included by the verbatim cudaCheck.h): same macros as CMSSW's.
#ifndef FWCore_Utilities_Likely_h
#define FWCore_Utilities_Likely_h

#if defined(__GNUC__)
#define LIKELY(x) (__builtin_expect(bool(x), true))
#define UNLIKELY(x) (__builtin_expect(bool(x), false))
#else
#define LIKELY(x) (x)
#define UNLIKELY(x) (x)
#endif

#endif
