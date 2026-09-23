# TODO — session 3

Phase 2 of the plan: boot. Run `__start` natively and get as far as
`CGame::init`, meeting the hardware one piece at a time.

1. **Choose the cut for system services.** Two candidates, to decide by
   reading the SDK code the game links:
   * *SDK functions*: replace `OSCreateThread`, `DVDRead*`, `NANDOpen`…
     with host code. It is direct, but there are many of them and they share
     state.
   * *IOS IPC*: let the SDK run as it is and answer its IPC requests
     (`/dev/di`, `/dev/fs`, `/dev/es`, `/dev/stm`, `/dev/usb/oh1`…) at the
     mailbox registers (`0xCD000000`), as Dolphin's IOS HLE does. Fewer and
     better-defined entry points, and game-agnostic, so it suits wiikit.
2. **Low memory**: the globals the IPL and apploader leave at `0x80000000`
   (disc ID, memory size, arena bounds, bus and CPU clocks, the BI2 pointer,
   OS globals), set before `__start` as Dolphin's HLE boot does.
3. **Threads**: `OSLoadContext` and the scheduler (`SelectThread`,
   `__OSDispatchInterrupt`) on host threads, one guest thread running at a
   time; alarms and the decrementer from the host clock.
4. **Console**: `OSReport` and friends to stdout. The first run will say
   where it stops.
5. **MMIO log**: every register the boot touches, with the function that
   touched it: the to-do list for the rest of phase 2.
6. **Side work**:
   * a Dolphin FIFO log of the main menu, to size the GX renderer
     (`05-open-questions.md` 9);
   * read `readController` and `setDefaultControlMapping` (questions 1–2).
