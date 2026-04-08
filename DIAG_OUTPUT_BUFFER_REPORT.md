# Diagnostic 7 — Output Buffer Memory Growth

**Date:** 2026-04-07
**Scope:** `_output_buffer` in `MainWindow` (scaffold.py L6495)

---

## Architecture

| Component | Location | Role |
|---|---|---|
| `_output_buffer` | L6495 | `list[tuple[str, str]]` — unbounded list of `(text, color)` pairs |
| `_flush_timer` | L6496-6498 | `QTimer`, 100ms interval, calls `_flush_output()` |
| `_on_stdout_ready` | L7024-7032 | Reads all available QProcess stdout, appends to buffer, starts timer |
| `_on_stderr_ready` | L7034-7042 | Same for stderr (colored `COLOR_WARN`) |
| `_flush_output` | L7044-7058 | Stops timer, iterates buffer, inserts each entry into QPlainTextEdit via `cursor.insertText()`, calls `.clear()` |
| `_on_finished` | L7067-7072 | Calls `_flush_output()` one final time on process exit |

**Data flow:**
`QProcess.readyReadStandardOutput` -> `_on_stdout_ready` -> `_output_buffer.append()` -> (100ms timer) -> `_flush_output()` -> `QPlainTextEdit.insertText()` -> `_output_buffer.clear()`

The QPlainTextEdit has `setMaximumBlockCount(OUTPUT_MAX_BLOCKS=10000)` (L6474) which caps the rendered line count, but the in-memory buffer list has no cap.

---

## Synthetic Injection Results (flush timer stopped)

Each iteration appends a 1KB string to the buffer.

| Iterations | Buffer len | Shallow size | Deep size |
|---:|---:|---:|---:|
| 1 | 1 | 88 B | 1.2 KB |
| 10 | 10 | 184 B | 11.0 KB |
| 100 | 100 | 920 B | 109.6 KB |
| 1,000 | 1,000 | 8.6 KB | 1.07 MB |
| 10,000 | 10,000 | 83.2 KB | 10.70 MB |

Growth is perfectly linear: ~1.1 KB overhead per entry (1024 bytes string + tuple + color string ref).

**Flush test (100 entries):** Buffer drained to len=0 after one flush cycle. Confirms `_flush_output()` calls `.clear()` correctly.

---

## Realistic QProcess Load (10 MB)

Subprocess: `python -c "write 10MB in 64KB chunks"`

### With flush timer DISABLED (worst case)

| Metric | Value |
|---|---|
| Total elapsed | 42 ms |
| Peak buffer entries | **1** |
| Peak buffer memory | **10.00 MB** |
| Flush time (single call) | 1,255 ms |

### With flush timer ENABLED (normal operation)

| Metric | Value |
|---|---|
| Total elapsed | 40 ms |
| Peak buffer entries | **1** |
| Peak buffer memory | **10.00 MB** |

**Key observation:** QProcess delivered the entire 10MB as a **single** `readyReadStandardOutput` signal. `readAllStandardOutput()` returned one 10MB byte blob which became a single ~10MB Python string in one buffer entry. The number of entries is small, but the **byte content** of individual entries can be arbitrarily large.

This means the buffer's memory cost is dominated by the size of individual `readAllStandardOutput()` returns, not the number of entries. A fast-producing subprocess fills Qt's internal pipe buffer, and `readAllStandardOutput()` drains it all at once.

---

## Answers

### Q1: Is the buffer actually unbounded between flush cycles?

**Yes, the buffer is unbounded.** There is no cap on `_output_buffer` length or total byte content.

However, in practice the 100ms flush timer keeps the **entry count** small (typically 1-5 entries between flushes). The real risk is not the number of entries but the **size of individual entries** — `readAllStandardOutput()` returns everything available in the pipe, which can be many megabytes in a single call if the subprocess writes faster than the event loop processes.

With flush enabled, the timer fires frequently enough that entries don't accumulate. But each individual entry can hold megabytes of data until it's flushed.

### Q2: Realistic peak memory cost for 10 MB/sec over 5 seconds?

**~10 MB peak buffer cost**, based on the measured 10MB load completing in ~40ms.

The subprocess writes 10MB total. Qt's pipe buffering means `readyReadStandardOutput` fires only once (or a handful of times), delivering the entire payload in one `readAllStandardOutput()` call. The buffer holds ~10MB in a single entry.

For a sustained 10 MB/sec stream over 5 seconds (50 MB total), the peak depends on how fast `_flush_output()` can drain to QPlainTextEdit. Measured flush rate: 10 MB took 1,255 ms to insert into QPlainTextEdit. During that 1.2 seconds, the event loop is blocked and no new `readyReadStandardOutput` signals fire — Qt pipe-buffers the incoming data. So the peak is roughly **one flush-cycle's worth of accumulated data** plus whatever Qt is holding in its pipe buffer.

Estimated peak for 50 MB total at 10 MB/sec: **10-15 MB** in the Python buffer, with additional data held in Qt's internal pipe buffer (OS-level, typically 64KB-1MB). The bottleneck is the QPlainTextEdit rendering, not the buffer itself.

### Q3: Is there any existing back-pressure mechanism?

**No.** There is no back-pressure at any level:

1. **QProcess level:** No `pause()`, `suspend()`, `setReadChannelMode()`, or any mechanism to stop reading from the pipe. `readyReadStandardOutput` is always connected and always calls `readAllStandardOutput()`.
2. **Buffer level:** No size cap, no high-water mark, no discard policy.
3. **OS pipe level:** The only implicit back-pressure is the OS pipe buffer (typically 4KB-64KB on Windows). When it fills, the child process's `write()` call blocks. But `readAllStandardOutput()` always drains it completely, so this only throttles if the event loop is blocked (e.g., during `_flush_output()`'s QPlainTextEdit insertion).

The implicit throttle from the slow QPlainTextEdit rendering (1.2s to render 10MB) is the only thing that limits peak memory in practice — while `_flush_output()` runs, the event loop is blocked, so the OS pipe buffer provides natural back-pressure to the child process.

---

## Call Sites Summary

| Line | Function | Access |
|---|---|---|
| 6495 | `__init__` | Initialize: `self._output_buffer: list[tuple[str, str]] = []` |
| 7030 | `_on_stdout_ready` | Append: `self._output_buffer.append((text, OUTPUT_FG))` |
| 7040 | `_on_stderr_ready` | Append: `self._output_buffer.append((text, COLOR_WARN))` |
| 7047 | `_flush_output` | Read guard: `if not self._output_buffer: return` |
| 7051 | `_flush_output` | Iterate: `for text, color in self._output_buffer:` |
| 7056 | `_flush_output` | Clear: `self._output_buffer.clear()` |
| 7072 | `_on_finished` | Drain: `self._flush_output()` (final flush on exit) |
