"""
Diagnostic 7 — Output buffer memory growth (L7, TG10)

Measures _output_buffer growth between flush cycles:
  1-5: Synthetic injection with flush timer stopped
  6:   Realistic 10MB QProcess load with 50ms sampling

DOES NOT modify scaffold.py.
"""

import sys, os, time, json, tempfile

# Force offscreen rendering — no window needed
os.environ["QT_QPA_PLATFORM"] = "offscreen"

sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QProcess

app = QApplication(sys.argv)

import scaffold

# ── Helper ────────────────────────────────────────────────────────────────────

def sizeof_buffer(buf):
    """Return (len, shallow_getsizeof, deep_byte_estimate)."""
    shallow = sys.getsizeof(buf)
    deep = shallow
    for text, color in buf:
        deep += sys.getsizeof(text) + sys.getsizeof(color)
    return len(buf), shallow, deep


def fmt(nbytes):
    if nbytes < 1024:
        return f"{nbytes} B"
    if nbytes < 1024 * 1024:
        return f"{nbytes / 1024:.1f} KB"
    return f"{nbytes / (1024 * 1024):.2f} MB"


def log(msg=""):
    print(msg, flush=True)


# ── Create a tool schema with _format to avoid dialog ─────────────────────────

schema = {
    "_format": "scaffold_schema",
    "tool": "diag_buffer_test",
    "binary": "echo",
    "description": "Diagnostic test tool.",
    "arguments": [
        {"name": "Verbose", "flag": "-v", "type": "boolean"}
    ]
}
tmp_schema = tempfile.NamedTemporaryFile(
    mode="w", suffix=".json", delete=False, dir=os.path.dirname(__file__)
)
json.dump(schema, tmp_schema)
tmp_schema.close()
SCHEMA = tmp_schema.name

# ── Build MainWindow ──────────────────────────────────────────────────────────

win = scaffold.MainWindow(tool_path=SCHEMA)
app.processEvents()

log("=" * 72)
log("DIAGNOSTIC 7 - Output buffer memory growth")
log("=" * 72)

# ── Part 1-5: Synthetic injection with timer stopped ──────────────────────────

log("\n--- Part 1-5: Synthetic injection (flush timer STOPPED) ---\n")

# Stop the flush timer so the buffer never drains
win._flush_timer.stop()

CHUNK = "X" * 1024  # 1 KB string

results = []
for count in [1, 10, 100, 1_000, 10_000]:
    # Clear buffer first
    win._output_buffer.clear()

    for _ in range(count):
        win._output_buffer.append((CHUNK, scaffold.OUTPUT_FG))

    buf_len, shallow, deep = sizeof_buffer(win._output_buffer)
    results.append((count, buf_len, shallow, deep))
    log(f"  {count:>6} iterations: len={buf_len:>6}  shallow={fmt(shallow):>10}  deep={fmt(deep):>10}")

# ── Part 5b: Flush a SMALL buffer (100 entries) to measure drain behaviour ────

log("\n  [Flush test with 100-entry buffer]")
win._output_buffer.clear()
win.output.clear()
for _ in range(100):
    win._output_buffer.append((CHUNK, scaffold.OUTPUT_FG))
log(f"  Buffer before flush: len={len(win._output_buffer)}")

win._flush_timer.start()
start = time.monotonic()
while time.monotonic() - start < 1.0:
    app.processEvents()
    time.sleep(0.01)

buf_len_after, shallow_after, deep_after = sizeof_buffer(win._output_buffer)
log(f"  Buffer after flush:  len={buf_len_after}  shallow={fmt(shallow_after)}  deep={fmt(deep_after)}")

# Clean up
win._flush_timer.stop()
win._output_buffer.clear()
win.output.clear()
app.processEvents()

# ── Part 6: Realistic 10MB QProcess load ──────────────────────────────────────

log("\n--- Part 6: Realistic QProcess load (10 MB output) ---\n")

TOTAL_BYTES = 10 * 1024 * 1024  # 10 MB
# Write in 64KB chunks so readyReadStandardOutput fires many times
EMIT_SCRIPT = (
    "import sys\n"
    f"remaining = {TOTAL_BYTES}\n"
    "chunk = b'A' * 65536\n"
    "while remaining > 0:\n"
    "    n = min(remaining, 65536)\n"
    "    sys.stdout.buffer.write(chunk[:n])\n"
    "    remaining -= n\n"
    "sys.stdout.buffer.flush()\n"
)

samples = []       # (elapsed_ms, buf_len, deep_size)
peak_len = 0
peak_deep = 0
process_done = [False]

def sample_buffer():
    buf_len, _, deep = sizeof_buffer(win._output_buffer)
    elapsed = time.monotonic() - run_start
    samples.append((elapsed * 1000, buf_len, deep))

def on_finished_hook(exit_code, exit_status):
    process_done[0] = True

# Create a QProcess the same way scaffold does
proc = QProcess(win)
proc.setProgram(sys.executable)
proc.setArguments(["-c", EMIT_SCRIPT])
proc.readyReadStandardOutput.connect(win._on_stdout_ready)
proc.readyReadStandardError.connect(win._on_stderr_ready)
proc.finished.connect(on_finished_hook)

# Assign to win.process so _on_stdout_ready can call self.process.readAllStandardOutput()
win.process = proc

# IMPORTANT: Keep flush timer STOPPED during the load test to measure
# raw buffer growth. If we flush, the QPlainTextEdit insertText calls
# are extremely slow and dominate timing.
win._flush_timer.stop()

run_start = time.monotonic()
proc.start()
log(f"  Process started (PID {proc.processId()})")

