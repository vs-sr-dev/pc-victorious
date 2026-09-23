// Native self-test of the recompiled executable.
//
// Loads the retail main.dol into guest memory and calls functions of the
// game's own C library and SDK *as recompiled*: string and number formatting
// (varargs, doubles), 64-bit division helpers, sorting through a game
// comparator (indirect calls), libm, and the SDK's paired-single matrix code.
// Each result is checked against the host computing the same thing.
//
//     selftest build/extract/sys/main.dol build/symbols.tsv
#include "ppc.h"
#include "mem.h"
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <random>
#include <sstream>
#include <string>
#include <vector>
#include <strings.h>

PPCFunc ppc_lookup(uint32_t addr);

static std::map<std::string, uint32_t> g_sym;
static PPCContext c;
static uint32_t g_heap = 0x81000000u;
static int g_pass = 0, g_fail = 0;

static void load_symbols(const char* path) {
    std::ifstream f(path);
    std::string line;
    std::getline(f, line);
    while (std::getline(f, line)) {
        std::stringstream ss(line);
        std::string addr, size, bind, type, sec, name;
        std::getline(ss, addr, '\t'); std::getline(ss, size, '\t'); std::getline(ss, bind, '\t');
        std::getline(ss, type, '\t'); std::getline(ss, sec, '\t'); std::getline(ss, name, '\t');
        if (type == "2" || name.rfind("_SDA", 0) == 0) g_sym[name] = (uint32_t)std::stoul(addr, nullptr, 16);
    }
}

static uint32_t alloc(uint32_t n) { uint32_t a = g_heap; g_heap += (n + 31) & ~31u; return a; }
static uint32_t put_str(const std::string& s) { uint32_t a = alloc((uint32_t)s.size() + 1); mem_write(a, s.c_str(), s.size() + 1); return a; }
static std::string get_str(uint32_t a) { std::string s; for (char ch; (ch = (char)g_mem[a]); ++a) s += ch; return s; }
static void put_f32(uint32_t a, float v) { st32(a, as_u32(v)); }
static float get_f32(uint32_t a) { return as_f32(ld32(a)); }

// Call a guest function by name: integer args in r3.., FP args in f1..
static void call(const char* name, std::vector<uint32_t> args, std::vector<double> fargs = {}) {
    auto it = g_sym.find(name);
    if (it == g_sym.end()) { std::fprintf(stderr, "no symbol %s\n", name); std::exit(2); }
    PPCFunc fn = ppc_lookup(it->second);
    if (!fn) { std::fprintf(stderr, "no recompiled function at %08X (%s)\n", it->second, name); std::exit(2); }
    for (size_t i = 0; i < args.size(); ++i) c.r[3 + i] = args[i];
    for (size_t i = 0; i < fargs.size(); ++i) c.f[1 + i] = fargs[i];
    c.cr[6] = !fargs.empty();          // CR1[eq]: varargs callers flag FP arguments
    c.r[1] = 0x817F0000u;
    c.lr = 0;
    fn(c);
}

static void check(bool ok, const char* what, const std::string& detail = "") {
    (ok ? g_pass : g_fail)++;
    std::printf("  %s  %s%s%s\n", ok ? "ok  " : "FAIL", what, detail.empty() ? "" : "  ", detail.c_str());
}

static bool close(double a, double b, double rel) { return std::fabs(a - b) <= rel * std::max(1.0, std::fabs(b)); }

