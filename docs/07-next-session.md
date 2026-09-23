# TODO — session 2

Phase 1 of the plan: the recompiler, up to "everything compiles".

1. **Semantics table**: for each of the 169 operations `--mix` reports,
   the C++ it becomes, including Rc/OE/CR/XER side effects, `frsp` and
   single-precision rounding, and paired singles with GQR (de)quantisation.
   Start from the most frequent ops; `.long` must stay at zero.
2. **Function map**: from `.symtab`, every function with its range; flag
   functions whose code falls outside their symbol (tail merges, shared
   epilogues `_savegpr_*` / `_restgpr_*`).
3. **Switch tables**: find the 719 `bctr` sites, the `lis/addi/lwzx/mtctr`
   pattern before each, and the table in `.data` / `.rodata`; list the
   targets.
4. **Emitter**: one C++ function per guest function, gotos for internal
   branches, direct calls for `bl` to known functions, `ctx` for registers,
   a dispatcher for `bctrl`.
5. **Build**: generate the whole of `.text` and compile it (a CMake target
   that only has to compile, not run). Count and fix what does not compile.
6. **Side work**, if time allows:
   * read `readController` (`05-open-questions.md` 1) and
     `setDefaultControlMapping` (2);
   * a Dolphin FIFO log of the main menu, to size the GX renderer (9).

Not yet: the runtime. It waits until the generated code compiles.