# Sample at ~50ms intervals until process is done
sample_timer = QTimer()
sample_timer.setInterval(50)
sample_timer.timeout.connect(sample_buffer)
sample_timer.start()

# Event loop until process completes (30s safety timeout)
timeout_at = run_start + 30
while not process_done[0] and time.monotonic() < timeout_at:
    app.processEvents()
    time.sleep(0.005)

# Final sample
sample_buffer()
sample_timer.stop()
elapsed_total = (time.monotonic() - run_start) * 1000

# Compute peaks
for elapsed_ms, buf_len, deep in samples:
    if buf_len > peak_len:
        peak_len = buf_len
    if deep > peak_deep:
        peak_deep = deep

# Now measure what flush does to the buffer
preflushed_len = len(win._output_buffer)
log(f"  Buffer entries before flush: {preflushed_len}")

# Flush (may be slow due to QPlainTextEdit rendering)
flush_start = time.monotonic()
win._flush_output()
flush_elapsed = (time.monotonic() - flush_start) * 1000
final_len, _, final_deep = sizeof_buffer(win._output_buffer)

log(f"  Total elapsed:        {elapsed_total:.0f} ms")
log(f"  Samples collected:    {len(samples)}")
log(f"  Peak buffer entries:  {peak_len}")
log(f"  Peak buffer memory:   {fmt(peak_deep)}")
log(f"  Flush took:           {flush_elapsed:.0f} ms")
log(f"  Buffer after flush:   len={final_len}  deep={fmt(final_deep)}")

log("\n  Sample trace (elapsed_ms, buf_entries, buf_deep):")
for elapsed_ms, buf_len, deep in samples:
    log(f"    {elapsed_ms:8.1f} ms  entries={buf_len:>6}  deep={fmt(deep):>10}")

# ── Part 6b: With flush timer active (realistic) ─────────────────────────────

log("\n--- Part 6b: Realistic load WITH flush timer active ---\n")

win._output_buffer.clear()
win.output.clear()
app.processEvents()

samples2 = []
peak_len2 = 0
peak_deep2 = 0
process_done[0] = False

def sample_buffer2():
    buf_len, _, deep = sizeof_buffer(win._output_buffer)
    elapsed = time.monotonic() - run_start2
    samples2.append((elapsed * 1000, buf_len, deep))

proc2 = QProcess(win)
proc2.setProgram(sys.executable)
proc2.setArguments(["-c", EMIT_SCRIPT])
proc2.readyReadStandardOutput.connect(win._on_stdout_ready)
proc2.readyReadStandardError.connect(win._on_stderr_ready)
proc2.finished.connect(on_finished_hook)
win.process = proc2

# Enable flush timer (normal operation)
win._flush_timer.start()

sample_timer2 = QTimer()
sample_timer2.setInterval(50)
sample_timer2.timeout.connect(sample_buffer2)
sample_timer2.start()

run_start2 = time.monotonic()
proc2.start()
log(f"  Process started (PID {proc2.processId()})")

timeout_at2 = run_start2 + 120  # longer timeout — flush is slow
while not process_done[0] and time.monotonic() < timeout_at2:
    app.processEvents()
    time.sleep(0.005)

sample_buffer2()
sample_timer2.stop()
win._flush_timer.stop()
elapsed_total2 = (time.monotonic() - run_start2) * 1000

for elapsed_ms, buf_len, deep in samples2:
    if buf_len > peak_len2:
        peak_len2 = buf_len
    if deep > peak_deep2:
        peak_deep2 = deep

log(f"  Total elapsed:        {elapsed_total2:.0f} ms")
log(f"  Samples collected:    {len(samples2)}")
log(f"  Peak buffer entries:  {peak_len2}")
log(f"  Peak buffer memory:   {fmt(peak_deep2)}")

log("\n  Sample trace (elapsed_ms, buf_entries, buf_deep):")
for elapsed_ms, buf_len, deep in samples2:
    log(f"    {elapsed_ms:8.1f} ms  entries={buf_len:>6}  deep={fmt(deep):>10}")

# ── Summary ───────────────────────────────────────────────────────────────────

log("\n" + "=" * 72)
log("SUMMARY")
log("=" * 72)
log(f"""
Synthetic injection (flush disabled):
  1 x 1KB   -> deep = {fmt(results[0][3])}
  10 x 1KB  -> deep = {fmt(results[1][3])}
  100 x 1KB -> deep = {fmt(results[2][3])}
  1K x 1KB  -> deep = {fmt(results[3][3])}
  10K x 1KB -> deep = {fmt(results[4][3])}

Realistic 10MB QProcess load (flush DISABLED):
  Peak buffer entries:  {peak_len}
  Peak buffer memory:   {fmt(peak_deep)}
  Total elapsed:        {elapsed_total:.0f} ms

Realistic 10MB QProcess load (flush ENABLED, 100ms timer):
  Peak buffer entries:  {peak_len2}
  Peak buffer memory:   {fmt(peak_deep2)}
  Total elapsed:        {elapsed_total2:.0f} ms

Q1: Buffer is UNBOUNDED between flush cycles. No cap on list length.
    The flush timer fires every 100ms, but readyReadStandardOutput can
    deliver many chunks between flushes.

Q2: Peak memory cost with flush enabled:    {fmt(peak_deep2)}
    Peak memory cost with flush disabled:   {fmt(peak_deep)}

Q3: No back-pressure mechanism exists. QProcess.readyReadStandardOutput
    is always consumed immediately via readAllStandardOutput() and appended
    to the list. There is no pause(), suspend(), or read-throttling.
""")

# Cleanup
os.unlink(SCHEMA)
win.close()
app.quit()
sys.exit(0)