int main(int argc, char** argv) {
    if (argc < 3) { std::fprintf(stderr, "usage: selftest main.dol symbols.tsv\n"); return 2; }
    if (!mem_init()) { std::fprintf(stderr, "mem_init failed\n"); return 1; }
    uint32_t entry = mem_load_dol(argv[1]);
    load_symbols(argv[2]);
    std::printf("main.dol loaded, entry %08X, %zu symbols\n", entry, g_sym.size());
    c.r[2] = g_sym["_SDA2_BASE_"];
    c.r[13] = g_sym["_SDA_BASE_"];

    std::printf("strings\n");
    call("strlen", {put_str("Hollywood Arts High School")});
    check(c.r[3] == std::strlen("Hollywood Arts High School"), "strlen", std::to_string(c.r[3]));
    call("strcmp", {put_str("Victoria"), put_str("Victorious")});
    check((int32_t)c.r[3] < 0, "strcmp less");
    call("strcmp", {put_str("Sikowitz"), put_str("Sikowitz")});
    check(c.r[3] == 0, "strcmp equal");
    call("atoi", {put_str("-4242")});
    check((int32_t)c.r[3] == -4242, "atoi", std::to_string((int32_t)c.r[3]));
    call("strtod", {put_str("3.14159e2"), 0});
    check(c.f[1] == std::strtod("3.14159e2", nullptr), "strtod", std::to_string(c.f[1]));

    std::printf("sprintf (varargs, integers, strings, doubles)\n");
    const char* fmt = "%s has %d fans, %.3f%% hip, 0x%08X, [%-6s] %10.4e %g";
    uint32_t buf = alloc(256);
    call("sprintf", {buf, put_str(fmt), put_str("Tori"), 12345u, 0xDEADBEEFu, put_str("Jade")},
         {99.5, 1234.5678, 0.000125});
    char host[256];
    std::snprintf(host, sizeof host, fmt, "Tori", 12345, 99.5, 0xDEADBEEFu, "Jade", 1234.5678, 0.000125);
    std::string guest = get_str(buf);
    check(guest == host && c.r[3] == guest.size(), "sprintf", "\"" + guest + "\"");

    std::printf("64-bit integer helpers\n");
    std::mt19937_64 rng(2012);
    bool div_ok = true;
    for (int i = 0; i < 2000; ++i) {
        int64_t a = (int64_t)rng(), b = (int64_t)(rng() >> (rng() % 60));
        if (!b) continue;
        call("__div2i", {(uint32_t)(a >> 32), (uint32_t)a, (uint32_t)(b >> 32), (uint32_t)b});
        int64_t q = (int64_t)((uint64_t)c.r[3] << 32 | c.r[4]);
        call("__mod2i", {(uint32_t)(a >> 32), (uint32_t)a, (uint32_t)(b >> 32), (uint32_t)b});
        int64_t m = (int64_t)((uint64_t)c.r[3] << 32 | c.r[4]);
        call("__div2u", {(uint32_t)((uint64_t)a >> 32), (uint32_t)a, (uint32_t)((uint64_t)b >> 32), (uint32_t)b});
        uint64_t qu = (uint64_t)c.r[3] << 32 | c.r[4];
        if (q != a / b || m != a % b || qu != (uint64_t)a / (uint64_t)b) { div_ok = false; break; }
    }
    check(div_ok, "__div2i / __mod2i / __div2u on 2000 random pairs");

    std::printf("libm\n");
    bool m_ok = true; double worst = 0;
    for (double x : {0.5, 1.0, -2.25, 3.14159, 10.0, 100.0, 1e-3}) {
        call("sin", {}, {x}); double s = c.f[1];
        call("cos", {}, {x}); double co = c.f[1];
        worst = std::max({worst, std::fabs(s - std::sin(x)), std::fabs(co - std::cos(x))});
        m_ok &= close(s, std::sin(x), 1e-15) && close(co, std::cos(x), 1e-15);
    }
    char w[64]; std::snprintf(w, sizeof w, "worst |error| %.2e", worst);
    check(m_ok, "sin / cos at 7 points", w);

    std::printf("qsort through game comparators (indirect calls)\n");
    std::vector<int32_t> v(200);
    for (auto& x : v) x = (int32_t)(rng() % 20001) - 10000;
    uint32_t arr = alloc(4 * (uint32_t)v.size());
    for (size_t i = 0; i < v.size(); ++i) st32(arr + 4 * (uint32_t)i, (uint32_t)v[i]);
    call("qsort", {arr, (uint32_t)v.size(), 4, g_sym["fileEntryCmpFuncByNameHash__FPCvPCv"]});
    std::sort(v.begin(), v.end());
    bool q_ok = true;
    for (size_t i = 0; i < v.size(); ++i) q_ok &= (int32_t)ld32(arr + 4 * (uint32_t)i) == v[i];
    check(q_ok, "qsort 200 ints with fileEntryCmpFuncByNameHash");
    std::vector<std::string> names = {"tori", "Andre", "jade", "Beck", "cat", "Robbie", "rex",
                                      "Trina", "sikowitz", "Sinjin", "Lane", "festus"};
    uint32_t sarr = alloc(4 * (uint32_t)names.size());
    for (size_t i = 0; i < names.size(); ++i) st32(sarr + 4 * (uint32_t)i, put_str(names[i]));
    call("qsort", {sarr, (uint32_t)names.size(), 4, g_sym["sortMe__FPCvPCv"]});
    std::sort(names.begin(), names.end(), [](auto& a, auto& b) { return strcasecmp(a.c_str(), b.c_str()) < 0; });
    std::string got;
    bool s_ok = true;
    for (size_t i = 0; i < names.size(); ++i) {
        std::string s = get_str(ld32(sarr + 4 * (uint32_t)i));
        s_ok &= s == names[i]; got += s + " ";
    }
    check(s_ok, "qsort 12 names with sortMe (case-insensitive)", got);

    std::printf("SDK matrix library (paired singles)\n");
    std::uniform_real_distribution<float> U(-4.f, 4.f);
    float A[3][4], B[3][4], H[3][4];
    uint32_t ga = alloc(48), gb = alloc(48), gab = alloc(48), gi = alloc(48);
    for (int r = 0; r < 3; ++r) for (int k = 0; k < 4; ++k) {
        A[r][k] = U(rng); B[r][k] = U(rng);
        put_f32(ga + 16 * r + 4 * k, A[r][k]); put_f32(gb + 16 * r + 4 * k, B[r][k]);
    }
    for (int r = 0; r < 3; ++r) for (int k = 0; k < 4; ++k)
        H[r][k] = A[r][0] * B[0][k] + A[r][1] * B[1][k] + A[r][2] * B[2][k] + (k == 3 ? A[r][3] : 0.f);
    call("PSMTXConcat", {ga, gb, gab});
    double err = 0;
    for (int r = 0; r < 3; ++r) for (int k = 0; k < 4; ++k) err = std::max(err, (double)std::fabs(get_f32(gab + 16 * r + 4 * k) - H[r][k]));
    std::snprintf(w, sizeof w, "max |error| %.2e", err);
    check(err < 1e-4, "PSMTXConcat", w);
    uint32_t vs = alloc(12), vd = alloc(12);
    float V[3] = {1.5f, -2.f, 0.25f};
    for (int k = 0; k < 3; ++k) put_f32(vs + 4 * k, V[k]);
    call("PSMTXMultVec", {ga, vs, vd});
    err = 0;
    for (int r = 0; r < 3; ++r) err = std::max(err, (double)std::fabs(get_f32(vd + 4 * r) - (A[r][0] * V[0] + A[r][1] * V[1] + A[r][2] * V[2] + A[r][3])));
    std::snprintf(w, sizeof w, "max |error| %.2e", err);
    check(err < 1e-4, "PSMTXMultVec", w);
    call("PSMTXInverse", {ga, gi});
    bool inv = c.r[3] == 1;
    call("PSMTXConcat", {ga, gi, gab});
    err = 0;
    for (int r = 0; r < 3; ++r) for (int k = 0; k < 4; ++k) err = std::max(err, (double)std::fabs(get_f32(gab + 16 * r + 4 * k) - (r == k ? 1.f : 0.f)));
    std::snprintf(w, sizeof w, "|A * inv(A) - I| %.2e", err);
    check(inv && err < 1e-3, "PSMTXInverse", w);

    std::printf("memcpy / memset (the game's, FPR-based copies)\n");
    bool mc_ok = true;
    for (int t = 0; t < 200 && mc_ok; ++t) {
        uint32_t n = (uint32_t)(rng() % 700), so = (uint32_t)(rng() % 8), dof = (uint32_t)(rng() % 8);
        uint32_t src = alloc(720) + so, dst = alloc(720) + dof;
        std::vector<uint8_t> ref(n);
        for (auto& b : ref) b = (uint8_t)rng();
        mem_write(src, ref.data(), n);
        call("memcpy", {dst, src, n});
        std::vector<uint8_t> out(n);
        mem_read(dst, out.data(), n);
        mc_ok &= out == ref && c.r[3] == dst;
        g_heap = 0x81100000u;
    }
    check(mc_ok, "memcpy, 200 random sizes and alignments (bit-exact through FPRs)");
    uint32_t ms = alloc(300);
    std::memset(g_mem + ms, 0, 300);
    call("memset", {ms + 3, 0xA5, 257});
    bool ms_ok = true;
    for (uint32_t i = 0; i < 257; ++i) ms_ok &= g_mem[ms + 3 + i] == 0xA5;
    check(ms_ok && g_mem[ms + 2] == 0 && g_mem[ms + 260] == 0, "memset");

    std::printf("%d passed, %d failed\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
